# Archivo: app/__init__.py
import os
from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime
import click

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

DB_NAME = "bar_app.db"

def create_app():
    app = Flask(__name__, 
                instance_relative_config=True, 
                static_folder='static', 
                template_folder='templates')
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una-llave-secreta-muy-dificil-de-adivinar')
    
    # Crear el directorio de instancia si no existe
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, DB_NAME)}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'

    @app.context_processor
    def utility_processor():
        def get_csrf_token():
            return generate_csrf()
        return dict(csrf_token=get_csrf_token)

    from .auth import auth_bp
    from .admin import admin_bp
    from .mozo import mozo_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(mozo_bp, url_prefix='/mozo')
    
    # --- LÍNEA CORREGIDA ---
    # Ahora importamos 'OrderItem' junto con los otros modelos.
    from .models import User, Product, Table, Order, OrderItem

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.cli.command("seed-db")
    def seed_db_command():
        """Crea los datos iniciales para la base de datos."""
        with app.app_context():
            # Limpiar datos existentes de productos y usuarios para un reinicio limpio
            OrderItem.query.delete()
            Order.query.delete()
            Product.query.delete()
            User.query.delete()
            Table.query.delete()
            db.session.commit()

            print("Tablas limpiadas. Creando nuevos datos...")
            
            # Crear usuarios
            admin = User(username="admin", role='admin')
            admin.set_password("admin123")
            mozo = User(username="mozo", role='mozo')
            mozo.set_password("mozo123")
            db.session.add_all([admin, mozo])
            print("-> Usuarios 'admin' y 'mozo' creados.")

            # --- NUEVA LISTA DE PRODUCTOS ---
            products_to_add = [
                # Sandwiches
                Product(name="Milanesa Común", type="Sandwiches", price=5300.00, stock=100),
                Product(name="Lomo Común", type="Sandwiches", price=6500.00, stock=100),
                Product(name="Lomo Cheddar", type="Sandwiches", price=6500.00, stock=100),
                Product(name="Ternera en sanguchero", type="Sandwiches", price=6500.00, stock=100),
                # Hamburguesas
                Product(name="Hamburguesa Simple", type="Hamburguesas", price=4800.00, stock=100),
                Product(name="Hamburguesa Especial", type="Hamburguesas", price=5400.00, stock=100),
                Product(name="Hamburguesa Roque", type="Hamburguesas", price=6400.00, stock=100),
                Product(name="Hamburguesa Pecaj", type="Hamburguesas", price=5400.00, stock=100),
                Product(name="Especial Don Enrique (Hamb.)", type="Hamburguesas", price=6200.00, stock=100),
                # Pizzas
                Product(name="Muzzarella", type="Pizzas", price=7000.00, stock=100),
                Product(name="Jamón y Morrones", type="Pizzas", price=8000.00, stock=100),
                Product(name="Napolitana", type="Pizzas", price=8000.00, stock=100),
                Product(name="Fugazzetta", type="Pizzas", price=8000.00, stock=100),
                Product(name="Calabresa", type="Pizzas", price=8000.00, stock=100),
                Product(name="Roquefort (Pizza)", type="Pizzas", price=8000.00, stock=100),
                Product(name="Choclo (Pizza)", type="Pizzas", price=8500.00, stock=100),
                Product(name="Ternera (Pizza)", type="Pizzas", price=10500.00, stock=100),
                Product(name="Especial Don Enrique (Pizza)", type="Pizzas", price=10500.00, stock=100),
                # Napolitanas
                Product(name="Napo para 1 persona", type="Napolitanas", price=7600.00, stock=100),
                Product(name="Napo para 2 personas", type="Napolitanas", price=11800.00, stock=100),
                Product(name="Napo Al roquefort", type="Napolitanas", price=7600.00, stock=100),
                Product(name="Napo a la fugazzeta", type="Napolitanas", price=7600.00, stock=100),
                # Tostados
                Product(name="Tostado Jamón y Queso", type="Tostados", price=4800.00, stock=100),
                Product(name="Tostado Ternera y Queso", type="Tostados", price=5700.00, stock=100),
                Product(name="Tostado Ternera verdura y queso", type="Tostados", price=6000.00, stock=100),
                Product(name="1/2 Mexicano", type="Tostados", price=9000.00, stock=100),
                # Agregados
                Product(name="Agregado Jamón", type="Agregados", price=800.00, stock=999),
                Product(name="Agregado Huevo", type="Agregados", price=800.00, stock=999),
                Product(name="Agregado Panceta", type="Agregados", price=800.00, stock=999),
                Product(name="Agregado Roque o cheddar", type="Agregados", price=800.00, stock=999),
                Product(name="Agregado Cebolla", type="Agregados", price=600.00, stock=999),
                Product(name="Agregado Papas", type="Agregados", price=1400.00, stock=999),
                Product(name="Agregado Hamburguesa", type="Agregados", price=1800.00, stock=999),
                # Papas
                Product(name="Papas Fritas", type="Papas", price=3200.00, stock=100),
                Product(name="Papas Gratinadas Cheddar o tybo", type="Papas", price=4000.00, stock=100),
                Product(name="Papas Don Enrique", type="Papas", price=4600.00, stock=100),
                Product(name="Papas Fritas (Porción)", type="Papas", price=3200.00, stock=100),
                Product(name="Papas Fritas (Para 2)", type="Papas", price=4000.00, stock=100),
                # Bebidas c/Alcohol
                Product(name="Quilmes / Salta 1lt", type="Bebidas c/Alcohol", price=4800.00, stock=100),
                Product(name="Imperial 1lt", type="Bebidas c/Alcohol", price=5000.00, stock=100),
                Product(name="Norte 1lt", type="Bebidas c/Alcohol", price=4500.00, stock=100),
                Product(name="Quilmes, Salta, Imperial lata", type="Bebidas c/Alcohol", price=2800.00, stock=100),
                Product(name="Smirnoff sabor - lata", type="Bebidas c/Alcohol", price=2900.00, stock=100),
                Product(name="Vino tinto 3/4", type="Bebidas c/Alcohol", price=4700.00, stock=100),
                # Bebidas s/Alcohol
                Product(name="Linea pepsi 2lt", type="Bebidas s/Alcohol", price=3800.00, stock=100),
                Product(name="Linea coca lata", type="Bebidas s/Alcohol", price=4000.00, stock=100),
                Product(name="Linea pepsi lata", type="Bebidas s/Alcohol", price=2500.00, stock=100),
                Product(name="Agua Mineral 1.5lt", type="Bebidas s/Alcohol", price=3200.00, stock=100),
                Product(name="Agua Mineral 500 ml", type="Bebidas s/Alcohol", price=2500.00, stock=100),
                Product(name="Agua saborizada 1.5lt", type="Bebidas s/Alcohol", price=3200.00, stock=100),
            ]
            db.session.add_all(products_to_add)
            print(f"-> {len(products_to_add)} productos nuevos creados.")

            # Crear mesas
            tables_to_add = [ Table(number=i, capacity=4 if i % 2 == 0 else 2, status='Vacía') for i in range(1, 11) ]
            db.session.add_all(tables_to_add)
            print(f"-> {len(tables_to_add)} mesas creadas.")
            
            db.session.commit()
            print("\n¡Base de datos inicializada con éxito!")
            print("Credenciales por defecto:")
            print("  Admin: admin / admin123")
            print("  Mozo:  mozo / mozo123\n")
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('mozo.tables_view'))
        return redirect(url_for('auth.login'))
        
    return app