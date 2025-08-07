#!/usr/bin/env python3
"""
Test script for the Enhanced Chatbot Integration
"""

import asyncio
import json
from backend.chatbot_service import EnhancedChatbotService, ConversationContext, ChatbotRouter
from backend.models import *
from sqlmodel import Session, create_engine

# Create a test database
engine = create_engine("sqlite:///./test_chatbot.db", echo=False)
SQLModel.metadata.create_all(engine)

async def test_chatbot_service():
    """Test the enhanced chatbot service functionality"""
    
    print("Testing Enhanced Chatbot Service")
    print("="*50)
    
    with Session(engine) as session:
        chatbot_service = EnhancedChatbotService(session)
        
        # Test phone number
        test_phone = "+5511999999999"
        test_name = "Test User"
        
        # Test cases
        test_messages = [
            "Olá, boa tarde!",
            "Qual o horário de funcionamento?", 
            "Quanto custa o serviço?",
            "Preciso falar com um atendente",
            "Não entendi a resposta anterior",
            "Tenho um problema urgente"
        ]
        
        print(f"\nTesting conversation with {test_phone} ({test_name})")
        print("-" * 40)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Customer: {message}")
            
            # Process message
            result = await chatbot_service.process_message(test_phone, message, test_name)
            
            if result['should_escalate']:
                print(f"   -> Escalated to human: {result['escalation_reason']}")
                escalation_msg = chatbot_service.get_escalation_message(result['escalation_reason'], test_name)
                print(f"   -> Escalation message: {escalation_msg}")
            else:
                print(f"   -> Bot response: {result['bot_response']}")
            
            # Small delay between messages
            await asyncio.sleep(0.5)

def test_conversation_context():
    """Test conversation context management"""
    
    print("\nTesting Conversation Context")
    print("="*50)
    
    context_manager = ConversationContext()
    test_phone = "+5511888888888"
    
    # Get initial context
    context = context_manager.get_context(test_phone)
    print(f"Initial context: {json.dumps(context, indent=2, default=str)}")
    
    # Update context
    context_manager.update_context(test_phone, {
        'conversation_stage': 'information_gathering',
        'user_intent': 'pricing_inquiry',
        'bot_responses_count': 2
    })
    
    updated_context = context_manager.get_context(test_phone)
    print(f"Updated context: {json.dumps(updated_context, indent=2, default=str)}")
    
    # Clear context
    context_manager.clear_context(test_phone)
    cleared_context = context_manager.get_context(test_phone)
    print(f"Cleared context: {json.dumps(cleared_context, indent=2, default=str)}")

def test_chatbot_router():
    """Test smart escalation routing logic"""
    
    print("\nTesting Smart Routing Logic")
    print("="*50)
    
    router = ChatbotRouter()
    
    test_cases = [
        ("Oi, como você está?", {"bot_responses_count": 0}),
        ("Preciso falar com um atendente", {"bot_responses_count": 1}),
        ("Não entendi sua resposta", {"bot_responses_count": 2}),
        ("Qual o horário de funcionamento?", {"bot_responses_count": 0}),
        ("Tenho um problema técnico grave", {"bot_responses_count": 1}),
        ("Quero um reembolso", {"bot_responses_count": 0}),
        ("Isso é urgente!", {"bot_responses_count": 3})
    ]
    
    for message, context in test_cases:
        should_escalate, reason = router.should_escalate_to_human(message, context)
        can_handle = router.can_bot_handle(message)
        
        print(f"\nMessage: '{message}'")
        print(f"Context: bot_responses={context.get('bot_responses_count', 0)}")
        print(f"Should escalate: {should_escalate} ({'YES' if should_escalate else 'NO'})")
        if should_escalate:
            print(f"Reason: {reason}")
        print(f"Bot can handle: {can_handle} ({'YES' if can_handle else 'NO'})")

async def main():
    """Run all tests"""
    
    print("Starting Enhanced Chatbot Tests")
    print("="*60)
    
    # Test 1: Conversation Context
    test_conversation_context()
    
    # Test 2: Smart Routing Logic  
    test_chatbot_router()
    
    # Test 3: Full Chatbot Service (requires running servers)
    try:
        await test_chatbot_service()
    except Exception as e:
        print(f"\nWARNING: Chatbot service test failed (servers may be offline): {e}")
        print("   This is normal if Rasa/Ollama servers are not running")
    
    print("\nAll tests completed!")
    print("\nTo fully test the chatbot integration:")
    print("1. Start your FastAPI server: uvicorn backend.main:app --reload")
    print("2. (Optional) Start Rasa server on localhost:5005")
    print("3. (Optional) Start Ollama server on localhost:11434") 
    print("4. Send test messages to your Twilio WhatsApp webhook")

if __name__ == "__main__":
    asyncio.run(main())