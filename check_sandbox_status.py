#!/usr/bin/env python3
"""Check WhatsApp sandbox status and number verification"""

import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

load_dotenv()

def check_sandbox_status():
    """Check if number is joined to WhatsApp sandbox"""
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    test_number = "+554196950370"  # Your number from logs
    
    client = Client(account_sid, auth_token)
    
    try:
        # Try to send actual message to see specific error
        message = client.messages.create(
            body="Test message from bot",
            from_='whatsapp:+14155238886',
            to=f'whatsapp:{test_number}'
        )
        print(f"SUCCESS: Message sent! SID: {message.sid}")
        return True
        
    except TwilioRestException as e:
        print(f"Twilio Error Code: {e.code}")
        print(f"Error Message: {e.msg}")
        print(f"More Info: {e.more_info}")
        
        if e.code == 21614:
            print("\nSOLUTION:")
            print("1. Open WhatsApp")
            print("2. Send message to: +1 415 523 8886")
            print("3. Message content: join <your-sandbox-code>")
            print("4. You should get a confirmation message")
            
        return False

if __name__ == "__main__":
    print("Checking WhatsApp sandbox status...")
    print(f"Testing with number: +554196950370")
    print("-" * 40)
    check_sandbox_status()