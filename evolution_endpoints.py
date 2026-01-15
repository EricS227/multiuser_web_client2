"""
Evolution API Endpoints for FastAPI
Add these endpoints to backend/main.py to manage Evolution API
"""

# ===== IMPORTS =====
# Add to top of backend/main.py:
# from backend.evolution_service import evolution_service

# ===== EVOLUTION API MANAGEMENT ENDPOINTS =====

@app.get("/api/evolution/status")
async def get_evolution_status(user: User = Depends(get_current_user)):
    """Check Evolution API instance status and connection"""
    if user.role not in ["admin", "agent"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        status = await evolution_service.get_instance_status()
        return {
            "enabled": evolution_service.enabled,
            "instance_name": evolution_service.instance_name,
            "base_url": evolution_service.base_url,
            "connection_status": status
        }
    except Exception as e:
        return {"error": str(e), "enabled": False}


@app.post("/api/evolution/create-instance")
async def create_evolution_instance(user: User = Depends(get_current_user)):
    """Create new WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.create_instance()
        if result:
            return {"status": "success", "data": result}
        else:
            return {"status": "error", "message": "Failed to create instance"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/evolution/qrcode")
async def get_evolution_qrcode(user: User = Depends(get_current_user)):
    """Get QR code for WhatsApp authentication"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        qr_data = await evolution_service.get_qrcode()
        if qr_data:
            return {
                "status": "success",
                "qrcode": qr_data,
                "instruction": "Scan this QR code with WhatsApp on your phone"
            }
        else:
            return {"status": "error", "message": "Failed to get QR code"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/evolution/configure-webhook")
async def configure_evolution_webhook(user: User = Depends(get_current_user)):
    """Configure Evolution API webhook for receiving messages"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        webhook_url = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/evolution")
        result = await evolution_service.set_webhook(webhook_url)

        if result:
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "data": result
            }
        else:
            return {"status": "error", "message": "Failed to configure webhook"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/evolution/logout")
async def evolution_logout(user: User = Depends(get_current_user)):
    """Logout from WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.logout()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/evolution/delete-instance")
async def delete_evolution_instance(user: User = Depends(get_current_user)):
    """Delete WhatsApp instance"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")

    try:
        result = await evolution_service.delete_instance()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== WEBHOOK ENDPOINT =====

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook to receive messages from Evolution API
    Evolution API will send messages to this endpoint
    """
    try:
        data = await request.json()

        print(f"📩 Evolution webhook received: {data.get('event', 'unknown')}")

        # Extract event type
        event = data.get("event")
        instance = data.get("instance")

        # Handle incoming messages
        if event == "messages.upsert":
            message_data = data.get("data", {})

            # Get message metadata
            key = message_data.get("key", {})
            message = message_data.get("message", {})
            pushName = message_data.get("pushName", "Cliente")

            # Ignore messages from us
            from_me = key.get("fromMe", False)
            if from_me:
                print("⏭️  Ignoring message from us")
                return {"status": "ignored", "reason": "message from us"}

            # Extract phone number
            remote_jid = key.get("remoteJid", "")
            phone_number = remote_jid.replace("@s.whatsapp.net", "")

            # Get message text
            conversation = message.get("conversation")
            extended_text = message.get("extendedTextMessage", {}).get("text")
            message_text = conversation or extended_text

            if not message_text:
                print("⏭️  Ignoring non-text message")
                return {"status": "ignored", "reason": "no text content"}

            print(f"💬 Message from {phone_number} ({pushName}): {message_text}")

            # Process through chatbot (reuse existing logic from Twilio webhook)
            with Session(engine) as session:
                chatbot_service = EnhancedClaudeChatbotService(session)

                # Process message through enhanced chatbot
                result = await chatbot_service.process_message(phone_number, message_text, pushName)

                should_escalate = result['should_escalate']
                bot_response = result.get('bot_response')
                bot_service = result.get('bot_service', 'unknown')
                escalation_reason = result.get('escalation_reason')

                # Save bot interaction for analytics
                if bot_response:
                    await _save_bot_interaction(
                        session, phone_number, message_text, bot_response,
                        pushName, bot_service, should_escalate, escalation_reason
                    )
                    print(f"🤖 BOT ({bot_service}) responding: {bot_response}")

            # Send response via Evolution API
            if bot_response:
                await evolution_service.send_text_message(phone_number, bot_response)

            # Handle escalation to human agent
            if should_escalate:
                print(f"🚨 ESCALATING conversation for {phone_number} to human agent")

                # Get escalation message
                with Session(engine) as session:
                    chatbot_service = EnhancedClaudeChatbotService(session)
                    escalation_message = chatbot_service.get_escalation_message(escalation_reason, pushName)

                    # Create or find existing conversation
                    existing_conversation = session.exec(
                        select(Conversation).where(
                            Conversation.customer_number == phone_number,
                            Conversation.status.in_(["pending", "active"])
                        )
                    ).first()

                    if existing_conversation:
                        conversation = existing_conversation
                        agent = get_least_busy_agent(session)
                        conversation.status = "active"
                        if agent and not conversation.assigned_to:
                            conversation.assigned_to = agent.id
                        session.add(conversation)
                        session.commit()
                    else:
                        # Create new conversation
                        agent = get_least_busy_agent(session)
                        system_user = session.exec(select(User).where(User.email == "system@internal")).first()

                        if not system_user:
                            system_user = User(
                                email="system@internal",
                                name="System Bot",
                                password_hash=hash_password("system_internal_password"),
                                role="system"
                            )
                            session.add(system_user)
                            session.commit()
                            session.refresh(system_user)

                        conversation = Conversation(
                            customer_number=phone_number,
                            name=pushName,
                            assigned_to=agent.id if agent else None,
                            created_by=agent.id if agent else system_user.id,
                            status="active"
                        )
                        session.add(conversation)
                        session.commit()
                        session.refresh(conversation)

                    # Save customer message
                    customer_msg = Message(
                        conversation_id=conversation.id,
                        sender="customer",
                        message_type="customer",
                        content=message_text
                    )
                    session.add(customer_msg)
                    session.commit()

                    # Save bot escalation message
                    if escalation_message:
                        bot_msg = Message(
                            conversation_id=conversation.id,
                            sender="bot",
                            message_type="bot",
                            content=escalation_message,
                            bot_service="evolution_escalation"
                        )
                        session.add(bot_msg)
                        session.commit()

                        # Broadcast to WebSocket clients
                        try:
                            asyncio.create_task(manager.broadcast({
                                "id": bot_msg.id,
                                "conversation_id": conversation.id,
                                "sender": "bot",
                                "message_type": "bot",
                                "message": escalation_message,
                                "timestamp": bot_msg.timestamp.isoformat()
                            }))
                        except Exception as e:
                            print(f"Error broadcasting: {e}")

                    # Notify agents via WebSocket
                    try:
                        escalation_data = {
                            "type": "new_escalation",
                            "source": "evolution_api",
                            "id": customer_msg.id,
                            "conversation_id": conversation.id,
                            "sender": "customer",
                            "message": message_text,
                            "customer_name": pushName,
                            "customer_number": phone_number,
                            "escalation_reason": escalation_reason,
                            "timestamp": customer_msg.timestamp.isoformat()
                        }
                        asyncio.create_task(manager.broadcast(escalation_data))
                    except Exception as e:
                        print(f"Error notifying agents: {e}")

                # Send escalation response
                if escalation_message:
                    await evolution_service.send_text_message(phone_number, escalation_message)

                return {
                    "status": "escalated_to_agent",
                    "response": escalation_message,
                    "reason": escalation_reason
                }
            else:
                return {
                    "status": "bot_response",
                    "response": bot_response,
                    "bot_service": bot_service
                }

        # Handle connection updates
        elif event == "connection.update":
            connection_data = data.get("data", {})
            state = connection_data.get("state", "unknown")
            print(f"🔌 Connection update: {state}")
            return {"status": "ok", "event": event}

        # Handle QR code updates
        elif event == "qrcode.updated":
            qr_data = data.get("data", {})
            print(f"📱 QR Code updated")
            return {"status": "ok", "event": event}

        return {"status": "ok", "event": event}

    except Exception as e:
        print(f"❌ Evolution webhook error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ===== UPDATE SEND MESSAGE FUNCTION =====
# Replace the existing send_whatsapp_message function with this:

async def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message using available services
    Priority: Evolution API -> Twilio
    """

    # Try Evolution API first (FREE)
    if evolution_service.enabled:
        result = await evolution_service.send_text_message(to_number, message)
        if result:
            print(f"✅ Evolution API: Message sent to {to_number}")
            return result

    # Fallback to Twilio if Evolution fails or is disabled
    if twilio_client and TWILIO_WHATSAPP_FROM:
        try:
            msg = twilio_client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_FROM,
                to=f"whatsapp:{to_number}"
            )
            print(f"✅ Twilio: Message sent to {to_number}: {msg.sid}")
            return msg.sid
        except Exception as e:
            print(f"❌ Twilio error: {e}")
            return None

    print("⚠️  No WhatsApp service available")
    return None
