# n8n WhatsApp Integration Guide

## Overview

Your FastAPI application now supports **n8n integration** alongside the existing Twilio WhatsApp functionality. This allows you to use n8n's powerful workflow automation to enhance your WhatsApp bot with advanced routing, multi-channel support, and complex automation logic.

## Architecture

```
WhatsApp → n8n Workflow → Your Railway FastAPI → n8n Response → WhatsApp
                    ↓
               (Parallel processing)
                    ↓  
WhatsApp → Twilio → Your Railway FastAPI → Twilio → WhatsApp
```

## n8n Webhook Endpoint

**URL**: `https://your-railway-app.railway.app/webhook/n8n`

### Request Format

```json
{
    "from": "whatsapp:+554196950370",
    "message": "Customer message text",
    "profile_name": "Customer Name",
    "workflow_id": "n8n_workflow_id",
    "execution_id": "n8n_execution_id"
}
```

### Response Format

**Bot Response:**
```json
{
    "status": "bot_response",
    "response": "Bot reply message",
    "bot_service": "claude_n8n",
    "conversation_id": 123,
    "n8n_format": true,
    "actions": {
        "send_whatsapp": {
            "to": "+554196950370",
            "message": "Bot reply message"
        },
        "save_conversation": true,
        "continue_chat": true
    },
    "metadata": {
        "workflow_id": "n8n_workflow_id",
        "execution_id": "n8n_execution_id",
        "profile_name": "Customer Name"
    }
}
```

**Escalation Response:**
```json
{
    "status": "escalated_to_agent",
    "response": "Connecting you to an agent...",
    "escalation_reason": "user_requested",
    "conversation_id": 123,
    "assigned_agent_id": 5,
    "message_history_count": 3,
    "n8n_format": true,
    "actions": {
        "send_whatsapp": {
            "to": "+554196950370",
            "message": "Connecting you to an agent..."
        },
        "notify_agents": true,
        "create_conversation": true
    }
}
```

## Environment Configuration

Add these variables to your Railway environment:

```env
# n8n Integration Settings
N8N_API_KEY=your_secure_api_key_here
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook
N8N_ENABLED=true
```

## Setting Up n8n Workflow

### 1. Basic WhatsApp Bot Workflow

```
Webhook Trigger → Function (Process Message) → HTTP Request (to FastAPI) → Function (Handle Response) → WhatsApp Send
```

#### Webhook Trigger Node
- **Method**: POST
- **Path**: `/webhook-whatsapp`
- **Response Mode**: Respond when workflow finishes

#### Function Node 1: Process Message
```javascript
// Extract WhatsApp data
const from = $json.From?.replace('whatsapp:', '') || $json.from;
const message = $json.Body || $json.message;
const profileName = $json.ProfileName || $json.profile_name || 'Customer';

return {
  from: from,
  message: message,
  profile_name: profileName,
  workflow_id: $workflow.id,
  execution_id: $execution.id
};
```

#### HTTP Request Node: Send to FastAPI
- **Method**: POST
- **URL**: `https://your-railway-app.railway.app/webhook/n8n`
- **Headers**: 
  - `Content-Type: application/json`
  - `x-n8n-api-key: your_api_key` (if configured)
- **Body**: `{{ $json }}`

#### Function Node 2: Handle Response
```javascript
const response = $json;

// Log the response
console.log('FastAPI Response:', response);

// Prepare WhatsApp response
return {
  to: `whatsapp:${response.actions?.send_whatsapp?.to}`,
  body: response.actions?.send_whatsapp?.message || response.response,
  conversation_id: response.conversation_id,
  escalated: response.status === 'escalated_to_agent'
};
```

#### WhatsApp Send Node (if using WhatsApp Business API)
- **To**: `{{ $json.to }}`
- **Message**: `{{ $json.body }}`

### 2. Advanced Workflow Features

