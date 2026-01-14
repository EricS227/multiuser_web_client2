#!/usr/bin/env python3
"""
Test script to verify chatbot functionality locally
"""
import requests
import json

def test_webhook_local():
    """Test the WhatsApp webhook locally"""
    
    # Local server URL
    webhook_url = "http://localhost:8000/webhook/whatsapp"
    
    # Test message payload (simulates Twilio webhook)
    test_payload = {
        "From": "whatsapp:+5531999999999",
        "Body": "Olá, preciso de ajuda",
        "ProfileName": "Test User"
    }
    
    print("=== Testing ChatBot Webhook Locally ===")
    print(f"Webhook URL: {webhook_url}")
    print(f"Test payload: {test_payload}")
    
    try:
        # Send POST request to webhook
        response = requests.post(webhook_url, data=test_payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Webhook is working!")
        else:
            print("ERROR: Webhook returned error")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Is it running?")
        print("Start server with: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"ERROR: {e}")

def test_chatbot_status():
    """Test chatbot status endpoint"""
    
    # You'll need to get an admin token first
    print("=== Testing ChatBot Status ===")
    print("To test chatbot status, you need to:")
    print("1. Login as admin to get token")
    print("2. Use token to access /chatbot/status endpoint")
    print("3. Admin credentials: admin@test.com / senha123")

if __name__ == "__main__":
    print("ChatBot Test Suite")
    print("==================")
    print()
    
    test_webhook_local()
    print()
    test_chatbot_status()
    print()
    print("Next steps:")
    print("1. Start the server: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print("2. Run this test: python test_chatbot_local.py")
    print("3. For external testing, use ngrok: ngrok http 8000")