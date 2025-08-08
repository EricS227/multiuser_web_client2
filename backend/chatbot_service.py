import httpx
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select
from backend.models import Message, Conversation, brazilian_now

class ConversationContext:
    """Manages conversation context and memory for chatbot interactions"""
    
    def __init__(self):
        self.contexts: Dict[str, Dict] = {}
        self.context_timeout = timedelta(hours=2)  # Context expires after 2 hours
    
    def get_context(self, phone_number: str) -> Dict:
        """Get conversation context for a phone number"""
        if phone_number in self.contexts:
            context = self.contexts[phone_number]
            # Check if context is still valid
            if brazilian_now() - context.get('last_updated', datetime.min) < self.context_timeout:
                return context
            else:
                # Context expired, clean it up
                del self.contexts[phone_number]
        
        return {
            'phone_number': phone_number,
            'conversation_stage': 'greeting',
            'user_intent': None,
            'collected_info': {},
            'bot_responses_count': 0,
            'escalation_requested': False,
            'last_updated': brazilian_now()
        }
    
    def update_context(self, phone_number: str, updates: Dict):
        """Update conversation context"""
        context = self.get_context(phone_number)
        context.update(updates)
        context['last_updated'] = brazilian_now()
        self.contexts[phone_number] = context
    
    def clear_context(self, phone_number: str):
        """Clear conversation context"""
        if phone_number in self.contexts:
            del self.contexts[phone_number]
    
    def cleanup_expired_contexts(self):
        """Clean up expired conversation contexts"""
        current_time = brazilian_now()
        expired_keys = []
        
        for phone_number, context in self.contexts.items():
            if current_time - context.get('last_updated', datetime.min) > self.context_timeout:
                expired_keys.append(phone_number)
        
        for key in expired_keys:
            del self.contexts[key]
        
        return len(expired_keys)

class ChatbotRouter:
    """Smart routing logic to determine when to escalate to human agents"""
    
    # Keywords that indicate user wants human help
    ESCALATION_KEYWORDS = [
        'falar com atendente', 'atendente', 'operador', 'humano', 'pessoa',
        'talk to agent', 'agent', 'human', 'operator', 'representative',
        'urgente', 'urgent', 'problema grave', 'serious problem',
        'reclamação', 'complaint', 'insatisfeito', 'dissatisfied'
    ]
    
    # Intent patterns that should go directly to human
    COMPLEX_INTENTS = [
        'refund', 'reembolso', 'cancelamento', 'cancel',
        'problema técnico', 'technical issue', 'bug',
        'conta bloqueada', 'account blocked', 'login problem'
    ]
    
    # Questions the bot can handle
    BOT_CAPABLE_INTENTS = [
        'horario', 'hours', 'funcionamento', 'operating',
        'preço', 'price', 'valor', 'cost', 'quanto custa',
        'informação', 'information', 'sobre', 'about',
        'contato', 'contact', 'telefone', 'email',
        'localização', 'location', 'endereço', 'address'
    ]

    def should_escalate_to_human(self, message: str, context: Dict) -> Tuple[bool, str]:
        """
        Determine if message should be escalated to human agent
        Returns (should_escalate, reason)
        """
        message_lower = message.lower()
        
        # Direct escalation request
        if any(keyword in message_lower for keyword in self.ESCALATION_KEYWORDS):
            return True, "user_requested"
        
        # Too many bot responses without resolution
        if context.get('bot_responses_count', 0) >= 3:
            return True, "max_bot_responses"
        
        # Complex intents that need human help
        if any(intent in message_lower for intent in self.COMPLEX_INTENTS):
            return True, "complex_intent"
        
        # User expressed frustration
        frustration_words = ['não entendi', 'não funciona', 'frustrado', 'irritado', 'confused', 'frustrated']
        if any(word in message_lower for word in frustration_words):
            return True, "user_frustration"
        
        # Previous escalation was requested
        if context.get('escalation_requested'):
            return True, "previous_escalation"
        
        return False, "bot_can_handle"

    def can_bot_handle(self, message: str) -> bool:
        """Check if bot can potentially handle this message"""
        message_lower = message.lower()
        return any(intent in message_lower for intent in self.BOT_CAPABLE_INTENTS)

