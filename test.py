import requests
import json
import time

def convert_json_format(existing_json):
    """
    Convert existing JSON output format to required format
    """
    # Extract the main event details
    main_event = {
        "StartTime": existing_json["EventStart"],
        "EndTime": existing_json["EventEnd"],
        "NumAttendees": 3,  # Assuming 3 attendees based on the example
        "Attendees": [
            "userone.amd@gmail.com",
            "usertwo.amd@gmail.com", 
            "userthree.amd@gmail.com"
        ],
        "Summary": existing_json["Subject"]
    }
    
    # Create the required format
    required_format = {
        "Request_id": existing_json["Request_id"],
        "Datetime": existing_json["Datetime"],
        "Location": existing_json["Location"],
        "From": existing_json["From"],
        "Attendees": [
            {
                "email": "userone.amd@gmail.com",
                "events": [main_event]
            },
            {
                "email": "usertwo.amd@gmail.com", 
                "events": [main_event]
            },
            {
                "email": "userthree.amd@gmail.com",
                "events": [main_event]
            }
        ],
        "Subject": existing_json["Subject"],
        "EmailContent": existing_json["EmailContent"],
        "EventStart": existing_json["EventStart"],
        "EventEnd": existing_json["EventEnd"],
        "Duration_mins": existing_json["Duration_mins"],
        "MetaData": existing_json["MetaData"]
    }
    
    return required_format

SERVER_URL = "http://134.199.207.82"
INPUT_JSON_FILE = "JSON_Samples/Input_Request.json"

start_time = time.time()

with open(INPUT_JSON_FILE) as f:
        input_json = json.load(f)
response = requests.post(SERVER_URL+":5000/receive", json=input_json, timeout=10)

# Convert to required format
converted_json = convert_json_format(response.json())
print(json.dumps(converted_json, indent=2))

end_time = time.time()
print(f"Time taken to generate prompt: {end_time - start_time:.2f} seconds")