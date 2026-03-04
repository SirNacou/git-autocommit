#!/usr/bin/env python3
import os
import sys

# Test common free models
models = [
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free", 
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-4b:free",
    "google/gemma-3-4b-it:free",
]

api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
if not api_key:
    print("OPENROUTER_API_KEY not set")
    sys.exit(1)

import requests

for model in models:
    print(f"Testing {model}...")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say 'test'"}],
            },
            timeout=10,
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ WORKS!")
            print(f"  Response: {response.json()['choices'][0]['message']['content']}")
        else:
            print(f"  Error: {response.text[:100]}")
    except Exception as e:
        print(f"  Exception: {e}")
    print()
