#!/bin/bash

echo "AI Scheduling Assistant - Jupyter Setup Script"
echo "============================================="
echo ""

# Get current directory name
CURRENT_DIR=$(pwd)
echo "Setting up in: $CURRENT_DIR"
echo ""

# Step 1: Check if we're in the right directory
if [ ! -f "main_submission.py" ]; then
    echo "❌ Error: main_submission.py not found!"
    echo "   Please run this script from your solution directory"
    echo "   Example: cd /home/user/tanmay/solution_tan"
    exit 1
fi

# Step 2: Check Python dependencies
echo "1. Checking Python dependencies..."
python3 -c "import flask" 2>/dev/null && echo "   ✓ Flask installed" || echo "   ❌ Flask missing"
python3 -c "import openai" 2>/dev/null && echo "   ✓ OpenAI installed" || echo "   ❌ OpenAI missing"
python3 -c "import google.auth" 2>/dev/null && echo "   ✓ Google Auth installed" || echo "   ❌ Google Auth missing"
python3 -c "import vllm" 2>/dev/null && echo "   ✓ vLLM installed" || echo "   ❌ vLLM missing"

# Step 3: Check GPU status
echo -e "\n2. Checking GPU status..."
rocm-smi | grep -E "GPU%|VRAM%" | head -5

# Step 4: Check for Google tokens
echo -e "\n3. Checking for Google Auth tokens..."
if [ -d "Keys" ]; then
    TOKEN_COUNT=$(ls Keys/*.token 2>/dev/null | wc -l)
    if [ $TOKEN_COUNT -gt 0 ]; then
        echo "   ✓ Found $TOKEN_COUNT token file(s) in Keys/"
        ls Keys/*.token | head -5
        
        # Create copies if needed
        if [ $TOKEN_COUNT -eq 1 ] && [ -f "Keys/userone.amd.token" ]; then
            echo "   ⚠️  Only one token found, creating copies for testing..."
            cp Keys/userone.amd.token Keys/usertwo.amd.token 2>/dev/null
            cp Keys/userone.amd.token Keys/userthree.amd.token 2>/dev/null
            echo "   ✓ Created test tokens"
        fi
    else
        echo "   ❌ No token files found in Keys/"
        echo "   Please copy .token files to Keys/ directory"
    fi
else
    echo "   ❌ Keys directory not found"
    mkdir -p Keys
    echo "   ✓ Created Keys directory"
fi

# Step 5: Check model availability
echo -e "\n4. Checking AI models..."
MODEL_PATH="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"
if [ -d "$MODEL_PATH" ]; then
    echo "   ✓ DeepSeek model found"
    du -sh "$MODEL_PATH" | awk '{print "   Model size: " $1}'
else
    echo "   ❌ DeepSeek model not found at $MODEL_PATH"
fi

# Step 6: Create start scripts
echo -e "\n5. Creating start scripts..."

# vLLM start script with dynamic GPU memory allocation
cat > start_vllm.sh << 'EOF'
#!/bin/bash
echo "Starting vLLM server..."
echo "Checking GPU availability..."

# Get current GPU memory usage
GPU_USAGE=$(rocm-smi --showmeminfo vram | grep -E "GPU\[0\]" -A 2 | grep "Used" | awk '{print $3}' | sed 's/%//')

if [ -z "$GPU_USAGE" ]; then
    GPU_USAGE=50
fi

echo "Current GPU memory usage: ${GPU_USAGE}%"

# Calculate available memory fraction
if [ $GPU_USAGE -gt 80 ]; then
    MEMORY_FRACTION=0.15
    echo "⚠️  High GPU usage detected, using only 15% memory"
elif [ $GPU_USAGE -gt 60 ]; then
    MEMORY_FRACTION=0.3
    echo "⚠️  Moderate GPU usage, using 30% memory"
else
    MEMORY_FRACTION=0.5
    echo "✓ Normal GPU usage, using 50% memory"
fi

echo "Starting vLLM with ${MEMORY_FRACTION} GPU memory utilization..."

HIP_VISIBLE_DEVICES=0 vllm serve /home/user/Models/deepseek-ai/deepseek-llm-7b-chat \
    --gpu-memory-utilization $MEMORY_FRACTION \
    --swap-space 16 \
    --disable-log-requests \
    --dtype float16 \
    --max-model-len 2048 \
    --tensor-parallel-size 1 \
    --host 0.0.0.0 \
    --port 3000 \
    --num-scheduler-steps 10 \
    --max-num-seqs 64 \
    --distributed-executor-backend "mp"
EOF

# Flask start script
cat > start_flask.sh << 'EOF'
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
EOF

# Test script
cat > run_tests.sh << 'EOF'
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
EOF

chmod +x start_vllm.sh start_flask.sh run_tests.sh
echo "   ✓ Created start_vllm.sh"
echo "   ✓ Created start_flask.sh"
echo "   ✓ Created run_tests.sh"

# Step 7: Test Python imports
echo -e "\n6. Testing Python imports..."
python3 -c "from src.ai_agent import AISchedulingAgent; print('   ✓ AI Agent module OK')" 2>/dev/null || echo "   ❌ AI Agent import failed"
python3 -c "from src.calendar_integration import CalendarManager; print('   ✓ Calendar module OK')" 2>/dev/null || echo "   ❌ Calendar import failed"
python3 -c "from src.meeting_scheduler import MeetingScheduler; print('   ✓ Scheduler module OK')" 2>/dev/null || echo "   ❌ Scheduler import failed"

# Step 8: Display instructions
echo -e "\n" 
echo "============================================="
echo "SETUP COMPLETE! 🎉"
echo "============================================="
echo ""
echo "📋 QUICK START INSTRUCTIONS:"
echo ""
echo "1. Open 3 terminals in Jupyter"
echo ""
echo "2. Terminal 1 - Start vLLM (AI Model Server):"
echo "   cd $CURRENT_DIR"
echo "   ./start_vllm.sh"
echo ""
echo "3. Terminal 2 - Start Flask (Your App):"
echo "   cd $CURRENT_DIR"
echo "   ./start_flask.sh"
echo ""
echo "4. Terminal 3 - Run Tests:"
echo "   cd $CURRENT_DIR"
echo "   ./run_tests.sh"
echo ""
echo "============================================="
echo "🔍 TROUBLESHOOTING:"
echo ""
echo "- If vLLM fails: Try using less GPU memory or wait for GPU to free up"
echo "- If Flask fails: Check if port 5000 is already in use"
echo "- If tests fail: Make sure both servers are running"
echo ""
echo "📡 Your external IP for testing: $(hostname -I | awk '{print $1}')"
echo "   Test from laptop: curl http://$(hostname -I | awk '{print $1}'):5000/health"
echo ""
echo "============================================="