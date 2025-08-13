import httpx
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select
from backend.models import Message, Conversation, BotContext, brazilian_now
import anthropic

class DatabaseContextManager:
    """Manages conversation context with database persistence"""
    
    def __init__(self, session: Session):
        self.session = session
        self.context_timeout = timedelta(hours=2)
    
    def get_context(self, phone_number: str) -> Dict:
        """Get conversation context for a phone number from database"""
        # Try to get existing context from database
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()
        
        if context_record and context_record.expires_at > brazilian_now():
            # Convert database record to dict
            return {
                'phone_number': context_record.phone_number,
                'conversation_stage': context_record.conversation_stage,
                'user_intent': context_record.user_intent,
                'collected_info': json.loads(context_record.collected_info or '{}'),
                'bot_responses_count': context_record.bot_responses_count,
                'escalation_requested': context_record.escalation_requested,
                'escalation_reason': context_record.escalation_reason,
                'last_updated': context_record.last_updated
            }
        
        # Create new context
        new_context = {
            'phone_number': phone_number,
            'conversation_stage': 'greeting',
            'user_intent': None,
            'collected_info': {},
            'bot_responses_count': 0,
            'escalation_requested': False,
            'escalation_reason': None,
            'last_updated': brazilian_now()
        }
        
        # Save to database
        self._save_context_to_db(phone_number, new_context)
        return new_context
    
    def update_context(self, phone_number: str, updates: Dict):
        """Update conversation context in database"""
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()
        
        if not context_record:
            # Create new record
            context_record = BotContext(phone_number=phone_number)
            self.session.add(context_record)
        
        # Update fields
        if 'conversation_stage' in updates:
            context_record.conversation_stage = updates['conversation_stage']
        if 'user_intent' in updates:
            context_record.user_intent = updates['user_intent']
        if 'collected_info' in updates:
            context_record.collected_info = json.dumps(updates['collected_info'])
        if 'bot_responses_count' in updates:
            context_record.bot_responses_count = updates['bot_responses_count']
        if 'escalation_requested' in updates:
            context_record.escalation_requested = updates['escalation_requested']
        if 'escalation_reason' in updates:
            context_record.escalation_reason = updates['escalation_reason']
        
        context_record.last_updated = brazilian_now()
        context_record.expires_at = brazilian_now() + self.context_timeout
        
        self.session.commit()
    
    def _save_context_to_db(self, phone_number: str, context: Dict):
        """Save new context to database"""
        context_record = BotContext(
            phone_number=phone_number,
            conversation_stage=context['conversation_stage'],
            user_intent=context['user_intent'],
            collected_info=json.dumps(context['collected_info']),
            bot_responses_count=context['bot_responses_count'],
            escalation_requested=context['escalation_requested'],
            escalation_reason=context['escalation_reason'],
            last_updated=context['last_updated'],
            expires_at=brazilian_now() + self.context_timeout
        )
        self.session.add(context_record)
        self.session.commit()
    
    def clear_context(self, phone_number: str):
        """Clear conversation context from database"""
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()
        if context_record:
            self.session.delete(context_record)
            self.session.commit()
    
    def cleanup_expired_contexts(self):
        """Clean up expired conversation contexts from database"""
        expired_contexts = self.session.exec(
            select(BotContext).where(BotContext.expires_at < brazilian_now())
        ).all()
        
        for context in expired_contexts:
            self.session.delete(context)
        
        self.session.commit()
        return len(expired_contexts)

