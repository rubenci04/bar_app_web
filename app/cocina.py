# app/cocina.py (Archivo Nuevo)

from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from . import db, socketio
from .models import Order, OrderItem, OrderStatus
from .utils import cocina_required
from sqlalchemy.orm import joinedload

cocina_bp = Blueprint('cocina', __name__)

@cocina_bp.route('/kitchen_display')
@cocina_required
def kitchen_display():
    """
    Vista principal para la cocina. Muestra todos los ítems pendientes.
    """
    return render_template('cocina/kitchen_display.html', title="Comandas de Cocina")

@cocina_bp.route('/get_pending_items')
@cocina_required
def get_pending_items():
    """
    Endpoint de API para obtener los ítems pendientes y agruparlos por pedido.
    """
    pending_items = db.session.query(OrderItem).join(Order).filter(
        Order.status.in_([OrderStatus.ACTIVE, OrderStatus.PENDING]),
        OrderItem.status == 'Pendiente'
    ).options(
        joinedload(OrderItem.product),
        joinedload(OrderItem.order)
    ).order_by(Order.created_at).all()

    # Agrupamos los items por pedido
    orders = {}
    for item in pending_items:
        order_id = item.order.id
        if order_id not in orders:
            orders[order_id] = {
                'id': order_id,
                'type': item.order.type,
                'table_number': item.order.table_assigned.number if item.order.table_assigned else None,
                'customer_name': item.order.customer_name,
                'created_at': item.order.created_at.strftime('%H:%M'),
                'items': []
            }
        orders[order_id]['items'].append({
            'id': item.id,
            'name': item.display_name or item.product.name,
            'quantity': item.quantity
        })
        
    return jsonify(list(orders.values()))

@cocina_bp.route('/mark_item_prepared/<int_item_id>', methods=['POST'])
@cocina_required
def mark_item_prepared(item_id):
    """
    Marca un ítem como 'Preparado'.
    """
    item = OrderItem.query.get_or_404(item_id)
    if item.status == 'Pendiente':
        item.status = 'Preparado'
        db.session.commit()
        # Emitimos un evento para notificar a la interfaz de cocina en tiempo real
        socketio.emit('item_status_update', {'item_id': item.id, 'status': 'Preparado'})
        return jsonify({'success': True, 'message': 'Ítem marcado como preparado.'})
    return jsonify({'success': False, 'message': 'El ítem no estaba pendiente.'})