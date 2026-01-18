"""
Order Bot Service - Detecta intenção de pedido e escala para atendente
"""

import re
from typing import Tuple


class OrderBotService:
    """Detecta se cliente quer fazer pedido e escala para atendente"""

    # Palavras-chave que indicam pedido
    ORDER_KEYWORDS = [
        'quero', 'preciso', 'pedir', 'pedido', 'comprar',
        'gas', 'gás', 'botijao', 'botijão',
        'p13', 'p20', 'p45', '13kg', '20kg', '45kg',
        'entrega', 'entregar', 'trazer', 'mandar',
        'troca', 'vazio', 'cheio',
        'quanto', 'preço', 'preco', 'valor',
        'cardapio', 'cardápio', 'menu', 'produtos',
    ]

    def detect_order_intent(self, message: str) -> bool:
        """Detecta se a mensagem tem intenção de pedido"""
        message_lower = message.lower()

        for keyword in self.ORDER_KEYWORDS:
            if keyword in message_lower:
                return True

        return False

    def get_escalation_response(self) -> str:
        """Resposta padrão ao detectar pedido"""
        return (
            "Entendi que você quer fazer um pedido! "
            "Vou transferir você para um atendente que vai te ajudar. "
            "Aguarde um momento..."
        )

    def get_menu_response(self) -> str:
        """Retorna cardápio básico"""
        return """*Nossos Produtos:*

*P13* (13kg)
  Com troca: R$ 100,00
  Sem troca: R$ 110,00

*P20* (20kg)
  Com troca: R$ 165,00
  Sem troca: R$ 180,00

*P45* (45kg)
  Com troca: R$ 320,00
  Sem troca: R$ 350,00

Para fazer um pedido, aguarde um atendente!"""

    def process_message(self, message: str) -> Tuple[bool, str]:
        """
        Processa mensagem e retorna (deve_escalar, resposta)
        """
        message_lower = message.lower()

        # Se perguntou cardápio/preço
        if any(word in message_lower for word in ['cardapio', 'cardápio', 'menu', 'preço', 'preco', 'valor', 'quanto']):
            return True, self.get_menu_response() + "\n\n" + self.get_escalation_response()

        # Se detectou intenção de pedido
        if self.detect_order_intent(message):
            return True, self.get_escalation_response()

        # Não é pedido
        return False, ""
