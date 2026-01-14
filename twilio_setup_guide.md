# Twilio WhatsApp Setup Guide

## 🚀 Quick Setup Steps

### 1. Twilio Console Configuration

1. **Go to**: [console.twilio.com](https://console.twilio.com)

2. **Navigate to**: Develop > Messaging > Try it out > WhatsApp sandbox

3. **Configure Webhook**:
   ```
   When a message comes in: https://your-app.railway.app/webhook/whatsapp
   HTTP Method: POST
   ```

4. **For Local Testing** (temporarily):
   ```
   When a message comes in: http://localhost:8000/webhook/whatsapp
   HTTP Method: POST
   ```

### 2. Join WhatsApp Sandbox

1. **Send WhatsApp message to**: +1 415 523 8886
2. **Message content**: `join <your-sandbox-code>`
   - Example: `join coffee-brave` (your actual code will be different)

3. **You should receive**: "You are all set! You can now send messages to this WhatsApp number."

### 3. Test Your Chatbot

Send these test messages to your Twilio WhatsApp number:

#### ✅ **Bot Should Handle These:**
- "Ola" → Gets greeting response
- "Qual o horario?" → Gets business hours
- "Quanto custa?" → Gets pricing info

#### 🔄 **Should Escalate to Human:**
- "Preciso falar com atendente" → Routes to agent
- "Não entendi" → Escalates due to confusion
- "Problema urgente" → Escalates due to urgency

### 4. Monitor Results

Check your FastAPI server logs to see:
- 📱 Incoming messages
- 🤖 Bot responses  
- 👥 Escalations to human agents

### 5. Production Deployment

**Railway Webhook URL Format:**
```
https://fastapi2production-production.up.railway.app/webhook/whatsapp
```

**Replace** `fastapi2production-production` with your actual Railway app name.

## 🔍 Troubleshooting

### Common Issues:

1. **Webhook not receiving messages**
   - ❌ Check webhook URL is correct
   - ❌ Ensure Railway app is deployed and running
   - ❌ Verify HTTP method is POST

2. **Bot not responding**
   - ❌ Check server logs for errors
   - ❌ Verify Twilio credentials in .env
   - ❌ Test with simple messages first

3. **Messages not sending**
   - ❌ Check TWILIO_WHATSAPP_FROM is correct sandbox number
   - ❌ Verify phone number format includes country code

## 📊 Monitoring Your Chatbot

### API Endpoints for Monitoring:
- `GET /chatbot/status` - Check bot health
- `GET /chatbot/analytics` - View performance stats
- `POST /chatbot/clear-context/{phone}` - Reset conversation

### Log Messages to Look For:
```
📱 Mensagem recebida de +5511999999999: Ola
🤖 Bot respondendo: Olá! Como posso ajudá-lo?
👥 Escalando para agente humano. Motivo: user_requested
```

## 🎯 Expected Behavior

### Smart Routing Logic:
1. **Simple Questions** → Bot responds automatically
2. **Complex Issues** → Routes to human agent  
3. **User Frustration** → Escalates after 2-3 bot responses
4. **Direct Requests** → Immediate human transfer

### Context Memory:
- Bot remembers conversation history
- Tracks interaction count
- Maintains user preferences
- Auto-expires after 2 hours

## ✅ Success Indicators

Your integration is working when you see:
- ✓ Messages received in webhook
- ✓ Bot responses sent via WhatsApp
- ✓ Smart escalation decisions
- ✓ Context maintained across messages