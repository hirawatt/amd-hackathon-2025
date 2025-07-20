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
