"""
Delivery Service - Gerenciamento de Entregas
"""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from backend.models.delivery_models import (
    Delivery, DeliveryHistory, Order, OrderStatus, Driver, DriverStatus
)


class DeliveryService:
    """Serviço para gerenciar entregas"""

    def __init__(self, session: Session):
        self.session = session

    def assign_driver(
        self,
        order_id: int,
        driver_id: int,
        tempo_estimado: Optional[int] = 30
    ) -> Optional[Delivery]:
        """Atribui entregador ao pedido"""
        order = self.session.get(Order, order_id)
        driver = self.session.get(Driver, driver_id)

        if not order or not driver:
            return None

        # Cria entrega
        delivery = Delivery(
            order_id=order_id,
            driver_id=driver_id,
            tempo_estimado=tempo_estimado,
        )
        self.session.add(delivery)

        # Atualiza status do pedido
        order.status = OrderStatus.EM_PREPARO
        self.session.add(order)

        # Atualiza status do entregador
        driver.status = DriverStatus.OCUPADO
        self.session.add(driver)

        self.session.commit()
        self.session.refresh(delivery)

        # Registra histórico
        self._add_history(delivery.id, None, "atribuido")

        return delivery

    def start_delivery(self, delivery_id: int) -> Optional[Delivery]:
        """Marca que entregador saiu para entrega"""
        delivery = self.session.get(Delivery, delivery_id)
        if not delivery:
            return None

        delivery.saiu_em = datetime.now()
        self.session.add(delivery)

        # Atualiza status do pedido
        if delivery.order:
            delivery.order.status = OrderStatus.SAIU_ENTREGA
            self.session.add(delivery.order)

        self.session.commit()
        self.session.refresh(delivery)

        self._add_history(delivery_id, "atribuido", "saiu_entrega")

        return delivery

    def complete_delivery(
        self,
        delivery_id: int,
        foto_entrega: Optional[str] = None,
        observacoes: Optional[str] = None
    ) -> Optional[Delivery]:
        """Marca entrega como concluída"""
        delivery = self.session.get(Delivery, delivery_id)
        if not delivery:
            return None

        delivery.entregue_em = datetime.now()
        delivery.confirmado_cliente = True
        delivery.foto_entrega = foto_entrega
        delivery.observacoes = observacoes
        self.session.add(delivery)

        # Atualiza status do pedido
        if delivery.order:
            delivery.order.status = OrderStatus.ENTREGUE
            delivery.order.completed_at = datetime.now()
            self.session.add(delivery.order)

        # Libera entregador
        if delivery.driver:
            delivery.driver.status = DriverStatus.DISPONIVEL
            self.session.add(delivery.driver)

        self.session.commit()
        self.session.refresh(delivery)

        self._add_history(delivery_id, "saiu_entrega", "entregue")

        return delivery

    def get_by_order(self, order_id: int) -> Optional[Delivery]:
        """Busca entrega pelo pedido"""
        return self.session.exec(
            select(Delivery).where(Delivery.order_id == order_id)
        ).first()

    def get_active_by_driver(self, driver_id: int) -> List[Delivery]:
        """Lista entregas ativas de um entregador"""
        return list(self.session.exec(
            select(Delivery)
            .where(Delivery.driver_id == driver_id)
            .where(Delivery.entregue_em == None)
        ).all())

    def get_available_driver(self) -> Optional[Driver]:
        """Busca entregador disponível"""
        return self.session.exec(
            select(Driver)
            .where(Driver.status == DriverStatus.DISPONIVEL)
            .where(Driver.ativo == True)
        ).first()

    def _add_history(
        self,
        delivery_id: int,
        status_anterior: Optional[str],
        status_novo: str,
        observacao: Optional[str] = None
    ):
        """Adiciona registro ao histórico"""
        history = DeliveryHistory(
            delivery_id=delivery_id,
            status_anterior=status_anterior,
            status_novo=status_novo,
            observacao=observacao,
        )
        self.session.add(history)
        self.session.commit()