#### Smart Routing Based on Keywords
```javascript
const message = $json.message.toLowerCase();

// Route based on intent
if (message.includes('urgent') || message.includes('emergency')) {
    return [{ route: 'urgent', priority: 'high' }];
} else if (message.includes('sales') || message.includes('buy')) {
    return [{ route: 'sales', department: 'sales' }];
} else if (message.includes('support') || message.includes('help')) {
    return [{ route: 'support', department: 'technical' }];
} else {
    return [{ route: 'general', department: 'general' }];
}
```

#### Business Hours Check
```javascript
const now = new Date();
const hour = now.getHours();
const day = now.getDay(); // 0 = Sunday

const businessHours = {
    start: 9,  // 9 AM
    end: 18,   // 6 PM
    weekends: false
};

const isBusinessHours = (
    hour >= businessHours.start && 
    hour < businessHours.end && 
    (businessHours.weekends || (day >= 1 && day <= 5))
);

return {
    is_business_hours: isBusinessHours,
    current_hour: hour,
    current_day: day,
    auto_response: !isBusinessHours ? "Thanks for your message! We'll respond during business hours (9 AM - 6 PM, Mon-Fri)." : null
};
```

## API Endpoints

### Status Endpoint
```bash
GET /n8n/status
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
    "n8n_integration": {
        "enabled": true,
        "webhook_url": "https://your-n8n-instance.com/webhook",
        "api_key_configured": true,
        "connectivity": "online",
        "webhook_endpoint": "/webhook/n8n"
    },
    "features": {
        "enhanced_routing": true,
        "workflow_automation": true,
        "parallel_processing": true,
        "fallback_to_twilio": true
    }
}
```

### Test Endpoint
```bash
POST /test-n8n
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "from": "+554196950370",
    "message": "test message",
    "profile_name": "Test User"
}
```

## Benefits of n8n Integration

### 1. **Enhanced Automation**
- Visual workflow builder
- Complex routing logic
- Conditional responses
- Multi-step processes

### 2. **Multi-Channel Support**
- WhatsApp (via your existing setup)
- Telegram integration
- Discord integration  
- Email automation
- SMS via multiple providers

### 3. **Advanced Features**
- Sentiment analysis
- Language detection
- CRM integration
- Database connections
- External API calls

### 4. **Business Logic**
- Business hours handling
- Department routing
- Priority escalation
- Customer segmentation

## Security Considerations

1. **API Key Authentication**: Always use API keys in production
2. **HTTPS Only**: Ensure all webhook URLs use HTTPS
3. **Input Validation**: n8n should validate all incoming data
4. **Rate Limiting**: Configure rate limits on your n8n webhooks

## Testing

### 1. Test n8n Integration
```bash
curl -X POST https://your-railway-app.railway.app/test-n8n \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"message": "test n8n integration"}'
```

### 2. Test Webhook Directly
```bash
curl -X POST https://your-railway-app.railway.app/webhook/n8n \
  -H "Content-Type: application/json" \
  -H "x-n8n-api-key: your_api_key" \
  -d '{
    "from": "+554196950370",
    "message": "Hello from n8n",
    "profile_name": "Test User",
    "workflow_id": "test_workflow",
    "execution_id": "test_123"
  }'
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check N8N_API_KEY configuration
2. **Connection Timeout**: Verify N8N_WEBHOOK_URL is accessible
3. **Missing Messages**: Check n8n workflow execution logs
4. **Duplicate Messages**: Ensure either Twilio OR n8n is handling the same WhatsApp number

### Debug Logs
Monitor Railway logs for:
- `N8N WEBHOOK DEBUG` - Message reception
- `N8N: Created conversation` - Conversation creation  
- `N8N: Error` - Error conditions

## Migration Strategy

### Phase 1: Parallel Operation (Recommended)
- Keep Twilio webhook active
- Add n8n webhook for enhanced features
- Route specific customers/keywords through n8n
- Gradual testing and optimization

### Phase 2: Full Migration (Future)
- Disable Twilio webhook
- Route all WhatsApp through n8n
- Remove Twilio dependencies

This allows you to test n8n integration without affecting your existing working system!