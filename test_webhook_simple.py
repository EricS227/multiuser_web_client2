#!/usr/bin/env python3
"""
Simple Twilio Webhook Tester
"""

import requests
import json
from urllib.parse import urlencode

def test_webhook():
    webhook_url = "http://localhost:8000/webhook/whatsapp"
    
    print("TWILIO WEBHOOK TESTER")
    print("=" * 40)
    
    # Test messages
    test_cases = [
        ("Ola, boa tarde!", "Simple greeting"),
        ("Qual o horario de funcionamento?", "Business hours question"),  
        ("Preciso falar com um atendente", "Request for human agent"),
        ("Nao entendi", "User confusion - should escalate")
    ]
    
    test_phone = "+5511999887766"
    
    for message, description in test_cases:
        print(f"\nTEST: {description}")
        print(f"Message: '{message}'")
        print("-" * 30)
        
        # Twilio webhook payload
        payload = {
            'From': f'whatsapp:{test_phone}',
            'Body': message,
            'ProfileName': 'Test User',
            'To': 'whatsapp:+14155238886',
            'MessageSid': 'SM123456789',
            'AccountSid': 'AC123456789'
        }
        
        try:
            response = requests.post(
                webhook_url,
                data=urlencode(payload),
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Result: {json.dumps(result, indent=2)}")
                except:
                    print(f"Response: {response.text}")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Connection error: {e}")
            print("Make sure your FastAPI server is running:")
            print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
            break

if __name__ == "__main__":
    test_webhook()