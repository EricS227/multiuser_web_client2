# 🤖 Twilio WhatsApp Chatbot Testing Guide

This guide will help you test your chatbot with Twilio WhatsApp integration on Railway.

## 🔧 Step 1: Configure Railway Environment Variables

In your Railway dashboard, add these Twilio environment variables:

```
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token  
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

**Where to find these values:**
1. Login to [Twilio Console](https://console.twilio.com/)
2. Copy Account SID and Auth Token from dashboard
3. Go to WhatsApp Sandbox settings for the phone number

## 📡 Step 2: Configure Twilio Webhook

1. **Get your Railway app URL:**
   ```
   https://your-app-name.railway.app
   ```

2. **Set webhook URL in Twilio Console:**
   - Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
   - In Sandbox settings, set webhook URL to:
   ```
   https://your-app-name.railway.app/webhook/whatsapp
   ```

3. **Set HTTP method to POST**

## 🧪 Step 3: Test Webhook Accessibility

Test if your webhook endpoint is accessible:

```bash
curl -X POST https://your-app-name.railway.app/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp%2B5511999999999&Body=test&ProfileName=TestUser"
```

**Expected response:** JSON with status and response message

## 📱 Step 4: Test WhatsApp Bot Responses

### Join Twilio WhatsApp Sandbox
1. From WhatsApp, send the join code to +1 415 523 8886
2. Example: Send "join your-sandbox-code" 

### Test Bot Conversations

**Test 1: Greeting**
Send: `Olá`
Expected: Welcome message with options

**Test 2: Business Hours** 
Send: `Qual o horário de funcionamento?`
Expected: Business hours information

**Test 3: Pricing**
Send: `Quanto custa?`
Expected: Pricing information with option to talk to consultant

**Test 4: Escalation Trigger**
Send: `Quero falar com atendente`
Expected: Bot escalates to human agent

### Bot Response Examples

The chatbot handles these conversation types:

```
Greetings: "oi", "olá", "hello", "bom dia"
→ Welcome message with menu options

Business Hours: "horário", "funciona", "aberto"  
→ Operating hours information

Pricing: "preço", "valor", "quanto custa"
→ Pricing info + escalation offer

Contact: "contato", "telefone", "email"
→ Contact information

Problems: "problema", "erro", "não funciona"
→ Auto-escalation to support

Escalation: "atendente", "operador", "humano"
→ Connect to human agent
```

## 👥 Step 5: Test Human Agent Escalation

### Trigger Escalation:
1. Send escalation keyword: `atendente`
2. Bot should respond with escalation message
3. Conversation appears in Railway app dashboard

### Verify Escalation:
1. Login to your Railway app: `https://your-app-name.railway.app`
2. Check conversations list for new entry
3. Verify WebSocket real-time updates

## 🔍 Step 6: Debug Issues

### Check Railway Logs:
```bash
railway logs
```

### Common Issues:

**1. Webhook not receiving messages:**
- Verify webhook URL in Twilio console
- Check Railway app is deployed and accessible
- Ensure URL ends with `/webhook/whatsapp`

**2. Bot not responding:**
- Check Twilio environment variables in Railway
- Verify Twilio credentials are correct
- Check Railway logs for errors

**3. Messages not appearing in dashboard:**
- Verify database is connected
- Check WebSocket connection
- Login to app and check conversations

### Debug Webhook Manually:

```bash
# Test webhook with curl
curl -X POST https://your-app-name.railway.app/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp%2B5511999999999&Body=Hello&ProfileName=TestUser"
```

## 📊 Step 7: Monitor Bot Performance

### Check Bot Analytics:
- Login to your app
- Go to `/chatbot/analytics` (admin only)
- View interaction statistics and escalation rates

### Bot Interaction Logs:
All bot conversations are saved in `BotInteraction` table for analysis.

## 🎯 Testing Checklist

- [ ] Railway environment variables configured
- [ ] Twilio webhook URL set correctly  
- [ ] Webhook endpoint accessible via curl
- [ ] WhatsApp sandbox joined successfully
- [ ] Bot responds to greetings
- [ ] Bot provides business information
- [ ] Escalation to human agents works
- [ ] Conversations appear in dashboard
- [ ] WebSocket real-time updates working
- [ ] Railway logs show no errors

## 🚨 Troubleshooting

**Bot gives generic responses only:**
- Bot logic is rule-based, not AI-powered
- Responses are predefined based on keywords
- For AI responses, integrate with OpenAI or similar service

**Escalation not working:**
- Check database connection
- Verify user roles in database
- Ensure WebSocket connections are active

**Messages not sending from app:**
- Verify Twilio credentials
- Check `send_whatsapp_message` function logs
- Ensure proper phone number formatting

## 📞 Support

For issues:
1. Check Railway deployment logs
2. Verify Twilio console webhook logs  
3. Test webhook endpoint manually
4. Check database for conversation records

Happy testing! 🚀

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Set up Twilio environment variables in Railway", "status": "in_progress"}, {"id": "2", "content": "Configure Twilio webhook URL to point to Railway app", "status": "pending"}, {"id": "3", "content": "Test webhook endpoint accessibility", "status": "pending"}, {"id": "4", "content": "Send test WhatsApp message to verify bot responses", "status": "pending"}, {"id": "5", "content": "Test escalation to human agent workflow", "status": "pending"}]