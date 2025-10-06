# Archivo: app/__init__.py (Versión Corregida)
import os
from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime
import click
from flask_caching import Cache
from flask_socketio import SocketIO

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
cache = Cache()
socketio = SocketIO()

DB_NAME = "bar_app.db"

def create_app():
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    app.jinja_env.add_extension('jinja2.ext.do')

    from .utils import convert_to_local_time
    def localtime_filter(dt, fmt=None):
        return convert_to_local_time(dt, fmt)
    app.jinja_env.filters['localtime'] = localtime_filter

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una-clave-de-desarrollo-cualquiera')
    
    # Esta es la sección corregida. He eliminado los 'else' duplicados
    # y he unificado la lógica de configuración.
    if os.environ.get('RENDER'):
        # Configuración para producción (Render)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        cache_dir = os.path.join(app.instance_path, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        app.config['CACHE_TYPE'] = 'FileSystemCache'
        app.config['CACHE_DIR'] = cache_dir
        app.config['CACHE_DEFAULT_TIMEOUT'] = int(os.environ.get('CACHE_TIMEOUT', 300))
        app.config['CACHE_THRESHOLD'] = 1000
    else:
        # Configuración para desarrollo local
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, DB_NAME)}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['CACHE_TYPE'] = 'SimpleCache'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    os.makedirs(app.instance_path, exist_ok=True)

    # Inicializo todas las extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    socketio.init_app(app)

    from .db_utils import register_commands
    register_commands(app)

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

    from .models import User, Product, Table, Order, OrderItem, CashSession
    from . import events

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.cli.command("seed-db")
    def seed_db_command():
        """Crea los datos iniciales para la base de datos."""
        with app.app_context():
            OrderItem.query.delete()
            Order.query.delete()
            Product.query.delete()
            User.query.delete()
            Table.query.delete()
            CashSession.query.delete()
            db.session.commit()

            print("Tablas limpiadas. Creando nuevos datos...")
            
            admin = User(username="admin", role='admin')
            admin.set_password("admin123")
            mozo = User(username="mozo", role='mozo')
            mozo.set_password("mozo123")
            db.session.add_all([admin, mozo])
            print("-> Usuarios 'admin' y 'mozo' creados.")

            products_to_add = [
                Product(name="Milanesa Común", type="Sandwiches", price=6000.00, stock=100),
                Product(name="Milanesa Especial", type="Sandwiches", price=7500.00, stock=100, description="Jamón, queso y papas fritas"),
                Product(name="Lomo Común", type="Sandwiches", price=7500.00, stock=100),
                Product(name="Lomo Cheddar", type="Sandwiches", price=7500.00, stock=100),
                Product(name="Lomo Especial", type="Sandwiches", price=9000.00, stock=100, description="Jamón, queso y papas fritas"),
                Product(name="Ternera en sanguchero", type="Sandwiches", price=7500.00, stock=100),
                Product(name="Hamburguesa Simple", type="Hamburguesas", price=5000.00, stock=100, description="Hamburguesa, cheddar, lechuga, tomate, salsa bbq. C/ papas fritas."),
                Product(name="Hamburguesa Especial", type="Hamburguesas", price=5500.00, stock=100, description="Hamburguesa, cheddar, lechuga, tomate, huevo, jamon, salsa bbq. C/ papas fritas."),
                Product(name="Hamburguesa Roque", type="Hamburguesas", price=5500.00, stock=100, description="Hamburguesa, tybo, cebolla, lechuga, tomate, roquefort, salsa bbq. C/ papas fritas."),
                Product(name="Hamburguesa Peca", type="Hamburguesas", price=5500.00, stock=100, description="Hamburguesa, cheddar, aros de cebolla fritos, huevo, panceta y salsa bbq. C/ papas fritas."),
                Product(name="Especial Don Enrique (Hamb.)", type="Hamburguesas", price=6500.00, stock=100, description="Doble Hamburguesa, cheddar huevo, panceta, cebolla caramelizada y salsa bbq. C/ papas fritas."),
                Product(name="Muzzarella", type="Pizzas", price=7000.00, stock=100, description="Salsa, muzzarela y aceitunas"),
                Product(name="Jamón y Morrones", type="Pizzas", price=8000.00, stock=100, description="Salsa, muzzarela, jamón, morrones y aceitunas"),
                Product(name="Napolitana", type="Pizzas", price=8000.00, stock=100, description="Salsa, muzzarela, rodajitas de tomate, y aceitunas"),
                Product(name="Fugazzeta", type="Pizzas", price=8000.00, stock=100, description="Salsa, muzzarela, cebollita salteada y aceitunas"),
                Product(name="Calabresa", type="Pizzas", price=8000.00, stock=100, description="Salsa, muzzarela, rodajas de salamin y aceitunas"),
                Product(name="Roquefort (Pizza)", type="Pizzas", price=8000.00, stock=100, description="Salsa, muzzarela, roquefort y aceitunas"),
                Product(name="Choclo", type="Pizzas", price=8500.00, stock=100, description="Salsa, muzzarela, choclo, huevo, morrón y aceitunas"),
                Product(name="Ternera (Pizza)", type="Pizzas", price=10500.00, stock=100, description="Salsa, muzzarela, ternera, huevo, morron y aceitunas"),
                Product(name="Especial Don Enrique (Pizza)", type="Pizzas", price=10500.00, stock=100, description="Salsa, muzzarela, papas fritas, huevos fritos, panceta, cebollita de verdeo y aceitunas"),
                Product(name="Napo para 1 persona", type="Napolitanas", price=8000.00, stock=100),
                Product(name="Napo para 2 personas", type="Napolitanas", price=13500.00, stock=100),
                Product(name="Milanesa Al roquefort", type="Napolitanas", price=8000.00, stock=100, description="Milanesa, salsa, queso cremoso y queso roquefort. C/Fritas"),
                Product(name="Milanesa a la fugazzeta", type="Napolitanas", price=8000.00, stock=100, description="Milanesa, queso, cebollita salteada y oregano. C/Fritas"),
                Product(name="Milanesa a la Americana", type="Napolitanas", price=9000.00, stock=100, description="Milanesa, salsa, queso, panceta y huevo frito. C/Fritas"),
                Product(name="Tostado Jamón y Queso", type="Tostados", price=5500.00, stock=100),
                Product(name="Tostado Ternera y Queso", type="Tostados", price=6500.00, stock=100),
                Product(name="Tostado Ternera verdura y queso", type="Tostados", price=7500.00, stock=100),
                Product(name="1/2 Mexicano", type="Tostados", price=11000.00, stock=100, description="(Jamón, queso, lechuga, tomate, lomo, cubierta gratinada con queso, Huevo c/papas)"),
                Product(name="Agregado Jamón", type="Agregados", price=1000.00, stock=999),
                Product(name="Agregado Huevo", type="Agregados", price=1000.00, stock=999),
                Product(name="Agregado Panceta", type="Agregados", price=1000.00, stock=999),
                Product(name="Agregado Roque o cheddar", type="Agregados", price=1000.00, stock=999),
                Product(name="Agregado Cebolla", type="Agregados", price=500.00, stock=999),
                Product(name="Agregado Papas", type="Agregados", price=1500.00, stock=999),
                Product(name="Agregado Hamburguesa", type="Agregados", price=2000.00, stock=999),
                Product(name="Recargo Pizza Mitad/Mitad", type="Agregados", price=500.00, stock=999),
                Product(name="Papas Fritas", type="Papas", price=3500.00, stock=100),
                Product(name="Papas Gratinadas", type="Papas", price=4500.00, stock=100, description="Chedar/queso cremoso"),
                Product(name="Papas Don Enrique", type="Papas", price=5000.00, stock=100, description="Papas grandes con cheddar, panceta y verdeo"),
                Product(name="Quilmes / Salta 1lt", type="Bebidas c/Alcohol", price=4500.00, stock=100),
                Product(name="Imperial 1lt", type="Bebidas c/Alcohol", price=5000.00, stock=100),
                Product(name="Norte 1lt", type="Bebidas c/Alcohol", price=4500.00, stock=100),
                Product(name="Quilmes, Salta, Imperial lata", type="Bebidas c/Alcohol", price=3000.00, stock=100),
                Product(name="Smirnoff sabor - lata", type="Bebidas c/Alcohol", price=3000.00, stock=100),
                Product(name="Vino tinto 3/4", type="Bebidas c/Alcohol", price=5000.00, stock=100),
                Product(name="Linea pepsi 2lt", type="Bebidas s/Alcohol", price=3500.00, stock=100),
                Product(name="Linea coca 1lt", type="Bebidas s/Alcohol", price=4000.00, stock=100),
                Product(name="Linea pepsi lata", type="Bebidas s/Alcohol", price=2000.00, stock=100),
                Product(name="Agua Mineral 500 ml", type="Bebidas s/Alcohol", price=2000.00, stock=100),
                Product(name="Agua saborizada 1.5lt", type="Bebidas s/Alcohol", price=3000.00, stock=100),
            ]
            db.session.add_all(products_to_add)
            print(f"-> {len(products_to_add)} productos nuevos creados.")
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
        
    return app, socketio