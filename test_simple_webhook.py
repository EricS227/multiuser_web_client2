#!/usr/bin/env python3
"""
Simple webhook test without external dependencies
"""
import requests
import json

def test_simple_webhook():
    """Test webhook with direct HTTP call"""
    
    webhook_url = "http://localhost:8000/webhook/whatsapp"
    
    # Simple test payload
    payload = {
        "From": "whatsapp:+5531999999999",
        "Body": "hello test",
        "ProfileName": "TestUser"
    }
    
    print("Testing simple webhook...")
    print(f"URL: {webhook_url}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(webhook_url, data=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Webhook responded!")
        else:
            print("FAILED: Got error response")
            
    except requests.exceptions.Timeout:
        print("TIMEOUT: Webhook took too long to respond")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_simple_webhook()