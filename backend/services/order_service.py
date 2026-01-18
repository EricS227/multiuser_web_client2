"""
Order Service - Gerenciamento de Pedidos
"""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from backend.models.delivery_models import (
    Order, OrderItem, OrderStatus, PaymentMethod, PaymentStatus,
    Customer, Product
)


class OrderService:
    """Serviço para gerenciar pedidos"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Busca pedido pelo ID"""
        return self.session.get(Order, order_id)

    def get_by_customer(self, customer_id: int, apenas_ativos: bool = False) -> List[Order]:
        """Lista pedidos de um cliente"""
        query = select(Order).where(Order.customer_id == customer_id)
        if apenas_ativos:
            query = query.where(Order.status.not_in([OrderStatus.ENTREGUE, OrderStatus.CANCELADO]))
        return list(self.session.exec(query.order_by(Order.created_at.desc())).all())

    def create(
        self,
        customer: Customer,
        items: List[dict],  # [{"product_id": 1, "quantidade": 2, "tem_troca": True}]
        endereco_entrega: Optional[str] = None,
        numero_entrega: Optional[str] = None,
        bairro_entrega: Optional[str] = None,
        complemento_entrega: Optional[str] = None,
        ponto_referencia_entrega: Optional[str] = None,
        observacoes: Optional[str] = None,
        forma_pagamento: Optional[PaymentMethod] = None,
        troco_para: Optional[float] = None,
    ) -> Order:
        """Cria novo pedido"""

        # Usa endereço do cliente se não informado
        order = Order(
            customer_id=customer.id,
            endereco_entrega=endereco_entrega or customer.endereco,
            numero_entrega=numero_entrega or customer.numero,
            bairro_entrega=bairro_entrega or customer.bairro,
            complemento_entrega=complemento_entrega or customer.complemento,
            ponto_referencia_entrega=ponto_referencia_entrega or customer.ponto_referencia,
            latitude_entrega=customer.latitude,
            longitude_entrega=customer.longitude,
            observacoes=observacoes,
            forma_pagamento=forma_pagamento,
            troco_para=troco_para,
        )

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Adiciona itens
        subtotal = 0
        for item_data in items:
            product = self.session.get(Product, item_data["product_id"])
            if not product:
                continue

            tem_troca = item_data.get("tem_troca", True)
            preco = product.preco_troca if tem_troca and product.preco_troca else product.preco
            quantidade = item_data.get("quantidade", 1)
            item_subtotal = preco * quantidade

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantidade=quantidade,
                preco_unitario=preco,
                tem_troca=tem_troca,
                subtotal=item_subtotal,
            )
            self.session.add(order_item)
            subtotal += item_subtotal

        # Atualiza totais
        order.subtotal = subtotal
        order.total = subtotal + order.taxa_entrega - order.desconto
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        return order

    def update_status(
        self,
        order_id: int,
        novo_status: OrderStatus,
        motivo_cancelamento: Optional[str] = None
    ) -> Optional[Order]:
        """Atualiza status do pedido"""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.status = novo_status

        if novo_status == OrderStatus.CONFIRMADO:
            order.confirmed_at = datetime.now()
        elif novo_status == OrderStatus.ENTREGUE:
            order.completed_at = datetime.now()
            order.status_pagamento = PaymentStatus.PAGO
        elif novo_status == OrderStatus.CANCELADO:
            order.cancelled_at = datetime.now()
            order.motivo_cancelamento = motivo_cancelamento

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def confirm(self, order_id: int) -> Optional[Order]:
        """Confirma pedido"""
        return self.update_status(order_id, OrderStatus.CONFIRMADO)

    def cancel(self, order_id: int, motivo: str = "Cancelado pelo cliente") -> Optional[Order]:
        """Cancela pedido"""
        return self.update_status(order_id, OrderStatus.CANCELADO, motivo)

    def list_pending(self) -> List[Order]:
        """Lista pedidos pendentes (novos e confirmados)"""
        return list(self.session.exec(
            select(Order)
            .where(Order.status.in_([OrderStatus.NOVO, OrderStatus.CONFIRMADO]))
            .order_by(Order.created_at)
        ).all())

    def list_in_delivery(self) -> List[Order]:
        """Lista pedidos em entrega"""
        return list(self.session.exec(
            select(Order)
            .where(Order.status.in_([OrderStatus.EM_PREPARO, OrderStatus.SAIU_ENTREGA]))
            .order_by(Order.created_at)
        ).all())

    def get_last_order(self, customer_id: int) -> Optional[Order]:
        """Busca último pedido do cliente"""
        return self.session.exec(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        ).first()
