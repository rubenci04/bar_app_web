# Archivo: app/models.py
from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .utils import get_current_time

# --- CONSTANTES DE ESTADOS Y ROLES ---
class UserRoles:
    ADMIN = 'admin'
    MOZO = 'mozo'

class TableStatus:
    EMPTY = 'Vacía'
    OCCUPIED = 'Ocupada'
    PAID = 'Pagada'

class OrderStatus:
    PENDING = 'Pendiente'
    ACTIVE = 'Activo'
    PAID = 'Pagado'
    CANCELED = 'Cancelado'
    ANNULLED = 'Venta Anulada'
# --- FIN DE CONSTANTES ---

# --- CONSTANTES DE ESTADOS Y ROLES ---
class UserRoles:
    ADMIN = 'admin'
    MOZO = 'mozo'

class TableStatus:
    EMPTY = 'Vacía'
    OCCUPIED = 'Ocupada'
    PAID = 'Pagada'

class OrderStatus:
    PENDING = 'Pendiente'
    ACTIVE = 'Activo'
    PAID = 'Pagado'
    CANCELED = 'Cancelado'
    ANNULLED = 'Venta Anulada'
# --- FIN DE CONSTANTES ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRoles.MOZO)
    # --- RELACIÓN AÑADIDA ---
    cash_sessions = db.relationship('CashSession', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<Product {self.name}>'

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default=TableStatus.EMPTY) # Vacía, Ocupada, Pagada
    orders = db.relationship('Order', back_populates='table_assigned', lazy='dynamic')

    def __repr__(self):
        return f'<Table {self.number}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False) # Mesa, Para Llevar
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PENDING) # Pendiente, Activo, Pagado, Cancelado, Venta Anulada
    customer_name = db.Column(db.String(100), nullable=True)
    total_amount = db.Column(db.Float, nullable=True, default=0.0)
    payment_method = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=True)
    
    table_assigned = db.relationship('Table', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade="all, delete-orphan")

    def calculate_total(self):
        self.total_amount = sum(item.subtotal for item in self.items if item.subtotal is not None)

    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product')

    def __init__(self, **kwargs):
        super(OrderItem, self).__init__(**kwargs)
        self.calculate_subtotal()

    def calculate_subtotal(self):
        self.subtotal = self.quantity * self.unit_price

    def __repr__(self):
        return f'<OrderItem {self.id}>'

# --- MODELO PARA EL CIERRE DE CAJA ACTUALIZADO ---
class CashSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
<<<<<<< Updated upstream
    start_time = db.Column(db.DateTime, default=get_current_time)
=======
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
>>>>>>> Stashed changes
    end_time = db.Column(db.DateTime, nullable=True)
    starting_cash = db.Column(db.Float, nullable=False)
    counted_cash = db.Column(db.Float, nullable=True) # El dinero físico contado al final
    
    # Valores calculados por el sistema al momento del cierre
    cash_sales = db.Column(db.Float, nullable=True)
    card_sales = db.Column(db.Float, nullable=True)
    transfer_sales = db.Column(db.Float, nullable=True)
    total_sales = db.Column(db.Float, nullable=True)
    
    # --- CAMPO NUEVO ---
    annulled_cash_sales = db.Column(db.Float, default=0.0)

    expected_cash = db.Column(db.Float, nullable=True) # starting_cash + cash_sales - annulled_cash_sales
    difference = db.Column(db.Float, nullable=True) # counted_cash - expected_cash
    
    status = db.Column(db.String(20), nullable=False, default='Abierta') # Abierta, Cerrada
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<CashSession {self.id} - {self.status}>'