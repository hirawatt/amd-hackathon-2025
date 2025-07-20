import json
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class CalendarManager:
    def __init__(self, keys_directory="Keys"):
        self.keys_directory = keys_directory
        
    def get_user_credentials(self, email):
        """Load user credentials from token file"""
        try:
            token_filename = email.split("@")[0] + ".token"
            token_path = f"{self.keys_directory}/{token_filename}"
            return Credentials.from_authorized_user_file(token_path)
        except Exception as e:
            print(f"Error loading credentials for {email}: {e}")
            return None
    
    def fetch_calendar_events(self, email, start_time, end_time):
        """Fetch calendar events for a user within a time range"""
        events_list = []
        
        print(f"[Calendar] Fetching events for {email} from {start_time} to {end_time}")
        
        try:
            creds = self.get_user_credentials(email)
            if not creds:
                print(f"[Calendar] No credentials found for {email}")
                return events_list
            
            service = build("calendar", "v3", credentials=creds)
            
            # Call the Calendar API
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"[Calendar] Found {len(events)} events for {email}")
            
            for event in events:
                attendee_list = []
                
                # Extract attendees
                if 'attendees' in event:
                    for attendee in event['attendees']:
                        attendee_list.append(attendee['email'])
                else:
                    attendee_list.append("SELF")
                
                # Get event times
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Ensure timezone info is present
                if 'T' in start and '+' not in start and 'Z' not in start:
                    # Add IST timezone if missing
                    start = start + "+05:30"
                if 'T' in end and '+' not in end and 'Z' not in end:
                    # Add IST timezone if missing  
                    end = end + "+05:30"
                
                events_list.append({
                    "StartTime": start,
                    "EndTime": end,
                    "NumAttendees": len(set(attendee_list)),
                    "Attendees": list(set(attendee_list)),
                    "Summary": event.get('summary', 'No Title')
                })
                
        except HttpError as error:
            print(f'An error occurred for {email}: {error}')
        except Exception as e:
            print(f'Error fetching events for {email}: {e}')
            
        return events_list
    
    def find_free_slots(self, busy_times, search_start, search_end, duration_mins):
        """Find available time slots given busy times"""
        free_slots = []
        
        print(f"\n[Calendar] Finding free slots:")
        print(f"  - Busy times count: {len(busy_times)}")
        print(f"  - Search range: {search_start} to {search_end}")
        print(f"  - Min duration needed: {duration_mins} minutes")
        
        # Convert strings to datetime objects if needed
        if isinstance(search_start, str):
            search_start = datetime.fromisoformat(search_start.replace('Z', '+00:00'))
            # Ensure timezone aware
            if search_start.tzinfo is None:
                search_start = search_start.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        if isinstance(search_end, str):
            search_end = datetime.fromisoformat(search_end.replace('Z', '+00:00'))
            # Ensure timezone aware
            if search_end.tzinfo is None:
                search_end = search_end.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        
        
        # Sort busy times by start time (only if not empty)
        if busy_times:
            busy_times.sort(key=lambda x: datetime.fromisoformat(x['start'].replace('Z', '+00:00')))
        
        current_time = search_start
        
        for busy_period in busy_times:
            busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
            busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
            
            # Ensure timezone aware
            if busy_start.tzinfo is None:
                busy_start = busy_start.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            if busy_end.tzinfo is None:
                busy_end = busy_end.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            
            # Check if there's a gap before this busy period
            if current_time + timedelta(minutes=int(duration_mins)) <= busy_start:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': busy_start.isoformat()
                })
            
            # Move current time to end of busy period
            current_time = max(current_time, busy_end)
        
        
        # Check for free time after last busy period
        if current_time + timedelta(minutes=int(duration_mins)) <= search_end:
            free_slots.append({
                'start': current_time.isoformat(),
                'end': search_end.isoformat()
            })
        
        print(f"[Calendar] Found {len(free_slots)} free slots")
        if free_slots:
            print(f"  First slot: {free_slots[0]['start']}")
            print(f"  Last slot: {free_slots[-1]['start']}")
        
        return free_slots
    
    def get_common_free_slots(self, attendee_events, search_start, search_end, duration_mins):
        """Find common free slots for all attendees"""
        all_busy_times = []
        
        # Collect all busy times from all attendees
        for attendee_data in attendee_events:
            for event in attendee_data['events']:
                all_busy_times.append({
                    'start': event['StartTime'],
                    'end': event['EndTime']
                })
        
        # Merge overlapping busy times
        merged_busy = self.merge_overlapping_times(all_busy_times)
        
        # Find free slots
        return self.find_free_slots(merged_busy, search_start, search_end, duration_mins)
    
    def merge_overlapping_times(self, time_periods):
        """Merge overlapping time periods"""
        if not time_periods:
            return []
        
        # Sort by start time
        def get_datetime(time_str):
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            return dt
        
        sorted_periods = sorted(time_periods, key=lambda x: get_datetime(x['start']))
        
        merged = [sorted_periods[0]]
        
        for period in sorted_periods[1:]:
            last_merged = merged[-1]
            last_end = get_datetime(last_merged['end'])
            current_start = get_datetime(period['start'])
            
            if current_start <= last_end:
                # Overlapping, merge them
                current_end = get_datetime(period['end'])
                if current_end > last_end:
                    last_merged['end'] = period['end']
            else:
                # No overlap, add as new period
                merged.append(period)
        
        return merged