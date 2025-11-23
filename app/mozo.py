# Archivo: app/mozo.py (Versión Mejorada con CRUD de Cantidades)
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .models import Table, Product, Order, OrderItem, TableStatus, OrderStatus
from . import db, socketio, cache
from .utils import mozo_required
from sqlalchemy.orm import joinedload, selectinload
from collections import OrderedDict
from datetime import datetime

mozo_bp = Blueprint('mozo', __name__)

@cache.memoize(timeout=600)
def get_products_by_category():
    products_query = Product.query.filter(Product.stock > 0).order_by(Product.type, Product.name).all()
    products_by_cat = OrderedDict()
    # [Yo]: Mantengo tu orden preferido de categorías, es vital para la velocidad del mozo.
    preferred_categories = [
        "Sandwiches", "Hamburguesas", "Pizzas", "Napolitanas", "Tostados", 
        "Papas", "Agregados", "Bebidas c/Alcohol", "Bebidas s/Alcohol", "Postre", "Otro"
    ]
    for cat_name in preferred_categories:
        products_by_cat[cat_name] = []
    for product in products_query:
        if product.type not in products_by_cat:
            products_by_cat[product.type] = []
        products_by_cat[product.type].append(product)
    
    final_products_by_cat = OrderedDict()
    for cat_name, prods_in_cat in products_by_cat.items():
        if prods_in_cat:
            final_products_by_cat[cat_name] = prods_in_cat
    return final_products_by_cat

@mozo_bp.route('/tables')
@mozo_required
def tables_view():
    tables_with_orders = db.session.query(Table).options(
        joinedload(Table.orders.and_(Order.status == 'Activo'))
    ).order_by(Table.number).all()

    tables_data = []
    for table in tables_with_orders:
        active_order = next((o for o in table.orders if o.status == 'Activo'), None)
        total_pedido_activo = active_order.total_amount if active_order else 0.0
        tables_data.append({
            'id': table.id, 'number': table.number, 'capacity': table.capacity,
            'status': table.status, 'total_pedido_activo': total_pedido_activo
        })
    return render_template('mozo/tables.html', tables_data=tables_data, title="Mesas del Restaurante")

@mozo_bp.route('/table/<int:table_id>')
@mozo_required
def table_detail_view(table_id):
    table_instance = Table.query.get_or_404(table_id)
    current_order = Order.query.filter(
        Order.table_id == table_instance.id,
        Order.status.in_([OrderStatus.ACTIVE, OrderStatus.PAID])
    ).first()
    
    products_by_category = get_products_by_category()
    pizzas = Product.query.filter_by(type='Pizzas').order_by(Product.name).all()
    payment_methods = ['Efectivo', 'Transferencia']

    return render_template('mozo/table_detail.html', 
                           table=table_instance, 
                           current_order=current_order, 
                           products_by_category=products_by_category, 
                           pizzas=pizzas,
                           payment_methods=payment_methods,
                           title=f"Mesa {table_instance.number}")

@mozo_bp.route('/table/<int:table_id>/start_order', methods=['POST'])
@mozo_required
def start_table_order(table_id):
    try:
        table = Table.query.get_or_404(table_id)
        if table.status != TableStatus.EMPTY:
            flash('La mesa ya se encuentra ocupada.', 'warning')
            return redirect(url_for('mozo.table_detail_view', table_id=table.id))

        # [Yo]: Limpieza de seguridad por si quedaron pedidos 'huerfanos' viejos
        old_orders = Order.query.filter(
            Order.table_id == table.id,
            Order.status.in_([OrderStatus.ACTIVE, OrderStatus.PENDING, OrderStatus.PAID])
        ).all()

        if old_orders:
            for order in old_orders:
                db.session.delete(order)
            db.session.commit()

        new_order = Order(type='Mesa', table_id=table.id, status=OrderStatus.ACTIVE)
        db.session.add(new_order)
        table.status = TableStatus.OCCUPIED
        db.session.commit()
        socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status})
        flash('Nuevo pedido iniciado en la mesa.', 'success')

        return redirect(url_for('mozo.table_detail_view', table_id=table.id))

    except Exception as e:
        db.session.rollback()
        flash('Error al iniciar pedido. Intente nuevamente.', 'danger')
        return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/order/<int:order_id>/add_item', methods=['POST'])
