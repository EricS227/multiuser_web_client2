#!/usr/bin/env python3
"""
Test script for Twilio WhatsApp webhook integration
This script simulates Twilio webhook calls to test your chatbot
"""

import requests
import json
import time
from urllib.parse import urlencode

class TwilioWebhookTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.webhook_url = f"{base_url}/webhook/whatsapp"
    
    def simulate_twilio_webhook(self, from_number, message_body, profile_name="Test User"):
        """
        Simulate a Twilio WhatsApp webhook call
        This mimics what Twilio sends to your webhook endpoint
        """
        
        # Twilio sends form data, not JSON
        payload = {
            'From': f'whatsapp:{from_number}',
            'Body': message_body,
            'ProfileName': profile_name,
            'To': 'whatsapp:+14155238886',  # Your Twilio number
            'MessageSid': f'SM{int(time.time())}test',
            'AccountSid': 'ACtest123',
            'NumMedia': '0'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TwilioProxy/1.1'
        }
        
        try:
            print(f"Sending message: '{message_body}' from {from_number}")
            response = requests.post(
                self.webhook_url,
                data=urlencode(payload),
                headers=headers,
                timeout=10
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Result: {json.dumps(result, indent=2)}")
                    return result
                except:
                    print(f"Response (text): {response.text}")
                    return {"status": "success", "response": response.text}
            else:
                print(f"ERROR: {response.status_code} - {response.text}")
                return {"status": "error", "code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"Connection Error: {e}")
            return {"status": "connection_error", "error": str(e)}
    
    def test_chatbot_scenarios(self):
        """Test various chatbot scenarios"""
        
        test_phone = "+5511999887766"
        
        test_cases = [
            ("Ola, boa tarde!", "Greeting - should get bot response"),
            ("Qual o horario de funcionamento?", "FAQ - should get bot response"), 
            ("Quanto custa o servico?", "Pricing - should get bot response or escalate"),
            ("Preciso falar com um atendente", "Direct escalation request"),
            ("Nao entendi sua resposta", "Frustration - should escalate"),
            ("Tenho um problema urgente", "Urgent issue - should escalate"),
            ("Quero um reembolso", "Complex issue - should escalate")
        ]
        
        print("=" * 60)
        print("TESTING CHATBOT SCENARIOS")
        print("=" * 60)
        
        results = []
        
        for i, (message, description) in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {description}")
            print("-" * 50)
            
            result = self.simulate_twilio_webhook(test_phone, message)
            results.append({
                "test": description,
                "message": message,
                "result": result
            })
            
            # Wait between tests to simulate real conversation
            time.sleep(2)
        
        return results
    
    def test_webhook_health(self):
        """Test if webhook endpoint is responding"""
        
        print("=" * 60)
        print("TESTING WEBHOOK HEALTH")
        print("=" * 60)
        
        try:
            # Test with minimal valid payload
            response = requests.post(
                self.webhook_url,
                data=urlencode({
                    'From': 'whatsapp:+5511999999999',
                    'Body': 'test',
                    'ProfileName': 'Health Check'
                }),
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=5
            )
            
            print(f"Webhook Status: {'✓ HEALTHY' if response.status_code == 200 else '✗ UNHEALTHY'}")
            print(f"Response Code: {response.status_code}")
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            print(f"Webhook Status: ✗ UNREACHABLE")
            print(f"Error: {e}")
            return False

def test_local_server():
    """Test against local development server"""
    print("TESTING LOCAL SERVER (localhost:8000)")
    print("=" * 60)
    
    tester = TwilioWebhookTester("http://localhost:8000")
    
    # Health check first
    if not tester.test_webhook_health():
        print("\n❌ Local server is not running!")
        print("Start your server with: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    # Run chatbot tests
    results = tester.test_chatbot_scenarios()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for result in results:
        status = "✓" if result["result"].get("status") != "error" else "✗"
        print(f"{status} {result['test']}: {result['message']}")
    
    return True

def test_railway_deployment():
    """Test against Railway deployment"""
    print("\nTESTING RAILWAY DEPLOYMENT")
    print("=" * 60)
    
    # You'll need to update this URL with your actual Railway deployment URL
    railway_url = "https://your-app.railway.app"
    
    print(f"⚠️  Update railway_url in script to your actual Railway URL:")
    print(f"    Current: {railway_url}")
    print(f"    Expected: https://your-project-name.railway.app")
    
    # Uncomment below once you update the URL
    # tester = TwilioWebhookTester(railway_url)
    # tester.test_webhook_health()
    # tester.test_chatbot_scenarios()

def main():
    print("🚀 TWILIO WEBHOOK TESTER")
    print("=" * 60)
    print("This script simulates Twilio WhatsApp webhook calls")
    print("to test your enhanced chatbot integration.")
    print()
    
    # Test local server
    success = test_local_server()
    
    if success:
        print("\n✅ LOCAL TESTS COMPLETED SUCCESSFULLY!")
        
        print("\n📋 NEXT STEPS FOR PRODUCTION:")
        print("1. Deploy to Railway (if not already done)")
        print("2. Update Twilio Console webhook URL to:")
        print("   https://your-app.railway.app/webhook/whatsapp")
        print("3. Test with real WhatsApp messages")
        print("4. Monitor chatbot analytics at /chatbot/analytics")
        
        # Test Railway deployment
        test_railway_deployment()
    
    else:
        print("\n❌ LOCAL TESTS FAILED")
        print("Please check your FastAPI server is running")

if __name__ == "__main__":
    main()