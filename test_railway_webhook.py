#!/usr/bin/env python3
"""
Railway Webhook Tester
"""

import requests
import json

def test_railway_webhook():
    print("RAILWAY WEBHOOK TESTER")
    print("=" * 40)
    
    # Common Railway URL patterns for your project
    possible_urls = [
        "https://fastapi2-production.up.railway.app",
        "https://fast-api2-production.up.railway.app", 
        "https://chatapp-production.up.railway.app",
        "https://whatsapp-chatbot-production.up.railway.app"
    ]
    
    print("Checking possible Railway URLs...")
    
    working_url = None
    
    for base_url in possible_urls:
        webhook_url = f"{base_url}/webhook/whatsapp"
        
        print(f"\nTesting: {webhook_url}")
        
        try:
            # Test with GET first (should return 405 Method Not Allowed)
            response = requests.get(webhook_url, timeout=5)
            
            if response.status_code == 405:
                print(f"✓ FOUND: {base_url}")
                print("  Status: 405 Method Not Allowed (Expected for POST endpoint)")
                working_url = base_url
                break
            elif response.status_code == 200:
                print(f"✓ FOUND: {base_url}")
                print("  Status: 200 OK")
                working_url = base_url
                break
            else:
                print(f"  Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  Error: {e}")
    
    if working_url:
        print(f"\n🎉 SUCCESS! Your Railway app is running at:")
        print(f"   {working_url}")
        print(f"\n📋 WEBHOOK URL FOR TWILIO CONSOLE:")
        print(f"   {working_url}/webhook/whatsapp")
        return working_url
    else:
        print(f"\n❌ Could not find your Railway deployment")
        print(f"   Please check your Railway dashboard for the correct URL")
        return None

def test_webhook_endpoint(base_url):
    """Test the webhook endpoint with a sample message"""
    
    webhook_url = f"{base_url}/webhook/whatsapp"
    
    print(f"\n🧪 TESTING WEBHOOK ENDPOINT")
    print("=" * 40)
    
    # Simulate Twilio webhook payload
    test_payload = {
        'From': 'whatsapp:+5511999999999',
        'Body': 'Ola, teste do webhook!',
        'ProfileName': 'Test User',
        'To': 'whatsapp:+14155238886',
        'MessageSid': 'SM123456789test',
        'AccountSid': 'ACtest123456789'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'TwilioProxy/1.1'
    }
    
    try:
        print(f"Sending test message to: {webhook_url}")
        print(f"Test message: '{test_payload['Body']}'")
        
        response = requests.post(
            webhook_url,
            data=test_payload,
            headers=headers,
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                
                # Check response type
                if result.get('status') == 'bot_response':
                    print("\n✓ SUCCESS: Bot responded automatically!")
                elif result.get('status') == 'escalated_to_agent':
                    print("\n✓ SUCCESS: Message escalated to human agent!")
                else:
                    print(f"\n✓ SUCCESS: Webhook processed message")
                    
            except json.JSONDecodeError:
                print(f"Response (text): {response.text}")
                
            return True
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🚀 RAILWAY WEBHOOK TESTING")
    print("=" * 50)
    
    # Step 1: Find Railway URL
    base_url = test_railway_webhook()
    
    if not base_url:
        print("\n💡 TO FIND YOUR RAILWAY URL:")
        print("1. Go to railway.app dashboard")
        print("2. Click on your project")
        print("3. Go to Settings > Domains")
        print("4. Copy the public domain URL")
        return
    
    # Step 2: Test webhook endpoint
    success = test_webhook_endpoint(base_url)
    
    if success:
        print(f"\n🎉 WEBHOOK TEST SUCCESSFUL!")
        print(f"\n📋 NEXT STEPS:")
        print(f"1. Go to console.twilio.com")
        print(f"2. Navigate to Messaging > WhatsApp > Sandbox")
        print(f"3. Set webhook URL to: {base_url}/webhook/whatsapp")
        print(f"4. Set HTTP method to: POST")
        print(f"5. Test with real WhatsApp messages!")
    else:
        print(f"\n❌ WEBHOOK TEST FAILED")
        print(f"Check your Railway deployment and try again")

if __name__ == "__main__":
    main()