# Archivo: app/mozo.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .models import Table, Product, Order, OrderItem
from . import db
from .utils import mozo_required
from sqlalchemy.orm import selectinload
from collections import OrderedDict
from datetime import datetime

mozo_bp = Blueprint('mozo', __name__)

def get_products_by_category():
    products_query = Product.query.filter(Product.stock > 0).order_by(Product.type, Product.name).all()
    products_by_cat = OrderedDict()
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
    tables_query = Table.query.order_by(Table.number).all()
    tables_data = []
    for table in tables_query:
        active_order = Order.query.filter_by(table_id=table.id, status='Activo').first()
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
    current_order = Order.query.filter_by(table_id=table_instance.id, status='Activo').first()
    products_by_category = get_products_by_category()
    pizzas = Product.query.filter_by(type='Pizzas').order_by(Product.name).all()
    
    payment_methods = ['Efectivo', 'Tarjeta', 'Transferencia']

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
    table = Table.query.get_or_404(table_id)
    if table.status == 'Vacía':
        new_order = Order(type='Mesa', table_id=table.id, status='Activo')
        db.session.add(new_order)
        table.status = 'Ocupada'
        db.session.commit()
        flash('Nuevo pedido iniciado en la mesa.', 'success')
    else:
        flash('La mesa ya se encuentra ocupada.', 'warning')
    return redirect(url_for('mozo.table_detail_view', table_id=table.id))

@mozo_bp.route('/order/<int:order_id>/add_item', methods=['POST'])
@mozo_required
def add_item_to_order(order_id):
    order = Order.query.get_or_404(order_id)
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    
    if not product_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Seleccione un producto y una cantidad válida.'}), 400

    product = Product.query.get_or_404(product_id)

    if product.stock < quantity:
        return jsonify({'success': False, 'message': f'Stock insuficiente para {product.name}. Stock actual: {product.stock}.'}), 400

    order_item = OrderItem.query.filter_by(order_id=order.id, product_id=product.id, display_name=None).first()
    if order_item:
        order_item.quantity += quantity
    else:
        order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, unit_price=product.price)
        db.session.add(order_item)
    
    order_item.calculate_subtotal()
    product.stock -= quantity
    
    order.calculate_total()
    db.session.commit()
    
    return jsonify({
        'success': True, 'message': f'{product.name} añadido correctamente.', 'order_total': order.total_amount,
        'item': {
            'id': order_item.id, 'name': product.name, 'quantity': order_item.quantity,
            'unit_price': order_item.unit_price, 'subtotal': order_item.subtotal,
            'product_id': product.id
        },
        'product_stock': product.stock
    })

@mozo_bp.route('/order/<int:order_id>/add_half_pizza', methods=['POST'])
@mozo_required
def add_half_pizza(order_id):
    order = Order.query.get_or_404(order_id)
    pizza1_id = request.form.get('pizza1_id', type=int)
    pizza2_id = request.form.get('pizza2_id', type=int)
    
    if not pizza1_id or not pizza2_id:
        return jsonify({'success': False, 'message': 'Debes seleccionar dos sabores de pizza.'}), 400

    pizza1 = Product.query.get_or_404(pizza1_id)
    pizza2 = Product.query.get_or_404(pizza2_id)
    
    surcharge = 500.0
    final_price = (pizza1.price / 2) + (pizza2.price / 2) + surcharge
    
    display_name = f"Mitad: {pizza1.name} / Mitad: {pizza2.name}"
    
    # Usamos el ID del primer producto como referencia, pero con los datos personalizados
    order_item = OrderItem(
        order_id=order.id,
        product_id=pizza1.id, 
        quantity=1,
        unit_price=final_price,
        display_name=display_name
    )
    
    db.session.add(order_item)
    order.calculate_total()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Pizza combinada añadida con éxito.',
        'order_total': order.total_amount,
        'item': {
            'id': order_item.id,
            'name': order_item.display_name,
            'quantity': order_item.quantity,
            'unit_price': order_item.unit_price,
            'subtotal': order_item.subtotal,
            'product_id': order_item.product_id
        }
    })

@mozo_bp.route('/order_item/<int:item_id>/remove', methods=['POST'])
@mozo_required
def remove_item_from_order(item_id):
    order_item = OrderItem.query.options(selectinload(OrderItem.order), selectinload(OrderItem.product)).get_or_404(item_id)
    order = order_item.order
    product = order_item.product
    
    if order.status not in ['Activo', 'Pendiente']:
        return jsonify({'success': False, 'message': 'No se pueden quitar ítems de un pedido que no esté activo o pendiente.'}), 400

    if product and not order_item.display_name:
        product.stock += order_item.quantity
    
    db.session.delete(order_item)
    
    order.calculate_total()
    db.session.commit()

    return jsonify({
        'success': True, 'message': 'Ítem eliminado.', 'order_total': order.total_amount, 'product_stock': product.stock if product else 0
    })

@mozo_bp.route('/order/<int:order_id>/mark_paid', methods=['POST'])
@mozo_required
def mark_order_paid(order_id):
    order = Order.query.get_or_404(order_id)
    payment_method = request.form.get('payment_method')

    if not payment_method:
        flash('Debe seleccionar un método de pago.', 'danger')
    elif order.status in ['Activo', 'Pendiente'] and order.items:
        order.status = 'Pagado'
        order.payment_method = payment_method
        order.updated_at = datetime.utcnow()
        if order.table_assigned:
            order.table_assigned.status = 'Vacía'
        db.session.commit()
        flash(f'Pedido #{order.id} marcado como pagado con {payment_method}.', 'success')
    else:
        flash('El pedido no se puede marcar como pagado o no tiene ítems.', 'warning')
    
    return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/table/<int:table_id>/liberate', methods=['POST'])
