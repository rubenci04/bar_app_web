# Archivo: app/admin.py (Versión Completa y Corregida)
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app, make_response
from . import db, cache, socketio
from .models import Product, Order, OrderItem, Table, User, CashSession, OrderStatus, TableStatus, UserRoles
from .utils import admin_required, mozo_required, get_current_time, convert_to_local_time, retry_on_db_error
from datetime import datetime, date, timedelta
from sqlalchemy import func
from flask_login import current_user
from werkzeug.datastructures import ImmutableMultiDict
from .exceptions import ConnectionError, ValidationError, TransactionError

admin_bp = Blueprint('admin', __name__)

ITEMS_PER_PAGE = 10

@cache.memoize(timeout=300)
def get_distinct_categories():
    try:
        db_categories_query = db.session.query(Product.type)\
            .filter(Product.type.isnot(None), Product.type != '')\
            .distinct().order_by(Product.type).all()
        categories = [category[0] for category in db_categories_query]
        current_app.logger.info(f"Categorías obtenidas de la base de datos (y guardadas en caché): {categories}")
        return categories
    except Exception as e:
        current_app.logger.error(f'Error al obtener categorías: {str(e)}')
        return []

def invalidate_product_cache():
    """Limpia el caché de categorías de productos."""
    cache.delete_memoized(get_distinct_categories)
    current_app.logger.info("Caché de categorías de productos invalidado.")

# Reemplaza la función dashboard completa en app/admin.py

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    
    # Restauro estas 3 líneas para calcular las ventas del día desglosadas
    total_sales_today = db.session.query(func.sum(Order.total_amount)).filter(func.date(Order.updated_at) == today, Order.status == OrderStatus.PAID).scalar() or 0.0
    sales_today_table = db.session.query(func.sum(Order.total_amount)).filter(db.func.date(Order.updated_at) == today, Order.status == OrderStatus.PAID, Order.type == 'Mesa').scalar() or 0.0
    sales_today_takeaway = db.session.query(func.sum(Order.total_amount)).filter(db.func.date(Order.updated_at) == today, Order.status == OrderStatus.PAID, Order.type == 'Para Llevar').scalar() or 0.0
    
    active_orders_count = Order.query.filter(Order.status.in_([OrderStatus.ACTIVE, OrderStatus.PENDING])).count()
    tables_occupied_count = Table.query.filter(Table.status == TableStatus.OCCUPIED).count()
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(OrderItem).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    top_products_labels = [p.name for p in top_products]
    top_products_data = [p.total_quantity for p in top_products]

    return render_template('admin/dashboard.html', 
        title="Panel de Administrador",
        total_sales_today=total_sales_today,
        # Me aseguro de pasar las variables a la plantilla
        sales_today_table=sales_today_table,
        sales_today_takeaway=sales_today_takeaway,
        active_orders_count=active_orders_count,
        tables_occupied_count=tables_occupied_count,
        top_products=top_products,
        top_products_labels=json.dumps(top_products_labels),
        top_products_data=json.dumps(top_products_data)
    )

