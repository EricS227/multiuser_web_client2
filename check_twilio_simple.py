#!/usr/bin/env python3
"""
Simple Twilio Configuration Checker (no emojis)
"""

import os
from dotenv import load_dotenv
from twilio.rest import Client

def main():
    print("TWILIO CONFIGURATION CHECKER")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    load_dotenv('backend/.env')
    load_dotenv('backend/secret.env')
    
    # Get credentials
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
    
    print(f"\nCHECKING ENVIRONMENT VARIABLES:")
    print(f"TWILIO_ACCOUNT_SID: {'SET' if account_sid and account_sid != 'SEU_ACCOUNT_SID' else 'NOT SET'}")
    print(f"TWILIO_AUTH_TOKEN: {'SET' if auth_token and auth_token != 'SEU_AUTH_TOKEN' else 'NOT SET'}")
    print(f"TWILIO_WHATSAPP_FROM: {'SET' if whatsapp_from else 'NOT SET'}")
    
    if account_sid and auth_token and whatsapp_from:
        print(f"\nCONNECTION TEST:")
        try:
            client = Client(account_sid, auth_token)
            account = client.api.account.fetch()
            print(f"SUCCESS: Connected to Twilio")
            print(f"Account: {account.friendly_name}")
            print(f"Status: {account.status}")
            return True
        except Exception as e:
            print(f"ERROR: {e}")
            return False
    else:
        print("ERROR: Missing required environment variables")
        return False

if __name__ == "__main__":
    main()