"""
Models para Sistema de Entregas de Botijão de Gás
"""

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class OrderStatus(str, Enum):
    """Status do pedido"""
    NOVO = "novo"
    CONFIRMADO = "confirmado"
    EM_PREPARO = "em_preparo"
    SAIU_ENTREGA = "saiu_entrega"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"


class PaymentMethod(str, Enum):
    """Forma de pagamento"""
    PIX = "pix"
    DINHEIRO = "dinheiro"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"


class PaymentStatus(str, Enum):
    """Status do pagamento"""
    PENDENTE = "pendente"
    PAGO = "pago"
    CANCELADO = "cancelado"


class DriverStatus(str, Enum):
    """Status do entregador"""
    DISPONIVEL = "disponivel"
    OCUPADO = "ocupado"
    OFFLINE = "offline"


# ===== MODELS =====

class Customer(SQLModel, table=True):
    """Cliente - quem faz o pedido"""
    __tablename__ = "customers"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    telefone: str = Field(unique=True, index=True)  # Número WhatsApp
    email: Optional[str] = None

    # Endereço principal
    endereco: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str = Field(default="Curitiba")
    estado: str = Field(default="PR")
    cep: Optional[str] = None

    # Coordenadas para calcular distância/rota
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Referência para entregador encontrar
    ponto_referencia: Optional[str] = None

    # Metadata
    ativo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    # Relacionamentos
    orders: List["Order"] = Relationship(back_populates="customer")


class Product(SQLModel, table=True):
    """Produto - tipos de botijão"""
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(unique=True)  # P13, P20, P45
    descricao: str  # Botijão 13kg, Botijão 20kg, etc.
    peso_kg: float  # 13, 20, 45
    preco: float  # Preço atual
    preco_troca: Optional[float] = None  # Preço com vasilhame de troca

    # Estoque
    estoque_atual: int = Field(default=0)
    estoque_minimo: int = Field(default=10)  # Alerta quando baixo

    # Metadata
    ativo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relacionamentos
    order_items: List["OrderItem"] = Relationship(back_populates="product")


class Driver(SQLModel, table=True):
    """Entregador"""
    __tablename__ = "drivers"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    telefone: str = Field(unique=True)  # WhatsApp do entregador

    # Status atual
    status: DriverStatus = Field(default=DriverStatus.OFFLINE)

    # Localização atual (atualizada pelo app/WhatsApp)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ultima_localizacao: Optional[datetime] = None

    # Veículo
    veiculo: Optional[str] = None  # Moto, Carro, etc.
    placa: Optional[str] = None

    # Capacidade máxima de botijões por viagem
    capacidade_p13: int = Field(default=4)
    capacidade_p20: int = Field(default=2)
    capacidade_p45: int = Field(default=1)

    # Metadata
    ativo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relacionamentos
    deliveries: List["Delivery"] = Relationship(back_populates="driver")


class Order(SQLModel, table=True):
    """Pedido"""
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Cliente
    customer_id: int = Field(foreign_key="customers.id")
    customer: Optional[Customer] = Relationship(back_populates="orders")

    # Status
    status: OrderStatus = Field(default=OrderStatus.NOVO)

    # Endereço de entrega (pode ser diferente do cadastro)
    endereco_entrega: str
    numero_entrega: str
    complemento_entrega: Optional[str] = None
    bairro_entrega: str
    ponto_referencia_entrega: Optional[str] = None
    latitude_entrega: Optional[float] = None
    longitude_entrega: Optional[float] = None

    # Pagamento
    subtotal: float = Field(default=0)
    taxa_entrega: float = Field(default=0)
    desconto: float = Field(default=0)
    total: float = Field(default=0)

    forma_pagamento: Optional[PaymentMethod] = None
    status_pagamento: PaymentStatus = Field(default=PaymentStatus.PENDENTE)
    troco_para: Optional[float] = None  # Se pagar em dinheiro

    # Observações
    observacoes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None

    # Relacionamentos
    items: List["OrderItem"] = Relationship(back_populates="order")
    delivery: Optional["Delivery"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    """Item do pedido"""
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)

    order_id: int = Field(foreign_key="orders.id")
    order: Optional[Order] = Relationship(back_populates="items")

    product_id: int = Field(foreign_key="products.id")
    product: Optional[Product] = Relationship(back_populates="order_items")

    quantidade: int = Field(default=1)
    preco_unitario: float  # Preço no momento do pedido
    tem_troca: bool = Field(default=True)  # Cliente tem vasilhame para trocar?
    subtotal: float


class Delivery(SQLModel, table=True):
    """Entrega - vincula pedido ao entregador"""
    __tablename__ = "deliveries"

    id: Optional[int] = Field(default=None, primary_key=True)

    order_id: int = Field(foreign_key="orders.id", unique=True)
    order: Optional[Order] = Relationship(back_populates="delivery")

    driver_id: int = Field(foreign_key="drivers.id")
    driver: Optional[Driver] = Relationship(back_populates="deliveries")

    # Timestamps da entrega
    atribuido_em: datetime = Field(default_factory=datetime.now)
    saiu_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None

    # Tempo estimado em minutos
    tempo_estimado: Optional[int] = None

    # Distância em km
    distancia_km: Optional[float] = None

    # Assinatura/Confirmação
    confirmado_cliente: bool = Field(default=False)
    foto_entrega: Optional[str] = None  # URL da foto

    # Observações do entregador
    observacoes: Optional[str] = None


class DeliveryHistory(SQLModel, table=True):
    """Histórico de status da entrega"""
    __tablename__ = "delivery_history"

    id: Optional[int] = Field(default=None, primary_key=True)

    delivery_id: int = Field(foreign_key="deliveries.id")

    status_anterior: Optional[str] = None
    status_novo: str

    # Localização no momento da mudança
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    observacao: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
