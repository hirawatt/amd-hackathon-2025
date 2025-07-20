import requests
import json
import time

def test_scheduling_assistant(server_url="http://localhost:5001"):
    """Test the AI Scheduling Assistant with sample requests"""
    
    # Test Case 1: All attendees available
    test_case_1 = {
        "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
        "Datetime": "19-07-2025T12:34:55",
        "Location": "IISc Bangalore",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Agentic AI Project Status Update",
        "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the status of Agentic AI Project."
    }
    
    # Test Case 2: Urgent meeting
    test_case_2 = {
        "Request_id": "6118b54f-907b-4451-8d48-dd13d76033b5",
        "Datetime": "19-07-2025T12:34:55",
        "Location": "IISc Bangalore",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Client Validation - Urgent",
        "EmailContent": "Hi Team. We've just received quick feedback from the client indicating that the instructions we provided aren't working on their end. Let's prioritize resolving this promptly. Let's meet Monday at 9:00 AM to discuss and resolve this issue."
    }
    
    # Test Case 3: Specific time request
    test_case_3 = {
        "Request_id": "6118b54f-907b-4451-8d48-dd13d76033c5",
        "Datetime": "19-07-2025T12:34:55",
        "Location": "IISc Bangalore",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Project Status",
        "EmailContent": "Hi Team. Let's meet on Tuesday at 11:00 A.M and discuss about our on-going Projects."
    }
    
    test_cases = [
        ("Test Case 1: Regular meeting", test_case_1),
        ("Test Case 2: Urgent meeting with specific time", test_case_2)
    ]
    
    print("Testing AI Scheduling Assistant")
    print("=" * 50)
    
    for test_name, test_data in test_cases:
        print(f"\n{test_name}")
        print("-" * 50)
        
        try:
            # Send request
            start_time = time.time()
            response = requests.post(f"{server_url}/receive", json=test_data, timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success! Response time: {end_time - start_time:.2f} seconds")
                print(f"  Scheduled: {result.get('EventStart', 'N/A')} to {result.get('EventEnd', 'N/A')}")
                print(f"  Duration: {result.get('Duration_mins', 'N/A')} minutes")
            else:
                print(f"✗ Failed with status code: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except requests.exceptions.Timeout:
            print("✗ Request timed out (>10 seconds)")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

def validate_response_format(response_data):
    """Validate that the response matches the expected format"""
    required_fields = [
        "Request_id", "Datetime", "Location", "From", "Attendees",
        "Subject", "EmailContent", "EventStart", "EventEnd", "Duration_mins", "MetaData"
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in response_data:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"Missing required fields: {missing_fields}")
        return False
    
    # Check Attendees structure
    if isinstance(response_data["Attendees"], list):
        for attendee in response_data["Attendees"]:
            if "email" not in attendee or "events" not in attendee:
                print("Invalid attendee structure")
                return False
    
    return True

if __name__ == "__main__":
    import sys
    
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001"
    
    print(f"Testing server at: {server_url}")
    
    # First check if server is running
    try:
        health_check = requests.get(f"{server_url}/health", timeout=5)
        if health_check.status_code == 200:
            print("✓ Server is healthy")
        else:
            print("✗ Server health check failed")
    except:
        print("✗ Cannot connect to server. Make sure it's running!")
        exit(1)
    
    # Run tests
    test_scheduling_assistant(server_url)