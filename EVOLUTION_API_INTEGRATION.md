# Guia de Integração - Evolution API

## O que é Evolution API?

Evolution API é uma API REST moderna e completa para WhatsApp, totalmente **GRATUITA** e open-source. É a solução recomendada para substituir o Twilio.

### Vantagens sobre Twilio
- ✅ **100% Gratuita** - sem custos mensais ou por mensagem
- ✅ **Multi-instâncias** - gerencie múltiplos números WhatsApp
- ✅ **Webhooks nativos** - receba mensagens em tempo real
- ✅ **QR Code simples** - autenticação fácil via WhatsApp Web
- ✅ **API REST completa** - envie textos, mídias, áudio, documentos
- ✅ **Auto-hospedada** - controle total dos seus dados
- ✅ **Ativa e mantida** - comunidade grande e ativa

### Comparação

| Recurso | Twilio | Evolution API | WPPConnect |
|---------|--------|---------------|------------|
| Custo | Pago | Grátis | Grátis |
| Multi-instâncias | ❌ | ✅ | ✅ |
| Auto-hospedagem | ❌ | ✅ | ✅ |
| Banco de dados | ❌ | ✅ | ⚠️ |
| Documentação | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Manutenção | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## Passo 1: Instalar Evolution API via Docker

### Método Rápido (Recomendado)

```bash
# Subir Evolution API com PostgreSQL e Redis
docker-compose -f docker-compose-evolution.yml up -d

# Verificar se está rodando
docker ps | grep evolution

# Ver logs
docker logs evolution-api -f
```

A Evolution API estará disponível em: `http://localhost:8080`

### Verificar Health

```bash
curl http://localhost:8080
```

Resposta esperada:
```json
{
  "status": "ok",
  "version": "2.x.x"
}
```

## Passo 2: Configurar Variáveis de Ambiente

Edite seu arquivo `.env`:

```env
# Evolution API Configuration
EVOLUTION_ENABLED=true
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=B6D711FCDE4D4FD5936544120E713976
EVOLUTION_INSTANCE_NAME=chatapp
EVOLUTION_WEBHOOK_URL=http://localhost:8000/webhook/evolution
```

**IMPORTANTE**: Para produção, mude o `EVOLUTION_API_KEY` para uma chave segura.

## Passo 3: Integrar no Backend FastAPI

### 3.1 Importar o Serviço

Adicione ao `backend/main.py`:

```python
from backend.evolution_service import evolution_service
```

### 3.2 Adicionar Endpoints de Gerenciamento

```python
@app.get("/evolution/status")
async def get_evolution_status(user: User = Depends(get_current_user)):
    """Check Evolution API instance status"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    status = await evolution_service.get_instance_status()
    return {"evolution_api": status, "enabled": evolution_service.enabled}

@app.post("/evolution/create-instance")
async def create_evolution_instance(user: User = Depends(get_current_user)):
    """Create new WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await evolution_service.create_instance()
    return result

@app.get("/evolution/qrcode")
async def get_evolution_qrcode(user: User = Depends(get_current_user)):
    """Get QR code for WhatsApp authentication"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    qr_data = await evolution_service.get_qrcode()
    return qr_data

@app.post("/evolution/webhook/configure")
async def configure_evolution_webhook(user: User = Depends(get_current_user)):
    """Configure Evolution API webhook"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    webhook_url = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/evolution")
    result = await evolution_service.set_webhook(webhook_url)
    return result
```

### 3.3 Modificar Função de Envio de Mensagens

Atualize a função `send_whatsapp_message` em `backend/main.py`:

```python
async def send_whatsapp_message(to_number: str, message: str):
    """Send WhatsApp message using Evolution API or Twilio (fallback)"""

    # Try Evolution API first (FREE)
    if evolution_service.enabled:
        result = await evolution_service.send_text_message(to_number, message)
        if result:
            print(f"Evolution API: Message sent to {to_number}")
            return result

    # Fallback to Twilio if Evolution fails
    if twilio_client and TWILIO_WHATSAPP_FROM:
        try:
            msg = twilio_client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_FROM,
                to=f"whatsapp:{to_number}"
            )
            print(f"Twilio: Message sent to {to_number}: {msg.sid}")
            return msg.sid
        except Exception as e:
            print(f"Twilio error: {e}")
            return None

    print("No WhatsApp service available")
    return None
```

### 3.4 Criar Webhook para Receber Mensagens

