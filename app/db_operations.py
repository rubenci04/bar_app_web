from flask import current_app
from sqlalchemy import text
from . import db
from .models import Order

def create_order_safely(**kwargs):
    """
    Crea un nuevo pedido de forma segura, asegurándose de que el ID sea único.
    """
    # Obtener el máximo ID actual y actualizar la secuencia
    with db.session.begin_nested():
        max_id = db.session.query(db.func.max(Order.id)).scalar() or 0
        db.session.execute(text(f"SELECT setval('order_id_seq', {max_id + 1}, false)"))
    
    # Crear el nuevo pedido
    new_order = Order(**kwargs)
    db.session.add(new_order)
    
    return new_order