@mozo_required
def liberate_table(table_id):
    table = Table.query.get_or_404(table_id)
    active_order = Order.query.filter_by(table_id=table.id, status='Activo').first()

    if active_order and active_order.items:
        flash(f'No se puede liberar la mesa {table.number} porque tiene un pedido activo con ítems. Cancele o cobre el pedido primero.', 'danger')
        return redirect(url_for('mozo.table_detail_view', table_id=table.id))

    if active_order:
        db.session.delete(active_order)

    table.status = 'Vacía'
    db.session.commit()
    flash(f'Mesa {table.number} liberada y pedido vacío eliminado.', 'success')
    return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@mozo_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order_type = order.type

    if order.status in ['Activo', 'Pendiente']:
        for item in order.items:
            if item.product and not item.display_name:
                item.product.stock += item.quantity
        order.status = 'Cancelado'
        order.updated_at = datetime.utcnow()
        if order.table_assigned and order.table_assigned.status == 'Ocupada':
            order.table_assigned.status = 'Vacía'
        db.session.commit()
        flash(f'Pedido #{order.id} cancelado. El stock ha sido devuelto.', 'success')
    else:
        flash('Este pedido no se puede cancelar.', 'warning')

    redirect_url = url_for('mozo.takeaway_orders_view') if order_type == 'Para Llevar' else url_for('mozo.tables_view')
    return redirect(redirect_url)

@mozo_bp.route('/takeaway')
@mozo_required
def takeaway_orders_view():
    orders = Order.query.filter_by(type='Para Llevar').order_by(Order.created_at.desc()).all()
    return render_template('mozo/takeaway_orders.html', orders=orders, title="Pedidos para Llevar")

@mozo_bp.route('/takeaway/new', methods=['GET', 'POST'])
@mozo_required
def new_takeaway_order():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        if not customer_name:
            flash('El nombre del cliente es obligatorio para crear un pedido.', 'danger')
            return redirect(url_for('mozo.new_takeaway_order'))
        else:
            new_order = Order(type='Para Llevar', customer_name=customer_name, status='Pendiente')
            db.session.add(new_order)
            db.session.commit()
            flash(f"Pedido para '{customer_name}' creado con éxito. Ahora puede añadir ítems.", 'success')
            return redirect(url_for('mozo.takeaway_order_detail', order_id=new_order.id))
    return render_template('mozo/takeaway_form.html', action="Nuevo", title="Nuevo Pedido para Llevar")

@mozo_bp.route('/takeaway/<int:order_id>', methods=['GET', 'POST'])
@mozo_required
def takeaway_order_detail(order_id):
    order = Order.query.filter_by(id=order_id, type='Para Llevar').first_or_404()
    payment_methods = ['Efectivo', 'Tarjeta', 'Transferencia']
    products_by_category = get_products_by_category()
    pizzas = Product.query.filter_by(type='Pizzas').order_by(Product.name).all()

    if request.method == 'POST':
        if order.status == 'Pendiente':
            customer_name = request.form.get('customer_name', '').strip()
            if customer_name:
                order.customer_name = customer_name
                db.session.commit()
                flash('Nombre del cliente actualizado.', 'success')
            else:
                flash('El nombre del cliente no puede estar vacío.', 'danger')
        else:
            flash('No se puede editar un pedido que no esté en estado "Pendiente".', 'warning')
        return redirect(url_for('mozo.takeaway_order_detail', order_id=order.id))
    
    return render_template('mozo/takeaway_form.html', 
                           order=order, 
                           products_by_category=products_by_category, 
                           pizzas=pizzas,
                           payment_methods=payment_methods,
                           action="Editar", 
                           title=f"Pedido Llevar #{order.id}")

@mozo_bp.route('/takeaway/<int:order_id>/mark_paid', methods=['POST'])
@mozo_required
def mark_takeaway_paid(order_id):
    order = Order.query.filter_by(id=order_id, type='Para Llevar').first_or_404()
    payment_method = request.form.get('payment_method')

    if not payment_method:
        flash('Debe seleccionar un método de pago.', 'danger')
        return redirect(url_for('mozo.takeaway_order_detail', order_id=order.id))

    if order.status in ['Pendiente', 'Listo'] and order.items:
        order.status = 'Pagado'
        order.payment_method = payment_method
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Pedido para llevar #{order_id} pagado con {payment_method}.', 'success')
    else:
        flash('El pedido no se puede marcar como pagado, o está vacío.', 'warning')
        return redirect(url_for('mozo.takeaway_order_detail', order_id=order.id))

    return redirect(url_for('mozo.takeaway_orders_view'))

@mozo_bp.route('/takeaway/<int:order_id>/delete', methods=['POST'])
@mozo_required
def delete_takeaway_order(order_id):
    order = Order.query.filter_by(id=order_id, type='Para Llevar').first_or_404()
    if order.status not in ['Pagado', 'Cancelado', 'Venta Anulada']:
        flash('Solo se pueden eliminar pedidos que ya han sido procesados.', 'warning')
    else:
        db.session.delete(order)
        db.session.commit()
        flash(f'Pedido #{order.id} eliminado del historial visible.', 'success')
    return redirect(url_for('mozo.takeaway_orders_view'))