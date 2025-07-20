from flask import Flask, request, jsonify
from threading import Thread
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.meeting_scheduler import MeetingScheduler

app = Flask(__name__)
received_data = []

# Initialize the meeting scheduler
meeting_scheduler = MeetingScheduler()

def your_meeting_assistant(data):
    """Main function called by the submission system"""
    try:
        # Use the meeting scheduler to process the request
        result = meeting_scheduler.schedule_meeting(data)
        return result
    except Exception as e:
        print(f"Error in your_meeting_assistant: {e}")
        # Return minimal valid response
        return {
            "Request_id": data.get("Request_id", ""),
            "Datetime": data.get("Datetime", ""),
            "Location": data.get("Location", ""),
            "From": data.get("From", ""),
            "Attendees": data.get("Attendees", []),
            "Subject": data.get("Subject", ""),
            "EmailContent": data.get("EmailContent", ""),
            "EventStart": "",
            "EventEnd": "",
            "Duration_mins": "",
            "MetaData": {"error": str(e)}
        }

@app.route('/receive', methods=['POST'])
def receive():
    """Endpoint to receive meeting requests"""
    try:
        data = request.get_json()
        print(f"\n Received: {json.dumps(data, indent=2)}")
        
        # Process the meeting request
        new_data = your_meeting_assistant(data)
        
        # Store for debugging
        received_data.append({
            "input": data,
            "output": new_data
        })
        
        print(f"\n\n\n Sending:\n {json.dumps(new_data, indent=2)}")
        return jsonify(new_data)
    
    except Exception as e:
        print(f"Error in receive endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "AI Scheduling Assistant"})

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify server is running"""
    return jsonify({
        "message": "AI Scheduling Assistant is running",
        "endpoints": ["/receive", "/health", "/test"],
        "total_requests_processed": len(received_data)
    })

def run_flask():
    """Run the Flask server"""
    app.run(host='0.0.0.0', port=5001, debug=True)

if __name__ == "__main__":
    print("Starting AI Scheduling Assistant Server...")
    print("Server will be available at http://0.0.0.0:5001")
    print("Endpoints:")
    print("  - POST /receive - Submit meeting requests")
    print("  - GET /health - Health check")
    print("  - GET /test - Test server status")
    
    # For production, run directly
    # For development/testing, can use threading
    run_flask()
    
    # Alternative: Run in background thread
    # Thread(target=run_flask, daemon=True).start()
    # print("Server started in background thread")