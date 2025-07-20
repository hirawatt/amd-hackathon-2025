#!/bin/bash
echo "Starting AI Scheduling Assistant..."
echo "Server will be available at http://0.0.0.0:5000"
echo ""

# Check if vLLM is running
if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: vLLM server not detected on port 3000"
    echo "   Make sure to start vLLM first in another terminal!"
    echo ""
fi

python3 main_submission.py