class EnhancedChatbotService:
    """Enhanced chatbot service with context awareness and smart routing"""
    
    def __init__(self, session: Session):
        self.session = session
        self.context_manager = ConversationContext()
        self.router = ChatbotRouter()
        
    async def process_message(self, phone_number: str, message: str, profile_name: str = "Cliente") -> Dict:
        """
        Process incoming message and determine appropriate response
        Returns: {
            'should_escalate': bool,
            'escalation_reason': str,
            'bot_response': str or None,
            'context_updated': bool
        }
        """
        # Get conversation context
        context = self.context_manager.get_context(phone_number)
        
        # Check if should escalate to human
        should_escalate, escalation_reason = self.router.should_escalate_to_human(message, context)
        
        if should_escalate:
            self.context_manager.update_context(phone_number, {
                'escalation_requested': True,
                'escalation_reason': escalation_reason
            })
            
            return {
                'should_escalate': True,
                'escalation_reason': escalation_reason,
                'bot_response': None,
                'context_updated': True
            }
        
        # Try to get bot response
        bot_response = await self._get_enhanced_bot_response(message, context, profile_name)
        
        if bot_response:
            # Update context
            self.context_manager.update_context(phone_number, {
                'bot_responses_count': context.get('bot_responses_count', 0) + 1,
                'last_bot_response': bot_response,
                'user_last_message': message
            })
            
            return {
                'should_escalate': False,
                'escalation_reason': None,
                'bot_response': bot_response,
                'context_updated': True
            }
        else:
            # Bot couldn't handle, escalate
            self.context_manager.update_context(phone_number, {
                'escalation_requested': True,
                'escalation_reason': 'bot_no_response'
            })
            
            return {
                'should_escalate': True,
                'escalation_reason': 'bot_no_response',
                'bot_response': None,
                'context_updated': True
            }
    
    async def _get_enhanced_bot_response(self, message: str, context: Dict, profile_name: str) -> Optional[str]:
        """Get enhanced bot response with context awareness"""
        
        # Add context to the message for better bot understanding
        enhanced_prompt = self._build_enhanced_prompt(message, context, profile_name)
        
        # Try multiple bot services in order
        response = await self._try_ollama_with_context(enhanced_prompt, context)
        if response:
            return response
            
        response = await self._try_rasa_with_context(enhanced_prompt, context)
        if response:
            return response
        
        # Fallback response based on context
        return self._get_fallback_response(message, context, profile_name)
    
    def _build_enhanced_prompt(self, message: str, context: Dict, profile_name: str) -> str:
        """Build enhanced prompt with conversation context"""
        
        conversation_history = ""
        if context.get('bot_responses_count', 0) > 0:
            conversation_history = f"\nHistórico recente: {context.get('user_last_message', '')} -> {context.get('last_bot_response', '')}"
        
        stage = context.get('conversation_stage', 'greeting')
        
        prompt = f"""
        Contexto da conversa:
        - Cliente: {profile_name}
        - Estágio: {stage}
        - Mensagens do bot enviadas: {context.get('bot_responses_count', 0)}{conversation_history}
        
        Mensagem atual: {message}
        
        Responda de forma útil e natural. Se não conseguir ajudar, sugira falar com um atendente.
        """
        
        return prompt
    
    async def _try_ollama_with_context(self, enhanced_prompt: str, context: Dict) -> Optional[str]:
        """Try Ollama with enhanced context"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral",
                        "prompt": enhanced_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 150
                        }
                    },
                    timeout=3.0
                )
                response.raise_for_status()
                result = response.json().get("response", "").strip()
                
                # Filter out responses that indicate the bot should escalate
                if any(phrase in result.lower() for phrase in ['falar com atendente', 'não posso ajudar', 'transferir']):
                    return None
                    
                return result if len(result) > 10 else None
                
        except Exception as e:
            print(f"Erro ao consultar Ollama: {e}")
            return None
    
    async def _try_rasa_with_context(self, enhanced_prompt: str, context: Dict) -> Optional[str]:
        """Try Rasa with enhanced context"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:5005/webhooks/rest/webhook",
                    json={
                        "sender": context.get('phone_number', 'user'),
                        "message": enhanced_prompt
                    },
                    timeout=3.0
                )
                response.raise_for_status()
                responses = response.json()
                
                if responses and len(responses) > 0:
                    text = responses[0].get("text", "")
                    if text and "encaminhar_para_humano" not in text.lower():
                        return text
                        
        except Exception as e:
            print(f"Erro ao consultar Rasa: {e}")
            
        return None
    
    def _get_fallback_response(self, message: str, context: Dict, profile_name: str) -> str:
        """Generate fallback response based on message analysis"""
        
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['oi', 'olá', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            return f"Olá {profile_name}! Como posso ajudá-lo hoje?"
        
        # FAQ responses
        if 'horario' in message_lower or 'funciona' in message_lower:
            return "Nosso horário de atendimento é de segunda a sexta, das 8h às 18h. Aos sábados das 8h às 12h."
        
        if 'preço' in message_lower or 'valor' in message_lower or 'custa' in message_lower:
            return "Para informações sobre preços, um de nossos atendentes pode te ajudar melhor. Gostaria que eu transfira para um atendente?"
        
        if 'contato' in message_lower or 'telefone' in message_lower:
            return "Nosso telefone principal é (11) 1234-5678. Você também pode continuar conversando aqui pelo WhatsApp!"
        
        # Default fallback
        responses = [
            f"Entendi sua mensagem, {profile_name}. Um momento enquanto verifico como posso ajudá-lo melhor.",
            "Obrigado pela sua mensagem. Gostaria que eu transfira para um de nossos atendentes?",
            "Posso tentar ajudá-lo ou, se preferir, posso conectá-lo com um atendente humano."
        ]
        
        # Use different responses based on context
        response_index = context.get('bot_responses_count', 0) % len(responses)
        return responses[response_index]
    
    def get_escalation_message(self, escalation_reason: str, profile_name: str) -> str:
        """Get appropriate escalation message based on reason"""
        
        messages = {
            'user_requested': f"Perfeito, {profile_name}! Vou conectar você com um de nossos atendentes. Um momento, por favor.",
            'max_bot_responses': f"Vou transferir você para um atendente humano que poderá ajudá-lo melhor, {profile_name}.",
            'complex_intent': f"Entendo que sua solicitação é importante, {profile_name}. Vou conectar você com um especialista.",
            'user_frustration': f"Peço desculpas pela confusão, {profile_name}. Vou transferir você para um atendente agora.",
            'previous_escalation': f"Como solicitado, {profile_name}, vou conectar você com um atendente.",
            'bot_no_response': f"Para melhor atendê-lo, {profile_name}, vou conectar você com um de nossos atendentes."
        }
        
        return messages.get(escalation_reason, f"Vou conectar você com um atendente, {profile_name}.")
    
    def cleanup_expired_contexts(self):
        """Clean up expired conversation contexts"""
        self.context_manager.cleanup_expired_contexts()