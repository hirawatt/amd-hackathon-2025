import json
from openai import OpenAI
from datetime import datetime, timedelta
import re

class AISchedulingAgent:
    def __init__(self, base_url="http://localhost:3000/v1", model_path="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"):
        self.base_url = base_url
        self.model_path = model_path
        self.client = OpenAI(api_key="NULL", base_url=base_url, timeout=None, max_retries=0)
    
    def parse_email(self, email_content):
        """Extract meeting details from email content"""
        try:
            print(f"[AI Agent] Parsing email: {email_content[:100]}...")
            response = self.client.chat.completions.create(
                model=self.model_path,
                temperature=0.0,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f""".
                    You are an AI Agent that helps in scheduling meetings.
                    Extract the following information from the email:
                    1. List of participant email addresses (comma-separated)
                    2. Meeting duration in minutes
                    3. Time constraints (e.g., 'next week', 'Thursday', 'Monday at 9:00 AM')
                    4. Meeting urgency (normal/urgent)
                    
                    If participant names are given without email domains, append @amd.com
                    Return ONLY valid JSON with keys: 'participants', 'duration_mins', 'time_constraints', 'urgency'
                    
                    Email: {email_content}
                    """
                }]
            )
            
            content = response.choices[0].message.content.strip()
            print(f"[AI Agent] Raw response: {content}")
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                # Ensure duration_mins is an integer
                if 'duration_mins' in result:
                    result['duration_mins'] = int(result['duration_mins'])
                print(f"[AI Agent] Parsed result: {result}")
                return result
            else:
                # Fallback if no JSON found
                print(f"Warning: No JSON in AI response: {content}")
                return {
                    'participants': '',
                    'duration_mins': 30,
                    'time_constraints': '',
                    'urgency': 'normal'
                }
                
        except Exception as e:
            print(f"Error in parse_email: {e}")
            # Return default values
            return {
                'participants': '',
                'duration_mins': 30,
                'time_constraints': '',
                'urgency': 'normal'
            }
    
    def extract_datetime_preference(self, email_content, request_datetime):
        """Extract specific datetime preferences from email"""
        try:
            print(f"[AI Agent] Extracting datetime preference from: {email_content[:100]}...")
            response = self.client.chat.completions.create(
                model=self.model_path,
                temperature=0.0,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""
                    Current datetime: {request_datetime}
                    
                    Extract the preferred meeting date and time from this email.
                    Consider phrases like:
                    - "next Thursday" 
                    - "Monday at 9:00 AM"
                    - "Tuesday at 11:00 A.M"
                    - "tomorrow"
                    - "ASAP" or "urgent" (means schedule at earliest available)
                    
                    For "Monday at 9:00 AM", extract:
                    - Day: Monday (next occurrence from current date)
                    - Time: 09:00 (24-hour format)
                    
                    Return ONLY JSON with:
                    - preferred_date: YYYY-MM-DD format (null if not specific)
                    - preferred_time: HH:MM format in 24-hour (e.g., "09:00" for 9 AM)
                    - is_specific_time: true if specific time like "9:00 AM" mentioned
                    - day_of_week: monday/tuesday/etc if mentioned (lowercase)
                    - urgency: urgent/normal based on keywords like URGENT, ASAP, promptly
                    
                    Email: {email_content}
                    """
                }]
            )
            
            content = response.choices[0].message.content.strip()
            print(f"[AI Agent] Datetime extraction response: {content}")
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                print(f"[AI Agent] Extracted datetime preferences: {result}")
                return result
            else:
                print(f"[AI Agent] No JSON found in datetime extraction")
                return {'preferred_date': None, 'preferred_time': None, 'is_specific_time': False}
                
        except Exception as e:
            print(f"Error in extract_datetime_preference: {e}")
            return {'preferred_date': None, 'preferred_time': None, 'is_specific_time': False}
    
    def suggest_meeting_time(self, available_slots, duration_mins, preferences=None):
        """Use AI to suggest the best meeting time from available slots"""
        try:
            if not available_slots:
                return {'selected_slot_number': 1, 'reason': 'No slots available'}
                
            slots_str = "\n".join([f"{i+1}. {slot['start']} to {slot['end']}" for i, slot in enumerate(available_slots[:10])])
            
            # Extract preference details
            urgency = preferences.get('urgency', 'normal') if isinstance(preferences, dict) else 'normal'
            time_constraints = preferences.get('time_constraints', '') if isinstance(preferences, dict) else str(preferences)
            preferred_time = preferences.get('preferred_time', '') if isinstance(preferences, dict) else ''
            email_content = preferences.get('email_content', '') if isinstance(preferences, dict) else ''
            
            prompt = f"""
            You are an intelligent meeting scheduler. Select the BEST time slot based on the meeting request.
            
            Meeting Request: {email_content}
            
            Available slots:
            {slots_str}
            
            Meeting details:
            - Duration: {duration_mins} minutes
            - Urgency: {urgency}
            - Time constraints: {time_constraints}
            - Preferred time: {preferred_time}
            
            Selection criteria:
            1. For URGENT meetings: Choose the EARLIEST available slot
            2. If specific time requested (e.g., "9:00 AM"): Choose slot matching that time
            3. If specific day requested (e.g., "Monday"): Choose slot on that day
            4. Consider business hours (9 AM - 6 PM)
            5. Prefer morning slots (9-11 AM) for important meetings
            6. Avoid lunch time (12-1 PM) unless necessary
            
            STRICTLY Return ONLY JSON with:
            - selected_slot_number: (1-based index of best slot)
            - reason: brief explanation of why this slot was chosen
            """
            
            response = self.client.chat.completions.create(
                model=self.model_path,
                temperature=0.0,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                # Default to first slot
                return {'selected_slot_number': 1, 'reason': 'Selected first available slot'}
                
        except Exception as e:
            print(f"Error in suggest_meeting_time: {e}")
            return {'selected_slot_number': 1, 'reason': 'Error occurred, using first slot'}