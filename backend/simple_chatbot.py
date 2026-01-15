"""
Simplified chatbot service without external dependencies
"""
from typing import Dict, Optional
from sqlmodel import Session

class SimpleChatbotService:
    """Simple chatbot service with only local responses"""
    
    def __init__(self, session: Session):
        self.session = session
    
    async def process_message(self, phone_number: str, message: str, profile_name: str = "Cliente") -> Dict:
        """Process message with simple local responses"""
        
        message_lower = message.lower()
        
        # Simple escalation logic
        escalation_keywords = ['atendente', 'operador', 'humano', 'agent', 'help']
        should_escalate = any(keyword in message_lower for keyword in escalation_keywords)
        
        if should_escalate:
            return {
                'should_escalate': True,
                'escalation_reason': 'user_requested',
                'bot_response': None,
                'context_updated': False
            }
        
        # Simple responses
        bot_response = self._get_simple_response(message_lower, profile_name)
        
        if bot_response:
            return {
                'should_escalate': False,
                'escalation_reason': None,
                'bot_response': bot_response,
                'context_updated': False
            }
        else:
            return {
                'should_escalate': True,
                'escalation_reason': 'bot_no_response',
                'bot_response': None,
                'context_updated': False
            }
    
    def _get_simple_response(self, message_lower: str, profile_name: str) -> Optional[str]:
        """Get simple automated response"""
        
        # Greeting
        if any(word in message_lower for word in ['oi', 'ola', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            return f"Olá {profile_name}! Como posso ajudá-lo hoje?"
        
        # Hours
        if 'horario' in message_lower or 'funciona' in message_lower:
            return "Nosso horário de atendimento é de segunda a sexta, das 8h às 18h. Aos sábados das 8h às 12h."
        
        # Contact
        if 'contato' in message_lower or 'telefone' in message_lower:
            return "Nosso telefone principal é (11) 1234-5678. Você também pode continuar conversando aqui pelo WhatsApp!"
        
        # Default response
        return f"Obrigado pela sua mensagem, {profile_name}. Gostaria que eu transfira para um de nossos atendentes?"
    
    def get_escalation_message(self, escalation_reason: str, profile_name: str) -> str:
        """Get escalation message"""
        return f"Perfeito, {profile_name}! Vou conectar você com um de nossos atendentes. Um momento, por favor."