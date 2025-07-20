#!/bin/bash
echo "Running AI Scheduling Assistant Tests..."
echo ""

# Check if both servers are running
VLLM_OK=false
FLASK_OK=false

if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "✓ vLLM server is running on port 3000"
    VLLM_OK=true
else
    echo "❌ vLLM server not found on port 3000"
fi

if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✓ Flask server is running on port 5000"
    FLASK_OK=true
else
    echo "❌ Flask server not found on port 5000"
fi

if [ "$VLLM_OK" = true ] && [ "$FLASK_OK" = true ]; then
    echo -e "\n✓ Both servers are running, starting tests...\n"
    python3 test_scheduler.py
else
    echo -e "\n❌ Please start both servers before running tests"
    echo "   Terminal 1: ./start_vllm.sh"
    echo "   Terminal 2: ./start_flask.sh"
fi
