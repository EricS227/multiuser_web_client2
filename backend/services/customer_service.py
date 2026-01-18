"""
Customer Service - Gerenciamento de Clientes
"""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from backend.models.delivery_models import Customer


class CustomerService:
    """Serviço para gerenciar clientes"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_phone(self, telefone: str) -> Optional[Customer]:
        """Busca cliente pelo telefone (WhatsApp)"""
        telefone_limpo = telefone.replace("+", "").replace(" ", "").replace("-", "")
        return self.session.exec(
            select(Customer).where(Customer.telefone == telefone_limpo)
        ).first()

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Busca cliente pelo ID"""
        return self.session.get(Customer, customer_id)

    def create(
        self,
        nome: str,
        telefone: str,
        endereco: str,
        numero: str,
        bairro: str,
        complemento: Optional[str] = None,
        cidade: str = "Curitiba",
        estado: str = "PR",
        cep: Optional[str] = None,
        ponto_referencia: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Customer:
        """Cria novo cliente"""
        telefone_limpo = telefone.replace("+", "").replace(" ", "").replace("-", "")

        customer = Customer(
            nome=nome,
            telefone=telefone_limpo,
            endereco=endereco,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            cep=cep,
            ponto_referencia=ponto_referencia,
            latitude=latitude,
            longitude=longitude,
        )

        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def update(self, customer_id: int, **kwargs) -> Optional[Customer]:
        """Atualiza dados do cliente"""
        customer = self.get_by_id(customer_id)
        if not customer:
            return None

        for key, value in kwargs.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)

        customer.updated_at = datetime.now()
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def get_or_create(self, telefone: str, nome: str = "Cliente") -> tuple[Customer, bool]:
        """Busca cliente ou cria um novo básico"""
        customer = self.get_by_phone(telefone)
        if customer:
            return customer, False

        # Cria cliente básico (sem endereço completo ainda)
        customer = Customer(
            nome=nome,
            telefone=telefone.replace("+", "").replace(" ", "").replace("-", ""),
            endereco="A definir",
            numero="",
            bairro="A definir",
        )
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer, True

    def list_all(self, apenas_ativos: bool = True) -> List[Customer]:
        """Lista todos os clientes"""
        query = select(Customer)
        if apenas_ativos:
            query = query.where(Customer.ativo == True)
        return list(self.session.exec(query).all())
