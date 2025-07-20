from datetime import datetime, timedelta, timezone
import re

def parse_datetime_string(datetime_str):
    """Parse various datetime string formats"""
    # Handle the format from input JSON: "19-07-2025T12:34:55"
    if 'T' in datetime_str and '+' not in datetime_str and 'Z' not in datetime_str:
        # Add timezone info (IST)
        datetime_str = datetime_str + "+05:30"
    
    # Replace hyphen-separated date with standard format
    if re.match(r'\d{2}-\d{2}-\d{4}', datetime_str[:10]):
        parts = datetime_str.split('T')
        date_parts = parts[0].split('-')
        datetime_str = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}T{parts[1]}"
    
    # Parse and ensure timezone aware
    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    
    # If still timezone naive, add IST timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    
    return dt

def get_next_weekday(current_date, target_weekday):
    """Get the next occurrence of a weekday"""
    weekdays = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    target_day = weekdays.get(target_weekday.lower())
    if target_day is None:
        return None
    
    days_ahead = target_day - current_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    
    result_date = current_date + timedelta(days=days_ahead)
    
    # Preserve timezone info
    if current_date.tzinfo is not None and result_date.tzinfo is None:
        result_date = result_date.replace(tzinfo=current_date.tzinfo)
    
    return result_date

def parse_time_constraint(constraint, reference_date):
    """Parse time constraints like 'next Thursday', 'Monday at 9:00 AM'"""
    constraint_lower = constraint.lower()
    
    # Ensure reference_date has timezone
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    
    # Extract day of week
    weekday_match = re.search(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', constraint_lower)
    
    # Extract time
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?', constraint_lower, re.IGNORECASE)
    
    target_date = reference_date
    target_time = None
    
    if weekday_match:
        weekday = weekday_match.group(1)
        target_date = get_next_weekday(reference_date, weekday)
    
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        period = time_match.group(3)
        
        if period and period.lower() in ['pm', 'p.m.'] and hour != 12:
            hour += 12
        elif period and period.lower() in ['am', 'a.m.'] and hour == 12:
            hour = 0
        
        target_time = {'hour': hour, 'minute': minute}
    
    return target_date, target_time

def get_business_hours_slots(date, duration_mins, timezone_offset="+05:30"):
    """Get available business hour slots for a given date"""
    slots = []
    
    # Business hours: 9 AM to 6 PM
    start_hour = 9
    end_hour = 18
    
    # Ensure date has timezone info
    if hasattr(date, 'tzinfo') and date.tzinfo is not None:
        # If date has timezone, use it to construct the times
        current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    else:
        # Create datetime objects for the date with timezone
        date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
        current_time = datetime.fromisoformat(f"{date_str}T{start_hour:02d}:00:00{timezone_offset}")
        end_time = datetime.fromisoformat(f"{date_str}T{end_hour:02d}:00:00{timezone_offset}")
    
    while current_time + timedelta(minutes=duration_mins) <= end_time:
        # Skip lunch hour (12 PM - 1 PM)
        if current_time.hour == 12:
            current_time = current_time.replace(hour=13, minute=0)
            continue
        
        slots.append({
            'start': current_time.isoformat(),
            'end': (current_time + timedelta(minutes=duration_mins)).isoformat()
        })
        
        # Move to next 30-minute slot
        current_time += timedelta(minutes=30)
    
    return slots

def is_within_business_hours(datetime_obj):
    """Check if a datetime is within business hours"""
    # Ensure datetime is timezone-aware
    if datetime_obj.tzinfo is None:
        # Assume IST timezone if not specified
        datetime_obj = datetime_obj.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    
    # Convert to IST for business hours check
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    if datetime_obj.tzinfo != ist_tz:
        datetime_obj = datetime_obj.astimezone(ist_tz)
    
    hour = datetime_obj.hour
    # Allow 9 AM to 6 PM (business hours)
    # Don't exclude lunch hour completely - just deprioritize it in scoring
    return 9 <= hour < 18

def format_datetime_for_output(datetime_str):
    """Ensure datetime string is in the correct output format"""
    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    # Convert to IST if needed
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return dt.isoformat()

def calculate_search_range(request_datetime, time_constraint=None):
    """Calculate the date range to search for available slots"""
    base_date = parse_datetime_string(request_datetime)
    
    # Ensure base_date has timezone info
    if base_date.tzinfo is None:
        base_date = base_date.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    
    if time_constraint:
        target_date, target_time = parse_time_constraint(time_constraint, base_date)
        if target_date:
            # Ensure target_date has same timezone as base_date
            if target_date.tzinfo is None:
                target_date = target_date.replace(tzinfo=base_date.tzinfo)
            # Search from the target date for 3 days
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=3)
        else:
            # Default: search for next 7 days
            start_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
    else:
        # Default: search for next 7 days
        start_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
    
    return start_date.isoformat(), end_date.isoformat()