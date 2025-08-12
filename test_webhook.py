#!/usr/bin/env python3
"""
Test script for Twilio WhatsApp webhook on Railway
"""
import requests
import sys
from urllib.parse import quote

def test_webhook(railway_url, test_message="Hello Bot!", from_number="+5511999999999", profile_name="TestUser"):
    """Test the WhatsApp webhook endpoint"""
    
    webhook_url = f"{railway_url}/webhook/whatsapp"
    
    # Prepare form data as Twilio sends it
    data = {
        'From': f'whatsapp:{from_number}',
        'Body': test_message,
        'ProfileName': profile_name
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    print(f"Testing webhook: {webhook_url}")
    print(f"Message: {test_message}")
    print(f"From: {from_number}")
    print("=" * 50)
    
    try:
        response = requests.post(webhook_url, data=data, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook is working!")
            try:
                json_response = response.json()
                print(f"Bot Status: {json_response.get('status')}")
                print(f"Bot Response: {json_response.get('response', 'No response field')}")
            except:
                print("Response is not JSON format")
        else:
            print("❌ Webhook failed!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to webhook: {e}")
        return False
    
    return response.status_code == 200

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_webhook.py <railway_url>")
        print("Example: python test_webhook.py https://your-app.railway.app")
        sys.exit(1)
    
    railway_url = sys.argv[1].rstrip('/')
    
    # Test different message types
    test_cases = [
        ("Olá", "Greeting test"),
        ("Qual o horário?", "Business hours test"),  
        ("Quanto custa?", "Pricing test"),
        ("Quero falar com atendente", "Escalation test"),
        ("Random message", "Default response test")
    ]
    
    print("🤖 Testing Twilio WhatsApp Chatbot")
    print("=" * 50)
    
    success_count = 0
    for message, description in test_cases:
        print(f"\n📝 {description}")
        if test_webhook(railway_url, message):
            success_count += 1
        print("-" * 30)
    
    print(f"\n📊 Results: {success_count}/{len(test_cases)} tests passed")
    
    if success_count == len(test_cases):
        print("🎉 All tests passed! Your chatbot is ready for WhatsApp!")
    else:
        print("⚠️  Some tests failed. Check Railway logs and Twilio configuration.")

if __name__ == "__main__":
    main()