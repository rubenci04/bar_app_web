# Archivo: app/__init__.py (Versión Corregida con WhiteNoise)
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
from whitenoise import WhiteNoise  # [Yo]: Importamos la librería mágica

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
    
    if os.environ.get('RENDER'):
        # Configuración para producción (Render)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # [Yo]: Configuración de WhiteNoise para servir estáticos en producción
        app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(app.root_path, 'static'), prefix='static/')
        
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
            # ... (El resto de tu función seed_db queda igual, lo omito para no hacer esto gigante)
            # Si necesitas que te copie también la función seed_db completa dímelo, 
            # pero con mantener lo que ya tenías ahí es suficiente.
            pass # (Tu lógica de seed-db aquí)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('mozo.tables_view'))
        return redirect(url_for('auth.login'))
        
    return app, socketio