class PermanentFallbackBot:
    """Rule-based permanent chatbot that works without external services"""
    
    def __init__(self):
        self.greeting_responses = [
            "Olá! Como posso ajudá-lo hoje? 😊",
            "Olá! Bem-vindo! Em que posso ser útil?",
            "Oi! Fico feliz em atendê-lo! Como posso ajudar?"
        ]
        
        self.business_hours_info = """
📅 Nossos horários de atendimento:

🕘 Segunda a Sexta: 8h às 18h
🕘 Sábado: 8h às 12h  
❌ Domingo: Fechado

Fora desses horários, deixe sua mensagem que retornaremos assim que possível!
"""
        
        self.contact_info = """
📞 Nossos contatos:

📱 WhatsApp: Este número que você está usando
☎️ Telefone: (11) 1234-5678
📧 Email: contato@empresa.com
📍 Endereço: [Seu endereço aqui]

Estou aqui para ajudar no que precisar!
"""
        
        self.faq_responses = {
            'horario': self.business_hours_info,
            'funcionamento': self.business_hours_info,
            'contato': self.contact_info,
            'telefone': self.contact_info,
            'email': self.contact_info,
            'endereco': self.contact_info,
            'preco': "Para informações detalhadas sobre preços, posso conectá-lo com um consultor. Digite 'atendente' se desejar!",
            'valor': "Para informações detalhadas sobre preços, posso conectá-lo com um consultor. Digite 'atendente' se desejar!",
            'servico': "Temos vários serviços disponíveis! Para informações específicas, posso conectá-lo com nossa equipe. Digite 'atendente'!",
            'produto': "Temos vários produtos disponíveis! Para informações específicas, posso conectá-lo com nossa equipe. Digite 'atendente'!"
        }

    def get_response(self, message: str, profile_name: str = "Cliente", context: Dict = None) -> str:
        """Generate rule-based response"""
        message_lower = message.lower().strip()
        
        # Handle greetings
        if any(word in message_lower for word in ['oi', 'ola', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            greeting = f"Olá {profile_name}! 👋 "
            
            if context and context.get('bot_responses_count', 0) > 0:
                greeting += "Que bom ter você de volta! "
            else:
                greeting += "Bem-vindo! "
            
            greeting += """Como posso ajudá-lo hoje? 

🕒 Horários de atendimento
💰 Preços e serviços  
📞 Informações de contato
❓ Dúvidas gerais

Ou digite 'atendente' para falar com nossa equipe!"""
            return greeting
        
        # Handle thanks
        if any(word in message_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks']):
            return f"😊 Por nada, {profile_name}! Fico feliz em ajudar! Se precisar de mais alguma coisa, estarei aqui!"
        
        # Handle FAQ topics
        for keyword, response in self.faq_responses.items():
            if keyword in message_lower:
                return response
        
        # Handle problems/issues
        if any(word in message_lower for word in ['problema', 'erro', 'nao funciona', 'bug', 'defeito']):
            return f"🔧 Entendo que você está com um problema, {profile_name}. Para resolver isso da melhor forma, vou conectar você com nosso suporte técnico. Digite 'atendente' para continuar."
        
        # Handle complaints
        if any(word in message_lower for word in ['reclamacao', 'insatisfeito', 'ruim', 'pessimo']):
            return f"😔 Lamento que tenha tido uma experiência negativa, {profile_name}. Sua opinião é muito importante. Vou conectar você com um supervisor. Digite 'atendente'."
        
        # Default helpful response with options
        responses = [
            f"Recebi sua mensagem, {profile_name}! Para ajudá-lo melhor, posso conectá-lo com um atendente. Digite 'atendente' ou me diga como posso ajudar com:\n\n🕒 Horários\n💰 Preços\n📞 Contato",
            f"Obrigado pela mensagem, {profile_name}! Posso ajudar com informações básicas ou conectá-lo com um especialista. Digite 'atendente' para falar com nossa equipe!",
            f"Entendi, {profile_name}! Para melhor atendê-lo, posso conectar você com um atendente humano. Digite 'atendente' ou me diga sobre o que gostaria de saber!"
        ]
        
        # Use different responses based on context
        response_index = context.get('bot_responses_count', 0) % len(responses) if context else 0
        return responses[response_index]

class ClaudeChatbotRouter:
    """Enhanced routing logic with Claude-specific considerations"""
    
    # Keywords that indicate user wants human help
    ESCALATION_KEYWORDS = [
        'falar com atendente', 'atendente', 'operador', 'humano', 'pessoa',
        'talk to agent', 'agent', 'human', 'operator', 'representative',
        'urgente', 'urgent', 'problema grave', 'serious problem',
        'reclamação', 'complaint', 'insatisfeito', 'dissatisfied'
    ]
    
    # Complex intents that should go to humans
    COMPLEX_INTENTS = [
        'refund', 'reembolso', 'cancelamento', 'cancel', 'estorno',
        'problema técnico', 'technical issue', 'bug', 'falha',
        'conta bloqueada', 'account blocked', 'login problem',
        'cobrança incorreta', 'billing issue', 'pagamento'
    ]
    
    # Topics Claude handles well
    CLAUDE_CAPABLE_INTENTS = [
        'horario', 'hours', 'funcionamento', 'operating',
        'preço', 'price', 'valor', 'cost', 'quanto custa',
        'informação', 'information', 'sobre', 'about',
        'contato', 'contact', 'telefone', 'email',
        'localização', 'location', 'endereço', 'address',
        'duvida', 'question', 'ajuda', 'help'
    ]

    def should_escalate_to_human(self, message: str, context: Dict) -> Tuple[bool, str]:
        """Determine if message should be escalated to human agent"""
        message_lower = message.lower()
        
        # Direct escalation request
        if any(keyword in message_lower for keyword in self.ESCALATION_KEYWORDS):
            return True, "user_requested"
        
        # Too many bot responses without resolution
        if context.get('bot_responses_count', 0) >= 4:  # Increased from 3 since Claude is better
            return True, "max_bot_responses"
        
        # Complex intents that need human help
        if any(intent in message_lower for intent in self.COMPLEX_INTENTS):
            return True, "complex_intent"
        
        # User expressed frustration
        frustration_words = ['não entendi', 'não funciona', 'frustrado', 'irritado', 'confused', 'frustrated', 'não resolve', 'não ajuda']
        if any(word in message_lower for word in frustration_words):
            return True, "user_frustration"
        
        # Previous escalation was requested
        if context.get('escalation_requested'):
            return True, "previous_escalation"
        
        # Check for business hours (can be configured)
        current_hour = brazilian_now().hour
        if current_hour < 8 or current_hour >= 18:  # Outside business hours
            if any(intent in message_lower for intent in self.COMPLEX_INTENTS):
                return True, "outside_business_hours"
        
        return False, "bot_can_handle"

class EnhancedClaudeChatbotService:
    """Enhanced chatbot service with Claude API, database context, and permanent fallbacks"""
    
    def __init__(self, session: Session):
        self.session = session
        self.context_manager = DatabaseContextManager(session)
        self.router = ClaudeChatbotRouter()
        self.fallback_bot = PermanentFallbackBot()
        
        # Initialize Claude client
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = None
        if self.claude_api_key:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                print("Claude API initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Claude API: {e}")
        else:
            print("Claude API key not found - using fallback bot only")
    
    async def process_message(self, phone_number: str, message: str, profile_name: str = "Cliente") -> Dict:
        """Process incoming message and determine appropriate response"""
        
        # Get conversation context from database
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
                'bot_service': None,
                'context_updated': True
            }
        
        # Try to get bot response with multi-tier approach
        bot_response, bot_service = await self._get_multi_tier_response(message, context, profile_name)
        
        if bot_response:
            # Update context in database
            self.context_manager.update_context(phone_number, {
                'bot_responses_count': context.get('bot_responses_count', 0) + 1,
                'last_bot_response': bot_response,
                'user_last_message': message,
                'conversation_stage': self._determine_conversation_stage(message, context)
            })
            
            return {
                'should_escalate': False,
                'escalation_reason': None,
                'bot_response': bot_response,
                'bot_service': bot_service,
                'context_updated': True
            }
        else:
            # Even fallback failed, escalate
            self.context_manager.update_context(phone_number, {
                'escalation_requested': True,
                'escalation_reason': 'all_bots_failed'
            })
            
            return {
                'should_escalate': True,
                'escalation_reason': 'all_bots_failed',
                'bot_response': None,
                'bot_service': None,
                'context_updated': True
            }
    
    async def _get_multi_tier_response(self, message: str, context: Dict, profile_name: str) -> Tuple[Optional[str], str]:
        """Multi-tier bot response system: Claude -> Ollama -> Rasa -> Permanent Fallback"""
        
        # Tier 1: Claude API (Primary)
        if self.claude_client:
            try:
                response = await self._try_claude_api(message, context, profile_name)
                if response:
                    return response, "claude"
            except Exception as e:
                print(f"Claude API failed: {e}")
        
        # Tier 2: Ollama (Secondary)
        try:
            response = await self._try_ollama_with_context(message, context, profile_name)
            if response:
                return response, "ollama"
        except Exception as e:
            print(f"Ollama failed: {e}")
        
        # Tier 3: Rasa (Tertiary) 
        try:
            response = await self._try_rasa_with_context(message, context)
            if response:
                return response, "rasa"
        except Exception as e:
            print(f"Rasa failed: {e}")
        
        # Tier 4: Permanent Fallback (Always Available)
        response = self.fallback_bot.get_response(message, profile_name, context)
        return response, "fallback"
    
    async def _try_claude_api(self, message: str, context: Dict, profile_name: str) -> Optional[str]:
        """Try Claude API with enhanced context"""
        try:
            # Build context-aware prompt
            system_prompt = f"""You are a helpful customer service assistant for a Brazilian company. 
            
Customer name: {profile_name}
Conversation context: {context.get('conversation_stage', 'greeting')} stage
Previous bot responses: {context.get('bot_responses_count', 0)}

Instructions:
- Respond in Portuguese (Brazilian)
- Be friendly, helpful, and professional
- Keep responses concise (under 150 words)
- If you cannot fully help, suggest connecting with a human agent by saying "Digite 'atendente'"
- Handle common business questions: hours, contact info, pricing, services
- For complex issues (refunds, technical problems, billing), recommend human agent
- Use appropriate emojis sparingly
"""
            
            # Add conversation history context
            conversation_history = ""
            if context.get('bot_responses_count', 0) > 0:
                conversation_history = f"Recent context: Customer said '{context.get('user_last_message', '')}' and we responded '{context.get('last_bot_response', '')}'"
            
            user_prompt = f"{conversation_history}\n\nCurrent customer message: {message}"
            
            # Call Claude API
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cost-effective
                max_tokens=200,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            claude_response = response.content[0].text.strip()
            
            # Filter out responses that indicate escalation
            if any(phrase in claude_response.lower() for phrase in ['transferir', 'encaminhar para atendente', 'não posso ajudar completamente']):
                return None
            
            return claude_response if len(claude_response) > 10 else None
            
        except Exception as e:
            print(f"Claude API error: {e}")
            return None
    
    async def _try_ollama_with_context(self, message: str, context: Dict, profile_name: str) -> Optional[str]:
        """Try Ollama with enhanced context (fallback from Claude)"""
        try:
            enhanced_prompt = f"""
            Contexto: Atendimento ao cliente em português brasileiro
            Cliente: {profile_name}
            Estágio da conversa: {context.get('conversation_stage', 'greeting')}
            Respostas do bot anteriores: {context.get('bot_responses_count', 0)}
            
            Mensagem do cliente: {message}
            
            Responda de forma útil e concisa em português. Se não conseguir ajudar completamente, sugira falar com um atendente.
            """
            
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
                    timeout=5.0
                )
                response.raise_for_status()
                result = response.json().get("response", "").strip()
                
                # Filter out escalation responses
                if any(phrase in result.lower() for phrase in ['falar com atendente', 'não posso ajudar', 'transferir']):
                    return None
                    
                return result if len(result) > 10 else None
                
        except Exception as e:
            print(f"Ollama error: {e}")
            return None
    
    async def _try_rasa_with_context(self, message: str, context: Dict) -> Optional[str]:
        """Try Rasa with context (tertiary fallback)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:5005/webhooks/rest/webhook",
                    json={
                        "sender": context.get('phone_number', 'user'),
                        "message": message
                    },
                    timeout=5.0
                )
                response.raise_for_status()
                responses = response.json()
                
                if responses and len(responses) > 0:
                    text = responses[0].get("text", "")
                    if text and "encaminhar_para_humano" not in text.lower():
                        return text
                        
        except Exception as e:
            print(f"Rasa error: {e}")
            
        return None
    
    def _determine_conversation_stage(self, message: str, context: Dict) -> str:
        """Determine conversation stage based on message content"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['oi', 'ola', 'hello', 'hi']):
            return 'greeting'
        elif any(word in message_lower for word in ['preco', 'valor', 'quanto custa']):
            return 'pricing_inquiry'
        elif any(word in message_lower for word in ['problema', 'erro', 'bug']):
            return 'support_request'
        elif any(word in message_lower for word in ['horario', 'funcionamento']):
            return 'info_request'
        elif any(word in message_lower for word in ['obrigado', 'valeu', 'thanks']):
            return 'closing'
        else:
            return context.get('conversation_stage', 'general_inquiry')
    
    def get_escalation_message(self, escalation_reason: str, profile_name: str) -> str:
        """Get appropriate escalation message based on reason"""
        
        messages = {
            'user_requested': f"Perfeito, {profile_name}! Vou conectar você com um de nossos atendentes. Um momento, por favor.",
            'max_bot_responses': f"Para melhor atendê-lo, {profile_name}, vou conectar você com um atendente especializado.",
            'complex_intent': f"Entendo que sua solicitação é importante, {profile_name}. Vou conectar você com um especialista que pode ajudá-lo melhor.",
            'user_frustration': f"Peço desculpas pela confusão, {profile_name}. Vou transferir você para um atendente humano agora.",
            'previous_escalation': f"Como solicitado, {profile_name}, vou conectar você com um atendente.",
            'outside_business_hours': f"Como estamos fora do horário comercial, {profile_name}, vou conectar você com nosso atendente de plantão.",
            'all_bots_failed': f"Para garantir o melhor atendimento, {profile_name}, vou conectar você com nossa equipe.",
            'bot_no_response': f"Para melhor atendê-lo, {profile_name}, vou conectar você com um de nossos atendentes."
        }
        
        return messages.get(escalation_reason, f"Vou conectar você com um atendente, {profile_name}.")
    
    def cleanup_expired_contexts(self):
        """Clean up expired conversation contexts from database"""
        return self.context_manager.cleanup_expired_contexts()