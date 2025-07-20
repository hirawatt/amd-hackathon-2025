#!/usr/bin/env python3
"""Debug script to test vLLM connection and responses"""

import requests
import json
from openai import OpenAI

# Test 1: Check if vLLM is running
print("1. Testing vLLM server connection...")
try:
    response = requests.get("http://localhost:3000/health")
    print(f"   ✓ vLLM health check: {response.status_code}")
except Exception as e:
    print(f"   ✗ vLLM not reachable: {e}")
    exit(1)

# Test 2: Check vLLM models endpoint
print("\n2. Checking available models...")
try:
    response = requests.get("http://localhost:3000/v1/models")
    models = response.json()
    print(f"   ✓ Models endpoint working")
    print(f"   Available models: {json.dumps(models, indent=2)}")
except Exception as e:
    print(f"   ✗ Models endpoint failed: {e}")

# Test 3: Test OpenAI client
print("\n3. Testing OpenAI client...")
try:
    client = OpenAI(api_key="NULL", base_url="http://localhost:3000/v1")
    
    # Simple test prompt
    test_prompt = "Say 'hello world' and nothing else."
    
    print(f"   Sending test prompt: {test_prompt}")
    
    response = client.chat.completions.create(
        model="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat",
        temperature=0.0,
        messages=[{
            "role": "user",
            "content": test_prompt
        }]
    )
    
    print(f"   ✓ Response received:")
    print(f"   Content: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"   ✗ OpenAI client failed: {e}")
    print(f"   Error type: {type(e).__name__}")

# Test 4: Test JSON parsing
print("\n4. Testing JSON extraction...")
try:
    client = OpenAI(api_key="NULL", base_url="http://localhost:3000/v1")
    
    json_prompt = """
    Return only valid JSON with no extra text:
    {"duration": 30, "urgency": "normal"}
    """
    
    response = client.chat.completions.create(
        model="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat",
        temperature=0.0,
        messages=[{
            "role": "user",
            "content": json_prompt
        }]
    )
    
    content = response.choices[0].message.content
    print(f"   Raw response: {repr(content)}")
    
    try:
        parsed = json.loads(content)
        print(f"   ✓ JSON parsed successfully: {parsed}")
    except json.JSONDecodeError as je:
        print(f"   ✗ JSON parse failed: {je}")
        print(f"   Response was: {content}")
        
except Exception as e:
    print(f"   ✗ Test failed: {e}")

# Test 5: Test with actual meeting prompt
print("\n5. Testing actual meeting extraction...")
try:
    client = OpenAI(api_key="NULL", base_url="http://localhost:3000/v1")
    
    meeting_prompt = """
    Extract meeting duration from this text and return ONLY valid JSON:
    "Let's meet for 30 minutes"
    
    Return format: {"duration_mins": NUMBER}
    """
    
    response = client.chat.completions.create(
        model="/home/user/Models/deepseek-ai/deepseek-llm-7b-chat",
        temperature=0.0,
        max_tokens=50,
        messages=[{
            "role": "user", 
            "content": meeting_prompt
        }]
    )
    
    content = response.choices[0].message.content
    print(f"   Raw response: {repr(content)}")
    
    # Try to extract JSON from response
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        parsed = json.loads(json_str)
        print(f"   ✓ Extracted JSON: {parsed}")
    else:
        print(f"   ✗ No JSON found in response")
        
except Exception as e:
    print(f"   ✗ Meeting test failed: {e}")

print("\n" + "="*50)
print("Debug complete. Check the results above.")
print("="*50)