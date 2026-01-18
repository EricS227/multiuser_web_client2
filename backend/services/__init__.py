"""
Services do Sistema de Entregas
"""

from backend.services.customer_service import CustomerService
from backend.services.order_service import OrderService
from backend.services.delivery_service import DeliveryService
from backend.services.driver_service import DriverService
from backend.services.product_service import ProductService

__all__ = [
    "CustomerService",
    "OrderService",
    "DeliveryService",
    "DriverService",
    "ProductService",
]
