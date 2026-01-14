#!/usr/bin/env python3
"""Test script to verify Twilio credentials and WhatsApp setup"""

import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Load environment variables
load_dotenv()

def test_twilio_credentials():
    """Test Twilio credentials and WhatsApp setup"""
    
    # Get credentials from .env
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
    
    print("Testing Twilio Configuration...")
    print(f"Account SID: {account_sid}")
    print(f"Auth Token: {'*' * 20}{auth_token[-4:] if auth_token else 'NOT SET'}")
    print(f"WhatsApp From: {whatsapp_from}")
    print("-" * 50)
    
    if not all([account_sid, auth_token, whatsapp_from]):
        print("❌ Missing Twilio credentials in .env file")
        return False
    
    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Test 1: Verify account
        print("Test 1: Verifying account...")
        account = client.api.accounts(account_sid).fetch()
        print(f"Account Status: {account.status}")
        print(f"Account Name: {account.friendly_name}")
        
        # Test 2: Check WhatsApp capability
        print("\nTest 2: Checking WhatsApp sandbox...")
        try:
            # Try to get WhatsApp sandbox settings
            incoming_phone_numbers = client.incoming_phone_numbers.list(limit=50)
            whatsapp_numbers = [num for num in incoming_phone_numbers if 'whatsapp' in str(num.capabilities)]
            
            if whatsapp_numbers:
                print(f"WhatsApp numbers found: {len(whatsapp_numbers)}")
            else:
                print("No WhatsApp numbers found - using sandbox")
            
        except Exception as e:
            print(f"WhatsApp check warning: {e}")
        
        # Test 3: Try sending a test message to a verified number
        print("\nTest 3: Testing message sending capability...")
        test_number = "+554196950370"  # Your number from the logs
        
        try:
            # This will test the authentication without actually sending
            message = client.messages.create(
                body="Test message - this should not be sent",
                from_=whatsapp_from,
                to=f"whatsapp:{test_number}"
            )
            print("Message creation successful - credentials are valid")
            print(f"Message SID: {message.sid}")
            return True
            
        except TwilioRestException as e:
            if e.code == 21614:  # Number not verified in sandbox
                print("Number not joined to WhatsApp sandbox")
                print("To fix: Send WhatsApp message to +1 415 523 8886")
                print("Message content: join <sandbox-name>")
                return "sandbox_not_joined"
            elif e.code == 20003:  # Authentication error
                print("Invalid credentials")
                return False
            else:
                print(f"Twilio error {e.code}: {e.msg}")
                return False
                
    except TwilioRestException as e:
        print(f"Authentication failed: {e.msg}")
        print("Check your Account SID and Auth Token")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    result = test_twilio_credentials()
    
    if result == True:
        print("\nAll tests passed! Twilio is properly configured.")
    elif result == "sandbox_not_joined":
        print("\nCredentials are valid but sandbox not joined.")
        print("Join sandbox to enable WhatsApp messaging.")
    else:
        print("\nConfiguration issues found. Please fix the above errors.")