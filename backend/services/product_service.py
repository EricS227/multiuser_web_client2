"""
Product Service - Gerenciamento de Produtos
"""

from sqlmodel import Session, select
from typing import Optional, List
from backend.models.delivery_models import Product


class ProductService:
    """Serviço para gerenciar produtos"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Busca produto pelo ID"""
        return self.session.get(Product, product_id)

    def get_by_name(self, nome: str) -> Optional[Product]:
        """Busca produto pelo nome (P13, P20, etc)"""
        return self.session.exec(
            select(Product).where(Product.nome == nome.upper())
        ).first()

    def list_available(self) -> List[Product]:
        """Lista produtos disponíveis"""
        return list(self.session.exec(
            select(Product)
            .where(Product.ativo == True)
            .where(Product.estoque_atual > 0)
        ).all())

    def list_all(self) -> List[Product]:
        """Lista todos os produtos ativos"""
        return list(self.session.exec(
            select(Product).where(Product.ativo == True)
        ).all())

    def update_stock(self, product_id: int, quantidade: int) -> Optional[Product]:
        """Atualiza estoque (positivo = entrada, negativo = saída)"""
        product = self.get_by_id(product_id)
        if not product:
            return None

        product.estoque_atual += quantidade
        if product.estoque_atual < 0:
            product.estoque_atual = 0

        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def create_default_products(self):
        """Cria produtos padrão se não existirem"""
        defaults = [
            {"nome": "P13", "descricao": "Botijão 13kg", "peso_kg": 13, "preco": 110.00, "preco_troca": 100.00},
            {"nome": "P20", "descricao": "Botijão 20kg", "peso_kg": 20, "preco": 180.00, "preco_troca": 165.00},
            {"nome": "P45", "descricao": "Botijão 45kg", "peso_kg": 45, "preco": 350.00, "preco_troca": 320.00},
        ]

        for data in defaults:
            existing = self.get_by_name(data["nome"])
            if not existing:
                product = Product(**data, estoque_atual=50)
                self.session.add(product)

        self.session.commit()
