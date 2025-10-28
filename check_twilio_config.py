#!/usr/bin/env python3
"""
Twilio Configuration Checker
Verifies your Twilio setup and credentials
"""

import os
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def load_environment():
    """Load environment variables from multiple sources"""
    
    # Try to load from various .env files
    env_files = ['.env', 'backend/.env', 'backend/secret.env']
    
    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"✓ Loaded environment from {env_file}")
            break
    else:
        print("⚠️  No .env file found, using system environment variables")

def check_twilio_credentials():
    """Check if Twilio credentials are configured and valid"""
    
    print("\nCHECKING TWILIO CREDENTIALS")
    print("=" * 50)
    
    # Get credentials from environment
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN") 
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
    
    # Check if credentials exist
    if not account_sid or account_sid == "SEU_ACCOUNT_SID":
        print("X TWILIO_ACCOUNT_SID not set or using placeholder")
        return False
        
    if not auth_token or auth_token == "SEU_AUTH_TOKEN":
        print("X TWILIO_AUTH_TOKEN not set or using placeholder")
        return False
        
    if not whatsapp_from:
        print("X TWILIO_WHATSAPP_FROM not set")
        return False
    
    print(f"✓ Account SID: {account_sid[:8]}...{account_sid[-4:]}")
    print(f"✓ Auth Token: {'*' * len(auth_token[:-4])}{auth_token[-4:]}")
    print(f"✓ WhatsApp From: {whatsapp_from}")
    
    # Test credentials by connecting to Twilio API
    try:
        print("\n🔍 Testing connection to Twilio API...")
        client = Client(account_sid, auth_token)
        
        # Try to get account info
        account = client.api.account.fetch()
        print(f"✓ Connected successfully!")
        print(f"  Account Name: {account.friendly_name}")
        print(f"  Account Status: {account.status}")
        
        return True
        
    except TwilioRestException as e:
        print(f"❌ Twilio API Error: {e}")
        print(f"   Error Code: {e.code}")
        print(f"   Error Message: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def check_whatsapp_sandbox():
    """Check WhatsApp Sandbox configuration"""
    
    print("\n📱 CHECKING WHATSAPP SANDBOX")
    print("=" * 50)
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    try:
        client = Client(account_sid, auth_token)
        
        # Get WhatsApp senders (sandbox numbers)
        senders = client.messaging.services.list()
        
        if senders:
            print(f"✓ Found {len(senders)} messaging services")
            for service in senders:
                print(f"  Service: {service.friendly_name} ({service.sid})")
        else:
            print("⚠️  No messaging services found")
        
        # Check for WhatsApp capability
        incoming_phone_numbers = client.incoming_phone_numbers.list(limit=10)
        
        whatsapp_numbers = [num for num in incoming_phone_numbers 
                           if 'whatsapp' in str(num.capabilities).lower()]
        
        if whatsapp_numbers:
            print(f"✓ Found {len(whatsapp_numbers)} WhatsApp-enabled numbers")
            for num in whatsapp_numbers:
                print(f"  Number: {num.phone_number}")
        else:
            print("⚠️  No WhatsApp-enabled numbers found")
            print("   Make sure you've activated WhatsApp Sandbox in Twilio Console")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking WhatsApp setup: {e}")
        return False

def test_webhook_url():
    """Test if your webhook URL is accessible"""
    
    print("\n🌐 TESTING WEBHOOK ACCESSIBILITY")
    print("=" * 50)
    
    # Test local webhook
    local_url = "http://localhost:8000/webhook/whatsapp"
    
    print(f"Testing local webhook: {local_url}")
    try:
        response = requests.get(local_url, timeout=5)
        if response.status_code == 405:  # Method not allowed is expected for GET on POST endpoint
            print("✓ Local webhook is accessible (405 Method Not Allowed is expected)")
        else:
            print(f"⚠️  Local webhook returned: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Local webhook not accessible: {e}")
        print("   Make sure your FastAPI server is running")
    
    # Check for Railway deployment URL
    print(f"\n📡 For production deployment:")
    print(f"   Your Railway webhook URL should be:")
    print(f"   https://your-app.railway.app/webhook/whatsapp")
    print(f"   Configure this URL in Twilio Console > WhatsApp > Sandbox")

def check_environment_setup():
    """Check overall environment setup"""
    
    print("\n⚙️  ENVIRONMENT SETUP CHECK")
    print("=" * 50)
    
    required_vars = [
        "SECRET_KEY",
        "TWILIO_ACCOUNT_SID", 
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_FROM"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "TOKEN" in var or "KEY" in var:
                display_value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "****"
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Create a .env file or set these in your environment")
        return False
    
    return True

def main():
    """Run all configuration checks"""
    
    print("TWILIO CONFIGURATION CHECKER")
    print("=" * 60)
    
    # Load environment
    load_environment()
    
    # Run checks
    checks = [
        ("Environment Setup", check_environment_setup),
        ("Twilio Credentials", check_twilio_credentials), 
        ("WhatsApp Sandbox", check_whatsapp_sandbox),
        ("Webhook URL", test_webhook_url)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n📊 CONFIGURATION SUMMARY")
    print("=" * 60)
    
    for check_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} {check_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED!")
        print("Your Twilio integration is properly configured.")
        print("\nNext steps:")
        print("1. Run: python test_twilio_webhook.py")
        print("2. Test with real WhatsApp messages")
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("Please fix the issues above before testing")

if __name__ == "__main__":
    main()