@admin_bp.route('/products')
@mozo_required
@retry_on_db_error(max_retries=3)
def products():
    page = request.args.get('page', 1, type=int)
    search_name = request.args.get('search_name', '').strip()
    search_category = request.args.get('search_category', '').strip()
    
    query = Product.query
    if search_name:
        query = query.filter(Product.name.ilike(f'%{search_name}%'))
    if search_category:
        query = query.filter(Product.type == search_category)
        
    pagination = query.order_by(Product.type, Product.name).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    
    return render_template('admin/products.html', 
        products_on_page=pagination.items,
        title="Gestionar Productos",
        pagination=pagination,
        search_name_value=search_name,
        search_category_value=search_category,
        distinct_categories_for_filter=get_distinct_categories()
    )

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@mozo_required
@retry_on_db_error(max_retries=3)
def add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price')
        product_type = request.form.get('type')
        stock_str = request.form.get('stock')
        description = request.form.get('description', '').strip()
        new_category = request.form.get('new_category', '').strip()
        
        if not all([name, price_str, product_type, stock_str]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product=request.form)

        if product_type == 'Otro':
            if not new_category:
                flash('Debe especificar el nombre de la nueva categoría.', 'danger')
                return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product=request.form)
            product_type = new_category

        try:
            price = float(price_str.replace(',', '.'))
            if price <= 0: raise ValueError()
        except (ValueError, TypeError):
            flash('El precio debe ser un número válido y mayor a 0.', 'danger')
            return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product=request.form)

        try:
            stock = int(stock_str)
            if stock < 0: raise ValueError()
        except (ValueError, TypeError):
            flash('El stock debe ser un número entero válido y no negativo.', 'danger')
            return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product=request.form)

        if Product.query.filter(func.lower(Product.name) == func.lower(name)).first():
            flash('Ya existe un producto con este nombre.', 'danger')
            return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product=request.form)

        new_product = Product(name=name, price=price, type=product_type, stock=stock, description=description)
        db.session.add(new_product)
        db.session.commit()
        invalidate_product_cache()
        flash('Producto añadido con éxito.', 'success')
        return redirect(url_for('admin.products'))
    
    return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), product={})

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@mozo_required
@retry_on_db_error(max_retries=3)
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price')
        product_type = request.form.get('type')
        stock_str = request.form.get('stock')
        description = request.form.get('description', '').strip()
        new_category = request.form.get('new_category', '').strip()
        
        if not all([name, price_str, product_type, stock_str]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('admin/product_form.html', action="Editar", title=f"Editar Producto: {name}", categories=get_distinct_categories(), product=request.form)

        if product_type == 'Otro':
            if not new_category:
                flash('Debe especificar el nombre de la nueva categoría.', 'danger')
                return render_template('admin/product_form.html', action="Editar", title=f"Editar Producto: {name}", categories=get_distinct_categories(), product=request.form)
            product_type = new_category

        try:
            price = float(price_str.replace(',', '.'))
            if price <= 0: raise ValueError()
        except (ValueError, TypeError):
            flash('El precio debe ser un número válido y mayor a 0.', 'danger')
            return render_template('admin/product_form.html', action="Editar", title=f"Editar Producto: {name}", categories=get_distinct_categories(), product=request.form)

        try:
            stock = int(stock_str)
            if stock < 0: raise ValueError()
        except (ValueError, TypeError):
            flash('El stock debe ser un número entero válido y no negativo.', 'danger')
            return render_template('admin/product_form.html', action="Editar", title=f"Editar Producto: {name}", categories=get_distinct_categories(), product=request.form)

        existing_product = Product.query.filter(Product.id != product_id, func.lower(Product.name) == func.lower(name)).first()
        if existing_product:
            flash('Ya existe otro producto con ese nombre.', 'danger')
            return render_template('admin/product_form.html', action="Editar", title=f"Editar Producto: {name}", categories=get_distinct_categories(), product=request.form)

        product.name = name
        product.price = price
        product.type = product_type
        product.stock = stock
        product.description = description
        db.session.commit()
        invalidate_product_cache()
        flash('Producto actualizado con éxito.', 'success')
        return redirect(url_for('admin.products'))

    return render_template('admin/product_form.html', action="Editar", 
                         title=f"Editar Producto: {product.name}",
                         categories=get_distinct_categories(), product=product)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@mozo_required
@retry_on_db_error(max_retries=3)
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if OrderItem.query.filter_by(product_id=product.id).first():
        flash('No se puede eliminar el producto porque está asociado a uno o más pedidos existentes.', 'danger')
    else:
        db.session.delete(product)
        db.session.commit()
        invalidate_product_cache()
        flash('Producto eliminado con éxito.', 'success')
    return redirect(url_for('admin.products'))

@admin_bp.route('/sales-reports')
@mozo_required
def sales_and_reports():
    page = request.args.get('page', 1, type=int)
    period = request.args.get('period', 'today')
    # (El resto de la lógica de filtros y fechas se mantiene)
    now = get_current_time()
    start_date, end_date = None, None
    
    # Lógica de fechas (sin cambios)
    reference_date = now.date()
    if period == 'today':
        start_date = datetime.combine(reference_date, datetime.min.time())
        end_date = datetime.combine(reference_date, datetime.max.time())
    elif period == 'week':
        start_of_week = reference_date - timedelta(days=reference_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_date = datetime.combine(start_of_week, datetime.min.time())
        end_date = datetime.combine(end_of_week, datetime.max.time())
    elif period == 'month':
        start_of_month = reference_date.replace(day=1)
        next_month = start_of_month.replace(day=28) + timedelta(days=4)
        end_of_month = next_month - timedelta(days=next_month.day)
        start_date = datetime.combine(start_of_month, datetime.min.time())
        end_date = datetime.combine(end_of_month, datetime.max.time())
    else: # 'year'
        start_of_year = reference_date.replace(day=1, month=1)
        end_of_year = reference_date.replace(day=31, month=12)
        start_date = datetime.combine(start_of_year, datetime.min.time())
        end_date = datetime.combine(end_of_year, datetime.max.time())

    # --- AQUÍ EMPIEZA LA LÓGICA COMPLETA ---
    stats_query = Order.query.filter(Order.status == OrderStatus.PAID, Order.updated_at.between(start_date, end_date))
    
    # 1. Cálculos para las tarjetas superiores
    total_ingresos = stats_query.with_entities(func.sum(Order.total_amount)).scalar() or 0.0
    total_pedidos = stats_query.count()
    promedio_por_pedido = total_ingresos / total_pedidos if total_pedidos > 0 else 0.0

    # 2. Datos para Gráfico de Ventas por Día (y tabla)
    ventas_por_dia = stats_query.with_entities(
        func.date(Order.updated_at).label('dia'),
        func.sum(Order.total_amount).label('total_diario')
    ).group_by('dia').order_by('dia').all()
    
    sales_by_day_labels = []
    for v in ventas_por_dia:
        dia_obj = v.dia
        if isinstance(dia_obj, str):
            dia_obj = datetime.strptime(dia_obj, '%Y-%m-%d').date()
        sales_by_day_labels.append(dia_obj.strftime('%d/%m'))
    sales_by_day_data = [v.total_diario for v in ventas_por_dia]

    # 3. Datos para Gráfico y Tabla de Top Productos
    base_items_query = OrderItem.query.join(Order).filter(Order.id.in_([o.id for o in stats_query.all()]))
    ranking_productos = base_items_query.join(Product).with_entities(
        Product.name, func.sum(OrderItem.quantity).label('total_quantity')
    ).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    top_products_labels = [p.name for p in ranking_productos]
    top_products_data = [p.total_quantity for p in ranking_productos]
    
    # 4. RESTAURO LOS CÁLCULOS PARA LAS OTRAS TABLAS
    categorias_populares = base_items_query.join(Product).with_entities(
        Product.type,
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).group_by(Product.type).order_by(func.sum(OrderItem.subtotal).desc()).limit(5).all()

    payment_methods_summary = stats_query.with_entities(
        Order.payment_method,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('total')
    ).filter(Order.payment_method.isnot(None)).group_by(Order.payment_method).order_by(func.count(Order.id).desc()).all()

    # 5. Registro detallado de ventas (Paginación)
    log_query = Order.query.filter(Order.status.in_([OrderStatus.PAID, OrderStatus.ANNULLED])).order_by(Order.updated_at.desc())
    pagination = log_query.paginate(page=page, per_page=15, error_out=False)

    return render_template('admin/sales_and_reports.html', 
        title="Ventas y Reportes",
        subtitle=f"para {period.replace('_', ' ').capitalize()}",
        active_period=period,
        total_ingresos=total_ingresos,
        total_pedidos=total_pedidos,
        promedio_por_pedido=promedio_por_pedido,
        pagination=pagination,
        # Restauro las variables que faltaban
        ranking_productos=ranking_productos,
        ventas_por_dia=ventas_por_dia,
        categorias_populares=categorias_populares,
        payment_methods_summary=payment_methods_summary,
        # Datos para los gráficos
        sales_by_day_labels=json.dumps(sales_by_day_labels),
        sales_by_day_data=json.dumps(sales_by_day_data),
        top_products_labels=json.dumps(top_products_labels),
        top_products_data=json.dumps(top_products_data)
    )

# ... (El resto de las funciones: sale_detail_view, annul_sale, manage_tables, etc., se mantienen igual que en la versión que ya tienes y funciona)
# ... Pega aquí el resto de tus funciones desde @admin_bp.route('/sale/detail/<int:order_id>') hasta el final del archivo.

@admin_bp.route('/sale/detail/<int:order_id>')
@admin_required
def sale_detail_view(order_id):
    order = Order.query.get_or_404(order_id)
    order.created_at = convert_to_local_time(order.created_at)
    order.updated_at = convert_to_local_time(order.updated_at)
    return_args = {key: val for key, val in request.args.items() if key != 'order_id'}
    
    return render_template('admin/sale_detail.html', 
                           sale_order=order, 
                           title=f"Detalle de Venta #{order.id}",
                           return_args=return_args)

@admin_bp.route('/annul_sale/<int:order_id>', methods=['POST'])
@admin_required
def annul_sale(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == OrderStatus.PAID:
        active_session = CashSession.query.filter_by(status='Abierta').first()
        if active_session and order.payment_method == 'Efectivo' and order.updated_at >= active_session.start_time:
            active_session.annulled_cash_sales = (active_session.annulled_cash_sales or 0.0) + order.total_amount

        order.status = OrderStatus.ANNULLED
        order.updated_at = get_current_time()
        for item in order.items:
            if item.product and not item.display_name:
                item.product.stock += item.quantity
        db.session.commit()
        flash(f'Venta #{order.id} anulada con éxito. El stock ha sido repuesto.', 'success')
    else:
        flash('Solo se pueden anular ventas con estado "Pagado".', 'danger')
    return_args = {key: val for key, val in request.form.items() if key not in ['order_id', 'csrf_token']}
    return redirect(url_for('admin.sales_and_reports', **return_args))
    
@admin_bp.route('/tables')
@mozo_required
def manage_tables():
    all_tables = Table.query.order_by(Table.number).all()
    return render_template('admin/manage_tables.html', 
                           tables=all_tables,
                           title="Gestionar Mesas")

@admin_bp.route('/tables/add', methods=['POST'])
@mozo_required
def add_table():
    number_str = request.form.get('number')
    capacity_str = request.form.get('capacity')

    if not number_str or not capacity_str:
        flash('El número y la capacidad de la mesa son obligatorios.', 'danger')
        return redirect(url_for('admin.manage_tables'))

    number = int(number_str)
    capacity = int(capacity_str)

    if Table.query.filter_by(number=number).first():
        flash(f'Ya existe una mesa con el número {number}.', 'danger')
    else:
        new_table = Table(number=number, capacity=capacity, status=TableStatus.EMPTY)
        db.session.add(new_table)
        db.session.commit()
        flash(f'Mesa {number} añadida con éxito.', 'success')

    return redirect(url_for('admin.manage_tables'))

@admin_bp.route('/tables/edit/<int:table_id>', methods=['POST'])
@mozo_required
def edit_table(table_id):
    table = Table.query.get_or_404(table_id)
    
    new_number_str = request.form.get('number')
    new_capacity_str = request.form.get('capacity')
    
    if not new_number_str or not new_capacity_str:
        flash('El número y la capacidad no pueden estar vacíos.', 'danger')
        return redirect(url_for('admin.manage_tables'))

    new_number = int(new_number_str)
    new_capacity = int(new_capacity_str)
    
    existing_table = Table.query.filter(Table.number == new_number, Table.id != table_id).first()
    if existing_table:
        flash(f'Ya existe otra mesa con el número {new_number}.', 'danger')
    else:
        table.number = new_number
        table.capacity = new_capacity
        db.session.commit()
        flash(f'Mesa {table.number} actualizada con éxito.', 'success')
    
    return redirect(url_for('admin.manage_tables'))

@admin_bp.route('/tables/delete/<int:table_id>', methods=['POST'])
@mozo_required
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status != TableStatus.EMPTY:
        flash('No se puede eliminar una mesa que está ocupada. Libérela primero.', 'danger')
    else:
        Order.query.filter_by(table_id=table.id).update({'table_id': None})
        db.session.delete(table)
        db.session.commit()
        flash(f'Mesa {table.number} eliminada con éxito.', 'success')
    
    return redirect(url_for('admin.manage_tables'))
    
@admin_bp.route('/tables/clear_all_paid', methods=['POST'])
@mozo_required
def clear_all_paid_tables():
    tables_to_clear = Table.query.filter_by(status=TableStatus.PAID).all()
    
    if not tables_to_clear:
        flash('No hay mesas pagadas para liberar.', 'info')
    else:
        for table in tables_to_clear:
            table.status = TableStatus.EMPTY
        db.session.commit()
        flash(f'{len(tables_to_clear)} mesas han sido liberadas con éxito.', 'success')
        
    return redirect(url_for('admin.manage_tables'))

@admin_bp.route('/users')
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.id).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    return render_template('admin/manage_users.html', pagination=pagination, title="Gestionar Usuarios")

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        role = request.form.get('role')
        if not all([username, password, role]):
            flash('Todos los campos son obligatorios.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario añadido con éxito.', 'success')
            return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/user_form.html', action="Añadir", title="Añadir Usuario")

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        role = request.form.get('role')
        user.role = role
        if password:
            user.set_password(password)
        db.session.commit()
        flash(f'Usuario {user.username} actualizado con éxito.', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/user_form.html', action="Editar", user=user, title=f"Editar Usuario {user.username}")

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user = User.query.get_or_404(user_id)
    if user.role == UserRoles.ADMIN:
        admin_count = User.query.filter_by(role=UserRoles.ADMIN).count()
        if admin_count <= 1:
            flash('No se puede eliminar al único administrador del sistema.', 'danger')
            return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado con éxito.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/cash-drawer')
@admin_required
def cash_drawer():
    active_session = CashSession.query.filter_by(status='Abierta').first()
    
    page = request.args.get('page', 1, type=int)
    closed_sessions = CashSession.query.filter_by(status='Cerrada').order_by(CashSession.end_time.desc()).paginate(page=page, per_page=5, error_out=False)

    if active_session:
        active_session.start_time = convert_to_local_time(active_session.start_time)
    for session in closed_sessions.items:
        session.start_time = convert_to_local_time(session.start_time)
        if session.end_time:
            session.end_time = convert_to_local_time(session.end_time)
    return render_template('admin/cash_drawer.html', 
                           title="Caja Diaria", 
                           active_session=active_session,
                           closed_sessions=closed_sessions)

@admin_bp.route('/cash-drawer/open', methods=['POST'])
@admin_required
def open_cash_session():
    starting_cash_str = request.form.get('starting_cash')
    
    active_session = CashSession.query.filter_by(status='Abierta').first()
    if active_session:
        flash('Ya hay una sesión de caja abierta.', 'danger')
        return redirect(url_for('admin.cash_drawer'))

    try:
        starting_cash = float(starting_cash_str)
        if starting_cash < 0:
            raise ValueError()
    except (ValueError, TypeError):
        flash('El monto inicial debe ser un número válido y positivo.', 'danger')
        return redirect(url_for('admin.cash_drawer'))

    new_session = CashSession(
        starting_cash=starting_cash,
        user_id=current_user.id
    )
    db.session.add(new_session)
    db.session.commit()
    flash(f'Caja abierta con un fondo inicial de ${starting_cash:.2f}.', 'success')
    return redirect(url_for('admin.cash_drawer'))

@admin_bp.route('/cash-drawer/close/<int:session_id>', methods=['GET', 'POST'])
@admin_required
def close_cash_session(session_id):
    session = CashSession.query.get_or_404(session_id)
    if session.status != 'Abierta':
        flash('Esta sesión ya ha sido cerrada.', 'warning')
        return redirect(url_for('admin.cash_drawer'))

    sales = db.session.query(
        Order.payment_method,
        func.sum(Order.total_amount).label('total')
    ).filter(
        Order.status == OrderStatus.PAID,
        Order.updated_at >= session.start_time
    ).group_by(Order.payment_method).all()

    session.cash_sales = sum(s.total for s in sales if s.payment_method == 'Efectivo') or 0.0
    session.card_sales = sum(s.total for s in sales if s.payment_method == 'Tarjeta') or 0.0
    session.transfer_sales = sum(s.total for s in sales if s.payment_method == 'Transferencia') or 0.0
    session.total_sales = sum(s.total for s in sales) or 0.0
    
    session.expected_cash = session.starting_cash + session.cash_sales - (session.annulled_cash_sales or 0.0)

    if request.method == 'POST':
        counted_cash_str = request.form.get('counted_cash')
        notes = request.form.get('notes')
        try:
            counted_cash = float(counted_cash_str)
            if counted_cash < 0:
                raise ValueError()
        except (ValueError, TypeError):
            flash('El monto contado debe ser un número válido y positivo.', 'danger')
            return render_template('admin/close_cash_session.html', title="Cerrar Caja", session=session)
        
        session.counted_cash = counted_cash
        session.difference = counted_cash - session.expected_cash
        session.end_time = get_current_time()
        session.status = 'Cerrada'
        session.notes = notes
        
        db.session.commit()
        flash('Caja cerrada con éxito.', 'success')
        return redirect(url_for('admin.cash_drawer'))

    return render_template('admin/close_cash_session.html', title="Cerrar Caja", session=session)

@admin_bp.route('/export-stats')
@admin_required
def export_stats():
    period = request.args.get('period', 'today')
    
    latest_sale = Order.query.order_by(Order.updated_at.desc()).first()
    reference_date = latest_sale.updated_at.date() if latest_sale else date.today()
    
    if period == 'today':
        start_date = datetime.combine(reference_date, datetime.min.time())
        end_date = datetime.combine(reference_date, datetime.max.time())
        period_title = f"Hoy ({reference_date.strftime('%d-%m-%Y')})"
    elif period == 'week':
        start_of_week = reference_date - timedelta(days=reference_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_date = datetime.combine(start_of_week, datetime.min.time())
        end_date = datetime.combine(end_of_week, datetime.max.time())
        period_title = f"Semana del {start_of_week.strftime('%d-%m-%Y')} al {end_of_week.strftime('%d-%m-%Y')}"
    elif period == 'month':
        start_of_month = reference_date.replace(day=1)
        next_month = start_of_month.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)
        start_date = datetime.combine(start_of_month, datetime.min.time())
        end_date = datetime.combine(last_day_of_month, datetime.max.time())
        period_title = f"Mes de {start_of_month.strftime('%B %Y')}"
    else:
        start_of_year = reference_date.replace(day=1, month=1)
        end_of_year = reference_date.replace(day=31, month=12)
        start_date = datetime.combine(start_of_year, datetime.min.time())
        end_date = datetime.combine(end_of_year, datetime.max.time())
        period_title = f"Año {start_of_year.year}"

    base_paid_query = Order.query.filter(Order.status == OrderStatus.PAID, Order.updated_at >= start_date, Order.updated_at <= end_date)
    total_ingresos = base_paid_query.with_entities(func.sum(Order.total_amount)).scalar() or 0.0
    total_pedidos = base_paid_query.count()
    promedio_por_pedido = total_ingresos / total_pedidos if total_pedidos > 0 else 0.0
    payment_methods_summary = base_paid_query.with_entities(Order.payment_method, func.count(Order.id), func.sum(Order.total_amount)).filter(Order.payment_method.isnot(None)).group_by(Order.payment_method).all()

    report_content = []
    report_content.append("="*40)
    report_content.append(" ESTADÍSTICAS DE VENTA - BAR DON ENRIQUE")
    report_content.append(f" Período: {period_title}")
    report_content.append("="*40)
    report_content.append(f"Ingresos Totales:      {total_ingresos:.2f}")
    report_content.append(f"Pedidos Cobrados:      {total_pedidos}")
    report_content.append(f"Promedio por Pedido:   {promedio_por_pedido:.2f}")
    report_content.append("-"*40)
    report_content.append("Desglose por Método de Pago:")
    for method, count, total in payment_methods_summary:
        report_content.append(f"  - {method}: {count} pedidos, total {total:.2f}")
    report_content.append("="*40)

    filename = f"estadisticas_{period}_{reference_date.strftime('%Y%m%d')}.txt"
    return Response(
        "\n".join(report_content),
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@admin_bp.route('/tables/bulk_action', methods=['POST'])
@mozo_required
def bulk_action_tables():
    action = request.form.get('action')
    table_ids = request.form.getlist('table_ids')

    if not action or not table_ids:
        flash('No se seleccionó ninguna acción o ninguna mesa.', 'warning')
        return redirect(url_for('mozo.tables_view'))

    table_ids = [int(id) for id in table_ids]
    
    liberated_count = 0
    canceled_count = 0

    if action == 'liberate':
        tables_to_liberate = Table.query.filter(Table.id.in_(table_ids), Table.status == TableStatus.PAID).all()
        for table in tables_to_liberate:
            table.status = TableStatus.EMPTY
            liberated_count += 1
            socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status.value})
        if liberated_count > 0:
            flash(f'{liberated_count} mesas han sido liberadas.', 'success')
        else:
            flash('Ninguna de las mesas seleccionadas estaba en estado "Pagada" para ser liberada.', 'info')

    elif action == 'cancel':
        orders_to_cancel = Order.query.filter(Order.table_id.in_(table_ids), Order.status == OrderStatus.ACTIVE).all()
        for order in orders_to_cancel:
            table_id = order.table_id
            for item in order.items:
                if item.product and not item.display_name:
                    item.product.stock += item.quantity
            
            if order.table_assigned:
                order.table_assigned.status = TableStatus.EMPTY
            
            db.session.delete(order)
            canceled_count += 1
            socketio.emit('table_status_update', {'table_id': table_id, 'status': TableStatus.EMPTY.value})
        if canceled_count > 0:
            flash(f'Se cancelaron los pedidos de {canceled_count} mesas y se restauró el stock.', 'success')
        else:
            flash('Ninguna de las mesas seleccionadas tenía un pedido activo para cancelar.', 'info')
            
    db.session.commit()
    return redirect(url_for('mozo.tables_view'))

@admin_bp.route('/bulk_pay_tables', methods=['POST'])
@mozo_required
def bulk_pay_tables():
    data = request.get_json()
    table_ids = data.get('table_ids', [])
    payment_method = data.get('payment_method')
    if not table_ids or not payment_method:
        return jsonify({'success': False, 'message': 'Faltan datos para procesar el cobro.'}), 400
    try:
        mesas_cobradas = 0
        for table_id in table_ids:
            table = Table.query.get(table_id)
            if not table or table.status != TableStatus.OCCUPIED:
                continue
            order = Order.query.filter_by(table_id=table.id, status=OrderStatus.ACTIVE).first()
            if not order:
                continue
            order.status = OrderStatus.PAID
            order.payment_method = payment_method
            table.status = TableStatus.PAID
            db.session.add(order)
            db.session.add(table)
            mesas_cobradas += 1
            socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status.value})
        db.session.commit()
        return jsonify({'success': True, 'message': f'{mesas_cobradas} mesas cobradas correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al cobrar las mesas: {str(e)}'}), 500