@mozo_required
def add_item_to_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PENDING]:
        return jsonify({'success': False, 'message': 'Pedido cerrado.'}), 400

    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    
    product = Product.query.get_or_404(product_id)

    if product.stock < quantity:
        return jsonify({'success': False, 'message': f'Sin stock suficiente. Quedan: {product.stock}.'}), 400

    try:
        # [Yo]: Busco si ya existe el ítem. Si es así, sumo cantidad. Si no, creo uno nuevo.
        order_item = OrderItem.query.filter_by(order_id=order.id, product_id=product.id, display_name=None).first()
        if order_item:
            order_item.quantity += quantity
            order_item.calculate_subtotal()
        else:
            order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, unit_price=product.price)
            db.session.add(order_item)
        
        product.stock -= quantity
        order.calculate_total()
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': f'{product.name} añadido.',
            'order_total': order.total_amount, 
            'items': _serialize_items(order) # [Yo]: Refactoricé esto en una función auxiliar abajo
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al agregar producto.'}), 500

# [Yo]: ESTA ES LA NUEVA FUNCIÓN CLAVE PARA EDITAR CANTIDADES
@mozo_bp.route('/order_item/<int:item_id>/update_quantity', methods=['POST'])
@mozo_required
def update_item_quantity(item_id):
    # [Yo]: Cargo el item con sus relaciones para no hacer consultas extra
    order_item = OrderItem.query.options(selectinload(OrderItem.order), selectinload(OrderItem.product)).get_or_404(item_id)
    order = order_item.order
    product = order_item.product
    
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PENDING]:
        return jsonify({'success': False, 'message': 'No se puede editar un pedido cerrado.'}), 400

    try:
        change = request.form.get('change', type=int) # +1 o -1
        if not change:
            return jsonify({'success': False, 'message': 'Cambio inválido.'}), 400

        # [Yo]: Lógica crítica de stock
        if change > 0: # Aumentar cantidad
            if product and product.stock < change:
                return jsonify({'success': False, 'message': f'Stock insuficiente.'}), 400
            if product: product.stock -= change
            order_item.quantity += change
            
        elif change < 0: # Disminuir cantidad
            # [Yo]: Si la cantidad llega a 0, eliminamos el ítem
            if order_item.quantity + change <= 0:
                if product: product.stock += order_item.quantity # Devolvemos todo el stock
                db.session.delete(order_item)
            else:
                if product: product.stock += abs(change) # Devolvemos solo la diferencia
                order_item.quantity += change

        order_item.calculate_subtotal()
        order.calculate_total()
        db.session.commit()

        return jsonify({
            'success': True,
            'order_total': order.total_amount,
            'items': _serialize_items(order)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error updating quantity: {e}")
        return jsonify({'success': False, 'message': 'Error al actualizar cantidad.'}), 500

@mozo_bp.route('/order/<int:order_id>/add_half_pizza', methods=['POST'])
@mozo_required
def add_half_pizza(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PENDING]:
        return jsonify({'success': False, 'message': 'Pedido cerrado.'}), 400
        
    pizza1_id = request.form.get('pizza1_id', type=int)
    pizza2_id = request.form.get('pizza2_id', type=int)
    
    if not pizza1_id or not pizza2_id:
        return jsonify({'success': False, 'message': 'Faltan datos.'}), 400

    pizza1 = Product.query.get(pizza1_id)
    pizza2 = Product.query.get(pizza2_id)
    
    surcharge_prod = Product.query.filter_by(name="Recargo Pizza Mitad/Mitad").first()
    surcharge = surcharge_prod.price if surcharge_prod else 500.0
    
    final_price = (pizza1.price / 2) + (pizza2.price / 2) + surcharge
    display_name = f"Mitad: {pizza1.name} / Mitad: {pizza2.name}"
    
    # [Yo]: Asigno el ID de producto del más caro para descontar stock o estadísticas
    ref_product_id = pizza1.id if pizza1.price >= pizza2.price else pizza2.id
    
    order_item = OrderItem(order_id=order.id, product_id=ref_product_id, quantity=1, unit_price=final_price, display_name=display_name)
    db.session.add(order_item)
    order.calculate_total()
    db.session.commit()
    
    return jsonify({
        'success': True, 'message': 'Pizza añadida.',
        'order_total': order.total_amount, 'items': _serialize_items(order)
    })

@mozo_bp.route('/order_item/<int:item_id>/remove', methods=['POST'])
@mozo_required
def remove_item_from_order(item_id):
    order_item = OrderItem.query.options(selectinload(OrderItem.order), selectinload(OrderItem.product)).get_or_404(item_id)
    order = order_item.order
    
    if order.status not in [OrderStatus.ACTIVE, OrderStatus.PENDING]:
        return jsonify({'success': False, 'message': 'Pedido cerrado.'}), 400

    if order_item.product and not order_item.display_name:
        order_item.product.stock += order_item.quantity
    
    db.session.delete(order_item)
    order.calculate_total()
    db.session.commit()

    return jsonify({
        'success': True, 'message': 'Ítem eliminado.',
        'order_total': order.total_amount, 'items': _serialize_items(order)
    })

@mozo_bp.route('/order/<int:order_id>/mark_paid', methods=['POST'])
@mozo_required
def mark_order_paid(order_id):
    order = Order.query.get_or_404(order_id)
    payment_method = request.form.get('payment_method')
    table_id = order.table_id

    if not payment_method:
        flash('Seleccione método de pago.', 'danger')
    elif order.status == OrderStatus.ACTIVE and order.items:
        order.status = OrderStatus.PAID
        order.payment_method = payment_method
        order.updated_at = datetime.utcnow()
        if order.table_assigned:
            order.table_assigned.status = TableStatus.PAID
            socketio.emit('table_status_update', {'table_id': order.table_assigned.id, 'status': order.table_assigned.status})
        db.session.commit()
        flash(f'Pedido #{order.id} cobrado.', 'success')
    else:
        flash('No se puede cobrar (verifique estado o ítems).', 'warning')
    
    if table_id:
        return redirect(url_for('mozo.table_detail_view', table_id=table_id))
    return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/table/<int:table_id>/clear', methods=['POST'])
@mozo_required
def clear_table(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status == TableStatus.PAID:
        table.status = TableStatus.EMPTY
        db.session.commit()
        socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status})
        flash(f'Mesa {table.number} liberada.', 'success')
    else:
        flash('La mesa debe estar Pagada para liberarse.', 'warning')
        return redirect(url_for('mozo.table_detail_view', table_id=table.id))
        
    return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@mozo_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    table_id = order.table_id
    order_type = order.type

    if order.status in [OrderStatus.ACTIVE, OrderStatus.PENDING]:
        # Devolver stock
        for item in order.items:
            if item.product and not item.display_name:
                item.product.stock += item.quantity
        
        if order.table_assigned:
            order.table_assigned.status = TableStatus.EMPTY
            socketio.emit('table_status_update', {'table_id': order.table_assigned.id, 'status': order.table_assigned.status})
        
        db.session.delete(order)
        db.session.commit()
        flash(f'Pedido #{order.id} cancelado. Stock devuelto.', 'success')
    else:
        flash('No se puede cancelar este pedido.', 'warning')

    if order_type == 'Mesa' and table_id:
        return redirect(url_for('mozo.tables_view'))
    return redirect(url_for('mozo.takeaway_orders_view'))

# --- RUTAS TAKEAWAY (Simplificadas visualmente, lógica igual) ---
@mozo_bp.route('/takeaway')
@mozo_required
def takeaway_orders_view():
    orders = Order.query.filter(Order.type == 'Para Llevar', Order.status == OrderStatus.PENDING).order_by(Order.created_at.desc()).all()
    return render_template('mozo/takeaway_orders.html', orders=orders, title="Pedidos para Llevar")

@mozo_bp.route('/takeaway/new', methods=['GET', 'POST'])
@mozo_required
def new_takeaway_order():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        if not customer_name:
            flash('Nombre del cliente obligatorio.', 'danger')
            return redirect(url_for('mozo.new_takeaway_order'))
        try:
            new_order = Order(type='Para Llevar', customer_name=customer_name, status=OrderStatus.PENDING)
            db.session.add(new_order)
            db.session.commit()
            return redirect(url_for('mozo.takeaway_order_detail', order_id=new_order.id))
        except Exception:
            db.session.rollback()
            flash('Error al crear pedido.', 'danger')
    return render_template('mozo/takeaway_form.html', action="Nuevo", title="Nuevo Pedido")

@mozo_bp.route('/takeaway/<int:order_id>', methods=['GET', 'POST'])
@mozo_required
def takeaway_order_detail(order_id):
    order = Order.query.filter_by(id=order_id, type='Para Llevar').first_or_404()
    products_by_category = get_products_by_category()
    pizzas = Product.query.filter_by(type='Pizzas').order_by(Product.name).all()
    payment_methods = ['Efectivo', 'Transferencia']

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        if customer_name:
            order.customer_name = customer_name
            db.session.commit()
            flash('Nombre actualizado.', 'success')
        return redirect(url_for('mozo.takeaway_order_detail', order_id=order.id))
    
    return render_template('mozo/takeaway_form.html', order=order, products_by_category=products_by_category, pizzas=pizzas, payment_methods=payment_methods, title=f"Pedido Llevar #{order.id}")

@mozo_bp.route('/takeaway/<int:order_id>/mark_paid', methods=['POST'])
@mozo_required
def mark_takeaway_paid(order_id):
    order = Order.query.get_or_404(order_id)
    payment_method = request.form.get('payment_method')
    if payment_method and order.status == OrderStatus.PENDING and order.items:
        order.status = OrderStatus.PAID
        order.payment_method = payment_method
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Pedido pagado.', 'success')
    else:
        flash('Error al cobrar.', 'danger')
    return redirect(url_for('mozo.takeaway_orders_view'))

@mozo_bp.route('/takeaway/bulk_pay', methods=['POST'])
@mozo_required
def bulk_pay_orders():
    try:
        data = request.get_json()
        order_ids = data.get('order_ids', [])
        payment_method = data.get('payment_method')
        if not order_ids or not payment_method: return jsonify({'success': False}), 400
        
        count = 0
        for oid in order_ids:
            o = Order.query.get(oid)
            if o and o.status == OrderStatus.PENDING and o.items:
                o.status = OrderStatus.PAID
                o.payment_method = payment_method
                o.updated_at = datetime.utcnow()
                count += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'{count} pedidos cobrados.'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False}), 500

@mozo_bp.route('/takeaway/bulk_action', methods=['POST'])
@mozo_required
def takeaway_bulk_action():
    action = request.form.get('action')
    order_ids = [int(x) for x in request.form.getlist('order_ids')]
    orders = Order.query.filter(Order.id.in_(order_ids)).all()
    count = 0
    if action == 'cancel':
        for o in orders:
            if o.status == OrderStatus.PENDING:
                o.status = OrderStatus.CANCELED
                o.updated_at = datetime.utcnow()
                count += 1
    elif action == 'clear':
        for o in orders:
            if o.status in [OrderStatus.PAID, OrderStatus.CANCELED]:
                db.session.delete(o)
                count += 1
    db.session.commit()
    flash(f'Acción completada en {count} pedidos.', 'info')
    return redirect(url_for('mozo.takeaway_orders_view'))

# [Yo]: Función auxiliar para no repetir código de serialización en cada endpoint
def _serialize_items(order):
    return [{
        'id': item.id, 
        'name': item.display_name or item.product.name,
        'quantity': item.quantity, 
        'unit_price': item.unit_price,
        'subtotal': item.subtotal, 
        'product_id': item.product_id
    } for item in order.items]