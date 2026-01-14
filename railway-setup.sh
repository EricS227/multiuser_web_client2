#!/bin/bash

# Railway Environment Setup Script
echo "Setting up Railway environment variables..."

# Generate a secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Generated SECRET_KEY: $SECRET_KEY"
echo ""
echo "Please add these environment variables to your Railway project:"
echo ""
echo "1. Go to your Railway project dashboard"
echo "2. Navigate to Variables tab"  
echo "3. Add the following variables:"
echo ""
echo "SECRET_KEY=$SECRET_KEY"
echo "DATABASE_URL=\${{DATABASE_URL}} (Railway will provide this automatically)"
echo ""

# Optionally, if you have Railway CLI installed, you can set them directly:
if command -v railway &> /dev/null; then
    echo "Railway CLI detected. Would you like to set these variables automatically? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        railway variables set SECRET_KEY="$SECRET_KEY"
        echo "SECRET_KEY set successfully in Railway!"
        echo ""
        echo "Note: Make sure to also set your Twilio variables if using WhatsApp:"
        echo "TWILIO_ACCOUNT_SID=your_twilio_sid"
        echo "TWILIO_AUTH_TOKEN=your_twilio_token"
        echo "TWILIO_WHATSAPP_FROM=whatsapp:+your_twilio_number"
    fi
else
    echo "Railway CLI not found. Please set variables manually in Railway dashboard."
fi