@admin_bp.route('/tables/bulk_action', methods=['POST'])
@mozo_required
def bulk_action_tables():
    action = request.form.get('action')
    table_ids = request.form.getlist('table_ids')

    if not action or not table_ids:
        flash('No se seleccionó ninguna acción o ninguna mesa.', 'warning')
        return redirect(url_for('mozo.tables_view'))

    table_ids = [int(id) for id in table_ids]
    
    liberated_count = 0
    canceled_count = 0

    if action == 'liberate':
        tables_to_liberate = Table.query.filter(Table.id.in_(table_ids), Table.status == TableStatus.PAID).all()
        for table in tables_to_liberate:
            table.status = TableStatus.EMPTY
            liberated_count += 1
            # Corrección: Se quitó .value
            socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status})
        if liberated_count > 0:
            flash(f'{liberated_count} mesas han sido liberadas.', 'success')
        else:
            flash('Ninguna de las mesas seleccionadas estaba en estado "Pagada" para ser liberada.', 'info')

    elif action == 'cancel':
        orders_to_cancel = Order.query.filter(Order.table_id.in_(table_ids), Order.status == OrderStatus.ACTIVE).all()
        for order in orders_to_cancel:
            table_id_to_update = order.table_id
            for item in order.items:
                if item.product and not item.display_name:
                    item.product.stock += item.quantity
            
            if order.table_assigned:
                order.table_assigned.status = TableStatus.EMPTY
            
            db.session.delete(order)
            canceled_count += 1
            # Corrección: Se quitó .value y se usó el estado correcto
            socketio.emit('table_status_update', {'table_id': table_id_to_update, 'status': TableStatus.EMPTY})
        if canceled_count > 0:
            flash(f'Se cancelaron los pedidos de {canceled_count} mesas y se restauró el stock.', 'success')
        else:
            flash('Ninguna de las mesas seleccionadas tenía un pedido activo para cancelar.', 'info')
            
    db.session.commit()
    return redirect(url_for('mozo.tables_view'))

