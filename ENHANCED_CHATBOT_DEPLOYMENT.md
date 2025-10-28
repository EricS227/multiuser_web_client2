# Enhanced Claude Chatbot - Railway Deployment Guide

## 🚀 Overview

Your FastAPI WhatsApp application now features an enhanced multi-tier chatbot system with Claude AI integration, database-persistent context, and permanent fallback support.

## ✨ Features Implemented

### 🧠 **Multi-Tier Chatbot Architecture**
1. **Primary**: Claude API (Anthropic) - Best conversational AI
2. **Secondary**: Ollama (Local LLM) - Offline backup
3. **Tertiary**: Rasa (NLU) - Traditional chatbot
4. **Permanent**: Rule-based fallback - Always available

### 🗄️ **Database-Persistent Context**
- **BotContext** model for conversation memory
- Context survives server restarts and scaling
- Automatic expiration after 2 hours
- Context cleanup functionality

### 🎯 **Smart Escalation System**
- User-requested escalation ("falar com atendente")
- Complex intent detection (refunds, technical issues)
- Frustration detection
- Maximum bot response limits
- Business hours awareness

### 🎨 **Enhanced Frontend**
- Bot message indicators (🤖)
- Agent message styling (👤)
- Customer message styling (👨‍💼)
- Bot service indicators ([claude], [fallback], etc.)
- Real-time message type display

## 🛠️ Railway Deployment Steps

### 1. **Environment Variables**
Set these in Railway dashboard:

```env
# Required
SECRET_KEY=your-super-secret-key-here
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Primary Bot Service (Recommended)
ANTHROPIC_API_KEY=your-claude-api-key

# Database (Railway PostgreSQL automatically provided)
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional
ALLOWED_ORIGINS=https://yourdomain.railway.app,http://localhost:8000
```

### 2. **Deploy to Railway**
```bash
# Option 1: Deploy script (automatic)
chmod +x deploy.sh
./deploy.sh

# Option 2: Manual deployment
git add .
git commit -m "Enhanced Claude chatbot integration 🤖"
git push origin main
```

### 3. **Database Migration**
The enhanced models will be created automatically on first run:
- `BotContext` - Conversation context storage
- Enhanced `Message` model with `message_type` and `bot_service` fields
- `BotInteraction` - Analytics tracking

## 🧪 Testing Your Deployment

### **Automated Tests**
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set Claude API key (optional)
export ANTHROPIC_API_KEY=your-key

# Run comprehensive tests
python test_enhanced_chatbot.py
```

### **Manual Testing via WhatsApp**

1. **Bot Responses** - Send: "Olá"
   - Should get Claude/fallback response
   - Check admin panel for bot service used

2. **Escalation** - Send: "Preciso falar com atendente"
   - Should escalate to human agent
   - Conversation appears in agent dashboard

3. **Complex Queries** - Send: "Quero cancelar minha conta"
   - Should auto-escalate due to complex intent
   - Gets connected to agent immediately

4. **FAQ Questions** - Send: "Qual o horário de funcionamento?"
   - Bot should respond with business hours
   - No escalation needed

## 📊 Monitoring & Analytics

### **Admin Endpoints**
- `GET /chatbot/status` - Service health check
- `GET /chatbot/analytics` - Performance metrics
- `POST /chatbot/cleanup-contexts` - Maintenance
- `POST /chatbot/clear-context/{phone}` - Reset user context

### **Key Metrics to Monitor**
- **Escalation Rate**: % of conversations escalated
- **Bot Response Rate**: % handled by bot vs human
- **Service Distribution**: Which bot service is used most
- **Context Persistence**: Database context effectiveness

## 🔧 Configuration Options

### **Escalation Thresholds**
```python
# In enhanced_chatbot_service.py
MAX_BOT_RESPONSES = 4  # Escalate after 4 bot responses
CONTEXT_TIMEOUT = timedelta(hours=2)  # Context expiration
```

### **Bot Service Priority**
1. Claude API (if API key available)
2. Ollama (if localhost:11434 available)  
3. Rasa (if localhost:5005 available)
4. Rule-based fallback (always available)

### **Business Logic Customization**
```python
# Modify in enhanced_chatbot_service.py
ESCALATION_KEYWORDS = ['atendente', 'operador', ...]
COMPLEX_INTENTS = ['refund', 'reembolso', ...]
BUSINESS_HOURS = (8, 18)  # 8 AM to 6 PM
```

## 🚨 Troubleshooting

### **Common Issues**

1. **Claude API Not Working**
   - Check API key in Railway environment
   - Verify API key validity
   - System falls back to other services automatically

2. **Context Not Persisting**
   - Check database connection
   - Verify BotContext table exists
   - Check for database migration errors

3. **Messages Not Showing Types**
   - Clear browser cache
   - Check frontend JavaScript console
   - Verify WebSocket connection

4. **Bot Not Escalating**
   - Check escalation keywords
   - Verify conversation assignment logic
   - Check agent availability

### **Debug Commands**
```bash
# Check bot service status
curl https://your-app.railway.app/chatbot/status

# Clear specific user context  
curl -X POST https://your-app.railway.app/chatbot/clear-context/+5511999999999

# View analytics
curl https://your-app.railway.app/chatbot/analytics
```

## 📈 Performance Optimization

### **Claude API Usage**
- Uses claude-3-haiku (fast & cost-effective)
- 150-word response limit
- 3-second timeout for responsiveness

### **Database Optimization**
- Context cleanup scheduled automatically
- Indexes on phone_number and expires_at
- Optimized queries for conversation history

### **Fallback Performance**
- Rule-based fallback has zero latency
- No external dependencies
- Always available even during outages

## 🔐 Security Considerations

- **API Keys**: Stored securely in Railway environment
- **Context Data**: No sensitive information stored
- **Rate Limiting**: Natural through conversation flow
- **Input Validation**: Sanitized through Twilio

## 🚀 Production Ready Features

✅ **High Availability**: Multiple fallback layers  
✅ **Scalability**: Database-persistent context  
✅ **Monitoring**: Comprehensive analytics  
✅ **Maintenance**: Auto cleanup & admin tools  
✅ **User Experience**: Smart escalation logic  
✅ **Cost Effective**: Efficient Claude API usage  

## 🎯 Next Steps (Optional)

1. **Advanced Analytics**: Custom dashboards
2. **A/B Testing**: Different escalation strategies  
3. **Multi-language**: Portuguese/English support
4. **CRM Integration**: Customer data enrichment
5. **Voice Messages**: Audio response handling

## 📞 Support

Your enhanced chatbot system is now production-ready with:
- **Zero downtime fallbacks**
- **Intelligent conversation routing** 
- **Persistent conversation memory**
- **Beautiful UI indicators**
- **Comprehensive monitoring**

**Status**: ✅ **Production Ready**  
**Deployment**: ✅ **Railway Compatible**  
**Testing**: ✅ **Fully Tested**  
**Documentation**: ✅ **Complete**

---
*Enhanced with Claude AI for superior customer experience* 🤖✨