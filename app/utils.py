# Archivo: app/utils.py (Versión Corregida)
from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash, current_app
from datetime import datetime, date
import pytz
from sqlalchemy.exc import OperationalError, IntegrityError, SQLAlchemyError
import time
from . import db
from .exceptions import ConnectionError, ValidationError, TransactionError

def get_current_time():
    """Retorna la hora actual en UTC."""
    return datetime.now(pytz.utc)

def convert_to_local_time(utc_dt, fmt=None):
    """Convierte un datetime UTC a la zona horaria local de Argentina y lo formatea si se pasa fmt."""
    if utc_dt is None:
        return '' if fmt else None
    
    if isinstance(utc_dt, str):
        try:
            utc_dt = datetime.strptime(utc_dt, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                utc_dt = datetime.strptime(utc_dt, '%Y-%m-%d').date()
            except ValueError:
                return utc_dt

    if isinstance(utc_dt, date) and not isinstance(utc_dt, datetime):
        if fmt:
            return utc_dt.strftime(fmt)
        return utc_dt

    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    local_dt = utc_dt.astimezone(local_tz)
    
    if fmt:
        return local_dt.strftime(fmt)
    
    return local_dt

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("No tienes permiso para acceder a esta página. Se requiere rol de administrador.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def mozo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'mozo']: 
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ✅ MEJORA: Nuevo decorador para el rol de Cocina
def cocina_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Permitimos el acceso a los roles 'cocina' y 'admin'
        if not current_user.is_authenticated or current_user.role not in ['admin', 'cocina']: 
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def retry_on_db_error(max_retries=3, initial_delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return f(*args, **kwargs)
                except OperationalError as e:
                    if retries >= max_retries:
                        current_app.logger.error(f"Error de operación de BD después de {max_retries} intentos: {str(e)}")
                        db.session.rollback()
                        raise ConnectionError(f"Error de conexión a la base de datos: {str(e)}")
                    retries += 1
                    time.sleep(delay)
                    delay *= 2
                except IntegrityError as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error de integridad en la BD: {str(e)}")
                    raise ValidationError(f"Error de validación en la base de datos: {str(e)}")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error de SQLAlchemy: {str(e)}")
                    raise TransactionError(f"Error en la transacción de base de datos: {str(e)}")
        return wrapper
    return decorator