@admin_bp.route('/bulk_pay_tables', methods=['POST'])
@mozo_required
def bulk_pay_tables():
    data = request.get_json()
    table_ids = data.get('table_ids', [])
    payment_method = data.get('payment_method')
    
    if not table_ids or not payment_method:
        return jsonify({'success': False, 'message': 'Faltan datos para procesar el cobro.'}), 400
    
    try:
        mesas_cobradas = 0
        for table_id in table_ids:
            table = Table.query.get(table_id)
            if not table or table.status != TableStatus.OCCUPIED:
                continue
            
            order = Order.query.filter_by(table_id=table.id, status=OrderStatus.ACTIVE).first()
            if not order or not order.items:
                continue
            
            order.status = OrderStatus.PAID
            order.payment_method = payment_method
            order.updated_at = datetime.utcnow()
            table.status = TableStatus.PAID
            
            db.session.add(order)
            db.session.add(table)
            
            # Corrección: Se quitó .value
            socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status})
            mesas_cobradas += 1
            
        db.session.commit()
        return jsonify({'success': True, 'message': f'{mesas_cobradas} mesa(s) cobrada(s) correctamente.'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cobrar mesas en lote: {str(e)}")
        return jsonify({'success': False, 'message': 'Ocurrió un error en el servidor.'}), 500