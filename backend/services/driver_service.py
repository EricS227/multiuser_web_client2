"""
Driver Service - Gerenciamento de Entregadores
"""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from backend.models.delivery_models import Driver, DriverStatus


class DriverService:
    """Serviço para gerenciar entregadores"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, driver_id: int) -> Optional[Driver]:
        """Busca entregador pelo ID"""
        return self.session.get(Driver, driver_id)

    def get_by_phone(self, telefone: str) -> Optional[Driver]:
        """Busca entregador pelo telefone"""
        telefone_limpo = telefone.replace("+", "").replace(" ", "").replace("-", "")
        return self.session.exec(
            select(Driver).where(Driver.telefone == telefone_limpo)
        ).first()

    def create(
        self,
        nome: str,
        telefone: str,
        veiculo: Optional[str] = None,
        placa: Optional[str] = None,
    ) -> Driver:
        """Cria novo entregador"""
        driver = Driver(
            nome=nome,
            telefone=telefone.replace("+", "").replace(" ", "").replace("-", ""),
            veiculo=veiculo,
            placa=placa,
        )
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def update_status(self, driver_id: int, status: DriverStatus) -> Optional[Driver]:
        """Atualiza status do entregador"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        driver.status = status
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def update_location(
        self,
        driver_id: int,
        latitude: float,
        longitude: float
    ) -> Optional[Driver]:
        """Atualiza localização do entregador"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        driver.latitude = latitude
        driver.longitude = longitude
        driver.ultima_localizacao = datetime.now()
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def go_online(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador online"""
        return self.update_status(driver_id, DriverStatus.DISPONIVEL)

    def go_offline(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador offline"""
        return self.update_status(driver_id, DriverStatus.OFFLINE)

    def list_available(self) -> List[Driver]:
        """Lista entregadores disponíveis"""
        return list(self.session.exec(
            select(Driver)
            .where(Driver.status == DriverStatus.DISPONIVEL)
            .where(Driver.ativo == True)
        ).all())

    def list_all(self, apenas_ativos: bool = True) -> List[Driver]:
        """Lista todos os entregadores"""
        query = select(Driver)
        if apenas_ativos:
            query = query.where(Driver.ativo == True)
        return list(self.session.exec(query).all())
