# WhatsApp Chatbot Testing Guide

## Complete Setup for WhatsApp Integration Testing

### 1. Prerequisites
- ✅ Server running on port 8000
- ✅ Twilio account with WhatsApp sandbox
- ✅ ngrok installed (download from https://ngrok.com/)

### 2. Start the Server
```bash
cd "C:\Users\Keke\Documents\projects\FAST_API2"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Expose Server with ngrok
In a new terminal:
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 4. Configure Twilio WhatsApp Sandbox
1. Go to https://console.twilio.com/
2. Navigate to **Develop** → **Messaging** → **Try it out** → **Send a WhatsApp message**
3. In the sandbox settings:
   - **When a message comes in**: `https://your-ngrok-url.ngrok.io/webhook/whatsapp`
   - **Method**: POST
   - Click **Save**

### 5. Test the Complete Flow

#### A. Test Bot Responses
Send these messages to your Twilio sandbox number:

1. **Greeting**: "Olá" 
   - Expected: Welcome message with options

2. **Business Hours**: "qual o horário?"
   - Expected: Hours information

3. **Pricing**: "quanto custa?"
   - Expected: Pricing info with escalation offer

4. **Contact**: "telefone"
   - Expected: Contact information

#### B. Test Escalation to Agent
Send: "quero falar com atendente"
- Expected: Escalation message + conversation created in agent interface

#### C. Test Agent Interface
1. Open browser: `http://localhost:8000/index.html`
2. Login with: `admin@test.com` / `senha123`
3. You should see the escalated conversation
4. Reply to the customer - message should go to WhatsApp

#### D. Test Context Awareness
1. Send same question multiple times
2. Expected: Bot should escalate after repeated queries

### 6. Testing with User Numbers

For testing with your personal WhatsApp numbers:

#### Option A: Twilio Trial (Verified Numbers Only)
- Add your number to Twilio verified caller IDs
- Use your actual number instead of the sandbox number

#### Option B: Company Number Setup
- Get a Twilio phone number
- Set up WhatsApp business profile
- Use your company's WhatsApp Business API

### 7. Expected Flow

```
1. Customer → WhatsApp Message
2. Twilio → Your Server Webhook 
3. Server → Chatbot Processing
4. If Bot Can Handle → Send Response to Customer
5. If Escalation Needed → Create Conversation + Notify Agents
6. Agent → Responds via Interface
7. Server → Sends Agent Response to Customer via Twilio
```

### 8. Monitoring and Debugging

#### Server Logs to Watch For:
```
MESSAGE received from +5531999999999: Hello
BOT responding: Olá TestUser! Bem-vindo! Como posso ajudá-lo hoje?
WhatsApp message sent to +5531999999999: [message_id]
```

#### Agent Interface Logs:
- WebSocket connections
- New conversation notifications
- Message broadcasts

### 9. Troubleshooting

#### Common Issues:
1. **Webhook not receiving**: Check ngrok URL in Twilio settings
2. **No WhatsApp response**: Check Twilio credentials in `.env`
3. **Agent not notified**: Check WebSocket connection in browser console
4. **403 errors**: Check user permissions and conversation assignment

#### Debug Commands:
```bash
# Test webhook locally
python test_simple_webhook.py

# Check environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('TWILIO_ACCOUNT_SID:', bool(os.getenv('TWILIO_ACCOUNT_SID')))"
```

### 10. Production Deployment

For Railway deployment:
1. Set environment variables in Railway dashboard
2. Use Railway URL instead of ngrok for Twilio webhook
3. Configure production database (PostgreSQL)

## Success Criteria ✅

- [ ] Customer can start conversation via WhatsApp  
- [ ] Bot provides helpful responses to common questions
- [ ] Smart escalation when bot can't help or customer requests agent
- [ ] Agent receives real-time notifications of new conversations
- [ ] Agent can reply through web interface
- [ ] Customer receives agent responses via WhatsApp
- [ ] Conversation history maintained throughout handoff
- [ ] Context awareness for returning customers
- [ ] Proper conversation status management (active/closed)

## Quick Test Script

```python
# Save as quick_test.py
import requests

def test_webhook():
    response = requests.post("http://localhost:8000/webhook/whatsapp", data={
        "From": "whatsapp:+5531999999999", 
        "Body": "Hello test", 
        "ProfileName": "TestUser"
    })
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

test_webhook()
```

Happy testing! 🚀📱