```python
@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook to receive messages from Evolution API
    """
    try:
        data = await request.json()

        print(f"Evolution webhook received: {data}")

        # Extract message data
        event = data.get("event")
        instance = data.get("instance")

        if event == "messages.upsert":
            message_data = data.get("data", {})

            # Get message info
            key = message_data.get("key", {})
            message = message_data.get("message", {})
            pushName = message_data.get("pushName", "Unknown")

            # Check if message is from customer (not from us)
            from_me = key.get("fromMe", False)
            if from_me:
                return {"status": "ignored", "reason": "message from us"}

            # Extract phone number and message text
            remote_jid = key.get("remoteJid", "")
            phone_number = remote_jid.replace("@s.whatsapp.net", "")

            # Get message text
            conversation = message.get("conversation")
            extended_text = message.get("extendedTextMessage", {}).get("text")
            message_text = conversation or extended_text

            if not message_text:
                return {"status": "ignored", "reason": "no text content"}

            print(f"Evolution: Message from {phone_number} ({pushName}): {message_text}")

            # Process through existing chatbot logic (same as Twilio webhook)
            with Session(engine) as session:
                chatbot_service = EnhancedClaudeChatbotService(session)
                result = await chatbot_service.process_message(phone_number, message_text, pushName)

                should_escalate = result['should_escalate']
                bot_response = result.get('bot_response')
                bot_service = result.get('bot_service', 'unknown')

                # Send response via Evolution API
                if bot_response:
                    await evolution_service.send_text_message(phone_number, bot_response)

                # Handle escalation (reuse existing logic)
                if should_escalate:
                    # Create conversation and assign to agent
                    # (same logic as Twilio webhook)
                    pass

            return {"status": "processed", "bot_response": bot_response}

        return {"status": "ok"}

    except Exception as e:
        print(f"Evolution webhook error: {e}")
        return {"status": "error", "message": str(e)}
```

## Passo 4: Configurar WhatsApp

### 4.1 Criar Instância

```bash
curl -X POST http://localhost:8000/evolution/create-instance \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4.2 Obter QR Code

```bash
curl http://localhost:8000/evolution/qrcode \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Retorno:
```json
{
  "code": "2@XXXXX...",  // QR code string
  "base64": "data:image/png;base64,iVBOR..."  // QR code image
}
```

### 4.3 Escanear QR Code

1. Acesse a URL retornada no navegador ou exiba o QR code base64
2. Abra WhatsApp no celular
3. Vá em **Configurações > Aparelhos conectados > Conectar um aparelho**
4. Escaneie o QR code

### 4.4 Verificar Conexão

```bash
curl http://localhost:8000/evolution/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Resposta esperada:
```json
{
  "state": "open",
  "statusReason": "connected"
}
```

## Passo 5: Testar Envio de Mensagem

### Via API

```bash
curl -X POST http://localhost:8000/test-bot \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "5541999999999",
    "message": "Olá, preciso de ajuda",
    "profile_name": "Teste"
  }'
```

### Enviar de Outro WhatsApp

Basta enviar uma mensagem para o número conectado. O sistema irá:
1. Receber via webhook Evolution
2. Processar com o chatbot
3. Responder automaticamente
4. Escalar para humano se necessário

## Passo 6: Deploy em Produção

### 6.1 Expor Webhook Publicamente

Use ngrok para teste ou configure domínio próprio:

```bash
# Com ngrok
ngrok http 8000

# Atualizar webhook
curl -X POST http://localhost:8000/evolution/webhook/configure \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"webhook_url": "https://your-domain.com/webhook/evolution"}'
```

### 6.2 Docker Compose Produção

```yaml
version: '3.8'
services:
  evolution-api:
    image: atendai/evolution-api:latest
    environment:
      - SERVER_URL=https://your-domain.com
      - AUTHENTICATION_API_KEY=your-secure-key-here
      # ... outras configs
```

### 6.3 Variáveis de Ambiente Produção

```env
EVOLUTION_ENABLED=true
EVOLUTION_API_URL=https://your-evolution-api-domain.com
EVOLUTION_API_KEY=your-secure-api-key
EVOLUTION_WEBHOOK_URL=https://your-fastapi-domain.com/webhook/evolution
```

## Recursos Adicionais

### Enviar Mídia

```python
# Enviar imagem
await evolution_service.send_media(
    to_number="+5541999999999",
    media_url="https://example.com/image.jpg",
    caption="Olha essa imagem!"
)
```

### Múltiplas Instâncias

Você pode ter múltiplas instâncias (múltiplos números WhatsApp):

```env
# Instância 1
EVOLUTION_INSTANCE_NAME=vendas

# Instância 2 (adicione outro serviço)
EVOLUTION_INSTANCE_NAME_2=suporte
```

### Monitoramento

```bash
# Ver logs Evolution API
docker logs evolution-api -f --tail 100

# Ver logs PostgreSQL
docker logs postgres-evolution -f

# Ver logs Redis
docker logs redis-evolution -f
```

## Troubleshooting

### QR Code não aparece
- Verifique se Evolution API está rodando: `docker ps`
- Verifique logs: `docker logs evolution-api`
- Tente recriar instância: `curl -X POST http://localhost:8000/evolution/create-instance`

### Webhook não recebe mensagens
- Verifique se webhook está configurado corretamente
- Use ngrok para expor localhost publicamente
- Verifique logs do FastAPI para erros

### Conexão cai
- Evolution API reconecta automaticamente
- Se persistir, faça logout e reconecte:
```bash
curl -X DELETE http://localhost:8000/evolution/logout
curl -X GET http://localhost:8000/evolution/qrcode  # Novo QR code
```

## Links Úteis

- [Evolution API GitHub](https://github.com/EvolutionAPI/evolution-api)
- [Documentação Oficial](https://doc.evolution-api.com/)
- [Postman Collection](https://doc.evolution-api.com/postman)

## Suporte

Em caso de problemas:
1. Verifique os logs: `docker logs evolution-api -f`
2. Consulte a documentação oficial
3. GitHub Issues: https://github.com/EvolutionAPI/evolution-api/issues
