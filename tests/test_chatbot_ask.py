#!/usr/bin/env python3
"""
Test script for chatbot ask endpoint
"""
import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
CHATBOT_ID = "15ef76de-454a-4278-a545-16d8a75f73a6"  # From the error log

def test_simple_endpoint():
    """Test a simple endpoint first"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to reach server...")
            response = requests.get(f"{BASE_URL}/health", timeout=15)
            print(f"Health endpoint status: {response.status_code}")
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print("Waiting 10 seconds before retry...")
                time.sleep(10)
    
    print("Cannot reach server after all attempts")
    return False

def test_chatbot_ask():
    """Test the chatbot ask endpoint"""
    url = f"{BASE_URL}/chatbot/{CHATBOT_ID}/ask"
    
    payload = {
        "question": "Hello, how are you?",
        "conversation_id": None
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Testing chatbot ask endpoint: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Success! Response: {json.dumps(response_data, indent=2)}")
        else:
            print(f"Error Response: {response.text[:500]}...")  # Truncate long error responses
            
    except requests.exceptions.Timeout:
        print("Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("Testing server connectivity...")
    if test_simple_endpoint():
        print("Server is reachable, testing chatbot endpoint...")
        test_chatbot_ask()
    else:
        print("Server is not reachable") 