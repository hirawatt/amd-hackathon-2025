from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_agent import AISchedulingAgent
from src.calendar_integration import CalendarManager
from utils.time_utils import (
    parse_datetime_string, parse_time_constraint, 
    calculate_search_range, format_datetime_for_output,
    get_business_hours_slots, is_within_business_hours
)

class MeetingScheduler:
    def __init__(self, vllm_base_url="http://localhost:3000/v1", 
                 model_path="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"):
        self.ai_agent = AISchedulingAgent(vllm_base_url, model_path)
        self.calendar_manager = CalendarManager()
    
    def schedule_meeting(self, request_data):
        """Main function to schedule a meeting based on request"""
        try:
            print("\n=== STARTING MEETING SCHEDULER ===")
            
            # Extract basic information
            request_id = request_data["Request_id"]
            from_email = request_data["From"]
            subject = request_data["Subject"]
            email_content = request_data["EmailContent"]
            request_datetime = request_data["Datetime"]
            location = request_data["Location"]
            
            print(f"Request ID: {request_id}")
            print(f"Subject: {subject}")
            print(f"From: {from_email}")
            
            # Get all attendee emails
            attendee_emails = [attendee["email"] for attendee in request_data["Attendees"]]
            if from_email not in attendee_emails:
                attendee_emails.append(from_email)
            
            # Parse email content using AI
            print(f"\n--- Parsing email with AI ---")
            meeting_details = self.ai_agent.parse_email(email_content)
            print(f"AI parsed meeting details: {meeting_details}")
            
            # Ensure duration_mins is an integer
            duration_mins = int(meeting_details.get('duration_mins', 30))
            time_constraints = meeting_details.get('time_constraints', '')
            print(f"Duration: {duration_mins} mins, Constraints: {time_constraints}")
            
            # Extract specific datetime if mentioned
            print(f"\n--- Extracting datetime preferences ---")
            datetime_pref = self.ai_agent.extract_datetime_preference(email_content, request_datetime)
            print(f"Datetime preferences: {datetime_pref}")
            
            # Calculate search range based on constraints and preferences
            request_dt = parse_datetime_string(request_datetime)
            
            # Intelligent search range calculation
            if datetime_pref.get('is_today'):
                # Handle "today" requests
                if request_dt.weekday() >= 5:  # Weekend
                    print(f"'Today' requested on weekend - searching next business day")
                    # For urgent weekend requests, start from Monday
                    days_until_monday = 7 - request_dt.weekday()
                    if request_dt.weekday() == 6:  # Sunday
                        days_until_monday = 1
                    search_dt = request_dt + timedelta(days=days_until_monday)
                else:
                    # Weekday - search today
                    search_dt = request_dt
                    
                search_start = search_dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                search_end = (search_dt + timedelta(days=1)).isoformat()
                
            elif datetime_pref.get('is_tomorrow'):
                # Handle "tomorrow" requests
                tomorrow = request_dt + timedelta(days=1)
                if tomorrow.weekday() >= 5:  # Weekend
                    # Skip to Monday
                    days_until_monday = 7 - tomorrow.weekday()
                    if tomorrow.weekday() == 6:
                        days_until_monday = 1
                    tomorrow = tomorrow + timedelta(days=days_until_monday)
                    
                search_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                search_end = (tomorrow + timedelta(days=1)).isoformat()
                
            elif datetime_pref.get('day_of_week'):
                # Specific day mentioned
                search_start, search_end = calculate_search_range(request_datetime, datetime_pref.get('day_of_week'))
            else:
                # Default search range
                search_start, search_end = calculate_search_range(request_datetime, time_constraints)
            
            # For urgent meetings, limit search to next 2-3 days
            if datetime_pref and datetime_pref.get('urgency') == 'urgent':
                search_end_dt = datetime.fromisoformat(search_start.replace('Z', '+00:00')) + timedelta(days=3)
                search_end = search_end_dt.isoformat()
                print(f"Urgent meeting detected - limiting search to 3 days")
            
            print(f"\n--- Search range ---")
            print(f"Search start: {search_start}")
            print(f"Search end: {search_end}")
            
            # Fetch calendar events for all attendees
            print(f"\n--- Fetching calendars for {len(attendee_emails)} attendees ---")
            attendee_events = []
            for email in attendee_emails:
                events = self.calendar_manager.fetch_calendar_events(email, search_start, search_end)
                attendee_events.append({
                    "email": email,
                    "events": events
                })
            
            # Find common free slots
            print(f"DEBUG: search_start={search_start}, search_end={search_end}")
            free_slots = self.calendar_manager.get_common_free_slots(
                attendee_events, search_start, search_end, duration_mins
            )
            print(f"DEBUG: Found {len(free_slots)} free slots")
            
            # Filter slots based on preferences and business hours
            suitable_slots = self.filter_suitable_slots(
                free_slots, duration_mins, datetime_pref, time_constraints
            )
            print(f"DEBUG: Found {len(suitable_slots)} suitable slots")
            
            # Select the best slot
            if suitable_slots:
                print(f"\n--- Scoring {len(suitable_slots)} suitable slots ---")
                # Score and rank slots based on preferences
                scored_slots = self.score_slots(suitable_slots, datetime_pref, request_datetime)
                
                # Print top 5 scored slots for debugging
                top_5 = sorted(scored_slots, key=lambda x: x['score'], reverse=True)[:5]
                print("\nTop 5 scored slots:")
                for i, s in enumerate(top_5):
                    print(f"{i+1}. Score: {s['score']}, Time: {s['slot']['start']}")
                
                # Use AI to select from top scored slots
                top_slots = sorted(scored_slots, key=lambda x: x['score'], reverse=True)[:5]
                
                ai_suggestion = self.ai_agent.suggest_meeting_time(
                    [s['slot'] for s in top_slots], 
                    duration_mins, 
                    {
                        'time_constraints': time_constraints,
                        'urgency': datetime_pref.get('urgency', 'normal'),
                        'preferred_time': datetime_pref.get('preferred_time'),
                        'time_range': datetime_pref.get('time_range'),
                        'email_content': email_content
                    }
                )
                
                print(f"\n--- AI selecting from top slots ---")
                print(f"AI suggestion: {ai_suggestion}")
                
                selected_slot_idx = ai_suggestion.get('selected_slot_number', 1) - 1
                selected_slot_idx = min(selected_slot_idx, len(top_slots) - 1)
                selected_slot = top_slots[selected_slot_idx]['slot']
                
                event_start = selected_slot['start']
                event_end = selected_slot['end']
                
                print(f"\nSELECTED SLOT: {event_start} to {event_end}")
                print(f"Reason: {ai_suggestion.get('reason', 'No reason provided')}")
            else:
                # No suitable slots found - this should rarely happen now
                # Try to find ANY slot in business hours
                print(f"WARNING: No suitable slots found, expanding search...")
                # Expand search range
                expanded_end = datetime.fromisoformat(search_end.replace('Z', '+00:00')) + timedelta(days=7)
                free_slots = self.calendar_manager.get_common_free_slots(
                    attendee_events, search_start, expanded_end.isoformat(), duration_mins
                )
                suitable_slots = self.filter_suitable_slots(
                    free_slots, duration_mins, None, time_constraints  # No specific time pref
                )
                
                if suitable_slots:
                    selected_slot = suitable_slots[0]  # Take first available
                    event_start = selected_slot['start']
                    event_end = selected_slot['end']
                else:
                    # Last resort - find next available business hour
                    event_start, event_end = self.find_next_business_hour_slot(
                        search_start, duration_mins
                    )
            
            # Create scheduled event for output
            scheduled_event = {
                "StartTime": format_datetime_for_output(event_start),
                "EndTime": format_datetime_for_output(event_end),
                "NumAttendees": len(attendee_emails),
                "Attendees": attendee_emails,
                "Summary": subject
            }
            
            # Add scheduled event to each attendee's events
            for attendee_data in attendee_events:
                attendee_data["events"].append(scheduled_event)
            
            # Prepare output
            output = {
                "Request_id": request_id,
                "Datetime": request_datetime,
                "Location": location,
                "From": from_email,
                "Attendees": attendee_events,
                "Subject": subject,
                "EmailContent": email_content,
                "EventStart": format_datetime_for_output(event_start),
                "EventEnd": format_datetime_for_output(event_end),
                "Duration_mins": str(duration_mins),
                "MetaData": {
                    "scheduling_method": "ai_optimized",
                    "constraints_considered": time_constraints
                }
            }
            
            return output
            
        except Exception as e:
            print(f"\n!!! ERROR in schedule_meeting: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Traceback:")
            traceback.print_exc()
            # Return with minimal valid response
            return self.create_error_response(request_data, str(e))
    
    def filter_suitable_slots(self, free_slots, duration_mins, datetime_pref, time_constraints):
        """Filter free slots based on preferences and constraints"""
        suitable_slots = []
        
        for slot in free_slots:
            try:
                slot_start = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                slot_end = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
                
                # Check if slot is long enough
                slot_duration = (slot_end - slot_start).total_seconds() / 60
                if slot_duration < int(duration_mins):
                    continue
                
                # For each possible start time within the slot (30-min intervals)
                current = slot_start
                while current + timedelta(minutes=int(duration_mins)) <= slot_end:
                    # Check business hours
                    if is_within_business_hours(current):
                        # Check specific time preference if mentioned
                        if datetime_pref and datetime_pref.get('is_specific_time'):
                            preferred_hour = int(datetime_pref.get('preferred_time', '10:00').split(':')[0])
                            if current.hour == preferred_hour:
                                suitable_slots.append({
                                    'start': current.isoformat(),
                                    'end': (current + timedelta(minutes=int(duration_mins))).isoformat()
                                })
                        else:
                            # No specific time preference, add the slot
                            suitable_slots.append({
                                'start': current.isoformat(),
                                'end': (current + timedelta(minutes=int(duration_mins))).isoformat()
                            })
                    
                    # Move to next 30-minute interval
                    current += timedelta(minutes=30)
                    
            except Exception as e:
                print(f"ERROR in filter_suitable_slots: {e}")
                print(f"  slot={slot}")
                raise
        
        return suitable_slots
    
    def score_slots(self, slots, datetime_pref, request_datetime):
        """Score slots based on preferences and constraints"""
        scored_slots = []
        request_dt = parse_datetime_string(request_datetime)
        
        for slot in slots:
            slot_dt = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
            score = 0
            
            # Urgency scoring - urgent meetings get higher scores for earlier slots
            if datetime_pref and datetime_pref.get('urgency') == 'urgent':
                # Hours from now - lower is better for urgent
                hours_from_now = (slot_dt - request_dt).total_seconds() / 3600
                if hours_from_now < 24:
                    score += 100  # Within 24 hours
                elif hours_from_now < 48:
                    score += 50   # Within 48 hours
                else:
                    score += 25   # Later
            
            # Specific time preference scoring
            if datetime_pref and datetime_pref.get('is_specific_time'):
                preferred_time = datetime_pref.get('preferred_time', '10:00')
                preferred_hour = int(preferred_time.split(':')[0])
                preferred_minute = int(preferred_time.split(':')[1]) if ':' in preferred_time else 0
                
                if slot_dt.hour == preferred_hour and slot_dt.minute == preferred_minute:
                    score += 200  # Exact match
                elif slot_dt.hour == preferred_hour:
                    score += 100  # Hour matches
                    
            # Handle time ranges intelligently
            if datetime_pref and datetime_pref.get('time_range'):
                time_range = datetime_pref.get('time_range')
                if '-' in time_range:
                    start_str, end_str = time_range.split('-')
                    range_start_hour = int(start_str.split(':')[0])
                    range_end_hour = int(end_str.split(':')[0])
                    
                    if range_start_hour <= slot_dt.hour < range_end_hour:
                        # Slot is within the requested range
                        score += 150
                        # Prefer earlier slots in the range for urgent meetings
                        if datetime_pref.get('urgency') == 'urgent' and slot_dt.hour == range_start_hour:
                            score += 50
            
            # Day of week preference
            if datetime_pref and datetime_pref.get('day_of_week'):
                weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                slot_weekday = weekdays[slot_dt.weekday()]
                if slot_weekday == datetime_pref.get('day_of_week'):
                    score += 150  # Correct day
            
            # General preferences
            # Morning slots (9-11 AM) are generally preferred
            if 9 <= slot_dt.hour < 11:
                score += 30
            # Avoid early morning and late afternoon
            elif slot_dt.hour < 9:
                score -= 20
            elif slot_dt.hour >= 16:
                score -= 10
            
            # Avoid slots right after lunch
            if slot_dt.hour == 13:
                score -= 15
            
            scored_slots.append({
                'slot': slot,
                'score': score,
                'datetime': slot_dt
            })
        
        return scored_slots
    
    def find_next_business_hour_slot(self, search_start, duration_mins):
        """Find the next available business hour slot"""
        start_dt = datetime.fromisoformat(search_start.replace('Z', '+00:00'))
        
        # Start from next business day at 10 AM
        if start_dt.hour >= 17 or start_dt.weekday() >= 4:  # After 5 PM or Friday/weekend
            # Move to next Monday
            days_ahead = 0 - start_dt.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            start_dt = start_dt + timedelta(days=days_ahead)
        else:
            # Next day
            start_dt = start_dt + timedelta(days=1)
        
        # Set to 10 AM
        slot_start = start_dt.replace(hour=10, minute=0, second=0, microsecond=0)
        slot_end = slot_start + timedelta(minutes=int(duration_mins))
        
        return slot_start.isoformat(), slot_end.isoformat()
    
    def find_fallback_slot(self, attendee_events, search_start, duration_mins):
        """Find a fallback slot when no common free time is available"""
        # Start from next business day at 10 AM
        start_dt = datetime.fromisoformat(search_start.replace('Z', '+00:00'))
        
        # Move to next business day
        if start_dt.weekday() >= 4:  # Friday or weekend
            days_to_monday = 7 - start_dt.weekday()
            start_dt = start_dt + timedelta(days=days_to_monday)
        else:
            start_dt = start_dt + timedelta(days=1)
        
        # Set to 10 AM
        fallback_start = start_dt.replace(hour=10, minute=0, second=0, microsecond=0)
        fallback_end = fallback_start + timedelta(minutes=int(duration_mins))
        
        return fallback_start.isoformat(), fallback_end.isoformat()
    
    def create_error_response(self, request_data, error_msg):
        """Create a valid response even when errors occur"""
        # Use a default time slot (next day at 10 AM)
        now = datetime.now(tz=timezone.utc)
        tomorrow = now + timedelta(days=1)
        event_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        event_end = event_start + timedelta(minutes=30)
        
        attendee_events = []
        for attendee in request_data.get("Attendees", []):
            attendee_events.append({
                "email": attendee["email"],
                "events": []
            })
        
        return {
            "Request_id": request_data.get("Request_id", ""),
            "Datetime": request_data.get("Datetime", ""),
            "Location": request_data.get("Location", ""),
            "From": request_data.get("From", ""),
            "Attendees": attendee_events,
            "Subject": request_data.get("Subject", ""),
            "EmailContent": request_data.get("EmailContent", ""),
            "EventStart": event_start.isoformat(),
            "EventEnd": event_end.isoformat(),
            "Duration_mins": "30",
            "MetaData": {"error": error_msg}
        }