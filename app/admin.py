# Archivo: app/admin.py (Versión Final con Reportes Avanzados)
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app, make_response, jsonify
from . import db, cache, socketio
from .models import Product, Order, OrderItem, Table, User, CashSession, OrderStatus, TableStatus, UserRoles
from .utils import admin_required, mozo_required, get_current_time, convert_to_local_time, retry_on_db_error
# [Yo]: Agregué 'time' aquí, es necesario para los filtros de fecha avanzados
from datetime import datetime, date, timedelta, time
from sqlalchemy import func
from flask_login import current_user
from werkzeug.datastructures import ImmutableMultiDict
from .exceptions import ConnectionError, ValidationError, TransactionError

admin_bp = Blueprint('admin', __name__)

ITEMS_PER_PAGE = 15  # [Yo]: Aumenté esto a 15 para que veas más registros por página

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

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    
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

# [Yo]: ESTA ES LA FUNCIÓN ACTUALIZADA CON TODOS LOS FILTROS Y NUEVAS MÉTRICAS
@admin_bp.route('/sales-reports')
@mozo_required
def sales_and_reports():
    page = request.args.get('page', 1, type=int)
    
    # Filtros de Fecha
    period = request.args.get('period', 'today')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    now = get_current_time()
    start_date, end_date = None, None
    is_custom_range = False

    # Lógica de Filtros
    if start_date_str and end_date_str:
        # Filtro Personalizado
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            period = 'custom'
            is_custom_range = True
        except ValueError:
            flash('Formato de fecha inválido.', 'danger')
            return redirect(url_for('admin.sales_and_reports'))
    else:
        # Filtros Predefinidos
        reference_date = now.date()
        if period == 'today':
            start_date = datetime.combine(reference_date, time.min)
            end_date = datetime.combine(reference_date, time.max)
        elif period == 'week':
            start_of_week = reference_date - timedelta(days=reference_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = datetime.combine(start_of_week, time.min)
            end_date = datetime.combine(end_of_week, time.max)
        elif period == 'month':
            start_of_month = reference_date.replace(day=1)
            # Truco para fin de mes
            next_month = start_of_month.replace(day=28) + timedelta(days=4)
            end_of_month = next_month - timedelta(days=next_month.day)
            start_date = datetime.combine(start_of_month, time.min)
            end_date = datetime.combine(end_of_month, time.max)
        elif period == 'year':
            start_of_year = reference_date.replace(day=1, month=1)
            end_of_year = reference_date.replace(day=31, month=12)
            start_date = datetime.combine(start_of_year, time.min)
            end_date = datetime.combine(end_of_year, time.max)
        else: # Default a hoy si algo falla
            start_date = datetime.combine(reference_date, time.min)
            end_date = datetime.combine(reference_date, time.max)

    # Consulta Base (Solo pagados para estadísticas)
    stats_query = Order.query.filter(Order.status == OrderStatus.PAID, Order.updated_at.between(start_date, end_date))
    
    # 1. KPIs Generales
    total_ingresos = stats_query.with_entities(func.sum(Order.total_amount)).scalar() or 0.0
    total_pedidos = stats_query.count()
    promedio_por_pedido = total_ingresos / total_pedidos if total_pedidos > 0 else 0.0

    # 2. Ventas por Día (Gráfico de Línea)
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

    # 3. Ranking Productos y Categorías
    # Optimizamos trayendo solo los IDs de las ordenes filtradas
    order_ids_subquery = stats_query.with_entities(Order.id)
    
    base_items_query = OrderItem.query.filter(OrderItem.order_id.in_(order_ids_subquery))
    
    # Top Productos
    ranking_productos = base_items_query.join(Product).with_entities(
        Product.name, func.sum(OrderItem.quantity).label('total_quantity')
    ).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    top_products_labels = [p.name for p in ranking_productos]
    top_products_data = [p.total_quantity for p in ranking_productos]
    
    # Top Categorías (Para gráfico de torta)
    categorias_populares = base_items_query.join(Product).with_entities(
        Product.type,
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).group_by(Product.type).order_by(func.sum(OrderItem.subtotal).desc()).all()
    
    cat_labels = [c.type for c in categorias_populares]
    cat_data = [c.total_revenue for c in categorias_populares]

    # 4. NUEVA MÉTRICA: Ventas por Hora (Horas Pico)
    # Lo hacemos en Python para compatibilidad universal (SQLite/Postgres)
    orders_data = stats_query.with_entities(Order.updated_at, Order.total_amount).all()
    hours_data = {h: 0 for h in range(24)} # Inicializar horas 0-23
    for o_date, o_amount in orders_data:
        local_dt = convert_to_local_time(o_date)
        if local_dt:
            hours_data[local_dt.hour] += o_amount
    
    # Filtramos solo horas con ventas para el gráfico
    busy_hours_labels = [f"{h}:00" for h in range(24) if hours_data[h] > 0]
    busy_hours_data = [hours_data[h] for h in range(24) if hours_data[h] > 0]

    # 5. NUEVA MÉTRICA: Rendimiento por Mesa
    top_tables = stats_query.join(Table).filter(Order.type == 'Mesa').with_entities(
        Table.number,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('total')
    ).group_by(Table.number).order_by(func.sum(Order.total_amount).desc()).limit(8).all()

    # 6. Resumen Métodos de Pago
    payment_methods_summary = stats_query.with_entities(
        Order.payment_method,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('total')
    ).filter(Order.payment_method.isnot(None)).group_by(Order.payment_method).order_by(func.count(Order.id).desc()).all()

    # Tabla Detallada (Logs)
    log_query = Order.query.filter(
        Order.status.in_([OrderStatus.PAID, OrderStatus.ANNULLED]), 
        Order.updated_at.between(start_date, end_date)
    ).order_by(Order.updated_at.desc())
    
    pagination = log_query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    return render_template('admin/sales_and_reports.html', 
        title="Ventas y Reportes",
        subtitle=f"({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})",
        active_period=period,
        is_custom_range=is_custom_range,
        start_date_val=start_date_str,
        end_date_val=end_date_str,
        
        total_ingresos=total_ingresos,
        total_pedidos=total_pedidos,
        promedio_por_pedido=promedio_por_pedido,
        
        pagination=pagination,
        
        # Datos para Gráficos
        sales_by_day_labels=json.dumps(sales_by_day_labels),
        sales_by_day_data=json.dumps(sales_by_day_data),
        top_products_labels=json.dumps(top_products_labels),
        top_products_data=json.dumps(top_products_data),
        cat_labels=json.dumps(cat_labels),
        cat_data=json.dumps(cat_data),
        busy_hours_labels=json.dumps(busy_hours_labels),
        busy_hours_data=json.dumps(busy_hours_data),
        
        # Datos para Tablas
        top_tables=top_tables,
        payment_methods_summary=payment_methods_summary
    )

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
            # ✅ CORRECCIÓN: Se elimina '.value'
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
            # ✅ CORRECCIÓN: Se elimina '.value' y se envía el estado correcto
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
            
            # ✅ CORRECCIÓN: Se elimina '.value'
            socketio.emit('table_status_update', {'table_id': table.id, 'status': table.status})
            mesas_cobradas += 1
            
        db.session.commit()
        return jsonify({'success': True, 'message': f'{mesas_cobradas} mesa(s) cobrada(s) correctamente.'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cobrar mesas en lote: {str(e)}")
        return jsonify({'success': False, 'message': 'Ocurrió un error en el servidor.'}), 500

# --- AGREGAR ESTO AL FINAL DE app/admin.py ---

@admin_bp.route('/actualizar-precios-ahora')
@admin_required
def update_prices_from_route():
    """
    Ruta especial para actualizar precios sin acceso a Shell.
    Solo accesible por administradores.
    """
    try:
        # 1. Definimos el Stock Masivo
        MASSIVE_STOCK = 100000
        
        # 2. La lista completa de precios del PDF
        menu_items = [
            # --- SANDWICHS ---
            {"name": "Milanesa Común", "type": "Sandwiches", "price": 7500, "description": "Sandwich de milanesa básico"},
            {"name": "Milanesa Especial", "type": "Sandwiches", "price": 8500, "description": "Jamón, queso y papas fritas"},
            {"name": "Lomo Común", "type": "Sandwiches", "price": 8500, "description": "Sandwich de lomo básico"},
            {"name": "Lomo Cheddar", "type": "Sandwiches", "price": 8500, "description": "Lomo con queso cheddar"},
            {"name": "Lomo Especial", "type": "Sandwiches", "price": 9500, "description": "Jamón, queso, lechuga, tomate, huevo. C/Papas"},
            {"name": "Miga Jamón y Queso", "type": "Sandwiches", "price": 6500, "description": "Plancha entera"},
            {"name": "Miga Ternera y Queso", "type": "Sandwiches", "price": 8500, "description": "Plancha entera"},
            {"name": "Mexicano (1/2 para 2 pers)", "type": "Sandwiches", "price": 14000, "description": "Jamón, queso, lechuga, tomate, lomo, cubierta queso, huevo c/papas"},
            {"name": "Ternera en Sanguchero", "type": "Sandwiches", "price": 8500, "description": "Ternera, queso, lechuga y tomate"},

            # --- BURGERS ---
            {"name": "Hamburguesa Simple", "type": "Hamburguesas", "price": 6000, "description": "Cheddar, lechuga, tomate, salsa bbq. C/ papas fritas"},
            {"name": "Hamburguesa Especial", "type": "Hamburguesas", "price": 6500, "description": "Cheddar, lechuga, tomate, huevo, jamón, salsa bbq. C/ papas fritas"},
            {"name": "Hamburguesa Roque", "type": "Hamburguesas", "price": 6500, "description": "Tybo, cebolla, lechuga, tomate, roquefort, salsa bbq. C/ papas fritas"},
            {"name": "Hamburguesa Pecal", "type": "Hamburguesas", "price": 6500, "description": "Cheddar, aros de cebolla, huevo, panceta y salsa bbq. C/ papas fritas"},
            {"name": "Especial Don Enrique Burger", "type": "Hamburguesas", "price": 7500, "description": "Doble Hamburguesa, cheddar, huevo, panceta, cebolla caramelizada y salsa bbq. C/ papas fritas"},

            # --- PAPAS ---
            {"name": "Papas Fritas", "type": "Papas", "price": 3500, "description": "Porción clásica"},
            {"name": "Papas Gratinadas", "type": "Papas", "price": 5000, "description": "Con Cheddar o queso cremoso"},
            {"name": "Papas Don Enrique", "type": "Papas", "price": 6000, "description": "Papas grandes con cheddar, panceta y verdeo"},

            # --- AGREGADOS ---
            {"name": "Agregado Jamón", "type": "Agregados", "price": 1500, "description": "Porción extra"},
            {"name": "Agregado Huevo", "type": "Agregados", "price": 1000, "description": "Unidad extra"},
            {"name": "Agregado Panceta", "type": "Agregados", "price": 1500, "description": "Porción extra"},
            {"name": "Agregado Roque o Cheddar", "type": "Agregados", "price": 1500, "description": "Porción extra"},
            {"name": "Agregado Cebolla", "type": "Agregados", "price": 1000, "description": "Porción extra"},
            {"name": "Agregado Papas", "type": "Agregados", "price": 1500, "description": "Porción extra"},
            {"name": "Agregado Hamburguesa", "type": "Agregados", "price": 2500, "description": "Medallón extra"},

            # --- PIZZAS ---
            {"name": "Pizza Muzzarela", "type": "Pizzas", "price": 8000, "description": "Salsa, muzzarela y aceitunas"},
            {"name": "Pizza Jamón y Morrones", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, jamón, morrones"},
            {"name": "Pizza Napolitana", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, rodajitas de tomate"},
            {"name": "Pizza Fugazzeta", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, cebollita salteada"},
            {"name": "Pizza Calabresa", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, rodajas de salamín"},
            {"name": "Pizza Roquefort", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, roquefort"},
            {"name": "Pizza Choclo", "type": "Pizzas", "price": 9500, "description": "Salsa, muzzarela, choclo, huevo, morrón"},
            {"name": "Pizza Ternera", "type": "Pizzas", "price": 12500, "description": "Salsa, muzzarela, ternera, huevo, morrón"},
            {"name": "Pizza Esp. Don Enrique", "type": "Pizzas", "price": 13000, "description": "Salsa, muzzarela, papas fritas, huevos fritos, panceta, verdeo"},
            {"name": "Recargo Pizza Mitad/Mitad", "type": "Otros", "price": 500, "description": "Costo operativo por combinación", "stock": MASSIVE_STOCK},

            # --- NAPOLITANAS (AL PLATO) ---
            {"name": "Mila Napo Clásica (1 pers)", "type": "Napolitanas", "price": 9000, "description": "Milanesa, salsa, queso, jamón. C/Fritas"},
            {"name": "Mila Napo Clásica (2 pers)", "type": "Napolitanas", "price": 15000, "description": "Milanesa, salsa, queso, jamón. C/Fritas (Para compartir)"},
            {"name": "Mila al Roquefort", "type": "Napolitanas", "price": 9000, "description": "Milanesa, salsa, queso cremoso y roquefort. C/Fritas"},
            {"name": "Mila a la Fugazzeta", "type": "Napolitanas", "price": 9000, "description": "Milanesa, queso, cebollita salteada y orégano. C/Fritas"},
            {"name": "Mila a la Americana", "type": "Napolitanas", "price": 9500, "description": "Milanesa, salsa, queso, panceta y huevo frito. C/Fritas"},

            # --- BEBIDAS S/ALCOHOL ---
            {"name": "Linea Pepsi 2lt", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Botella grande"},
            {"name": "Linea Coca 1lt", "type": "Bebidas s/Alcohol", "price": 4000, "description": "Botella mediana"},
            {"name": "Linea Pepsi lata", "type": "Bebidas s/Alcohol", "price": 2000, "description": "Lata"},
            {"name": "Pritty 1lt", "type": "Bebidas s/Alcohol", "price": 2500, "description": "Botella"},
            {"name": "Pritty 500ml", "type": "Bebidas s/Alcohol", "price": 1500, "description": "Botella chica"},
            {"name": "Agua Mineral 500ml", "type": "Bebidas s/Alcohol", "price": 2000, "description": "Botella chica"},
            {"name": "Agua Saborizada 1.5lt", "type": "Bebidas s/Alcohol", "price": 3000, "description": "Botella grande"},
            {"name": "Monster lata", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Energizante"},

            # --- BEBIDAS C/ALCOHOL ---
            {"name": "Quilmes / Salta 1lt", "type": "Bebidas c/Alcohol", "price": 5000, "description": "Cerveza Litro"},
            {"name": "Imperial 1lt", "type": "Bebidas c/Alcohol", "price": 5000, "description": "Cerveza Litro"},
            {"name": "Norte 1lt", "type": "Bebidas c/Alcohol", "price": 4500, "description": "Cerveza Litro"},
            {"name": "Quilmes lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
            {"name": "Salta lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
            {"name": "Imperial lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
            {"name": "Smirnoff lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Lata"},
            {"name": "Vino Tinto 3/4", "type": "Bebidas c/Alcohol", "price": 5500, "description": "Botella"},
        ]

        updated_count = 0
        created_count = 0

        # 3. Iteramos sobre los productos usando la sesión de base de datos activa
        for item_data in menu_items:
            product = Product.query.filter(Product.name.ilike(item_data['name'])).first()

            if product:
                product.price = item_data['price']
                product.type = item_data['type']
                product.description = item_data.get('description', '')
                product.stock = MASSIVE_STOCK
                updated_count += 1
            else:
                new_product = Product(
                    name=item_data['name'],
                    price=item_data['price'],
                    type=item_data['type'],
                    description=item_data.get('description', ''),
                    stock=MASSIVE_STOCK
                )
                db.session.add(new_product)
                created_count += 1

        db.session.commit()
        
        # Limpiamos el caché para que los cambios se vean al instante
        invalidate_product_cache()
        
        flash(f'¡Éxito! Precios actualizados. {updated_count} modificados, {created_count} nuevos.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar: {str(e)}', 'danger')

    return redirect(url_for('admin.products'))