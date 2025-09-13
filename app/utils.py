# Archivo: app/utils.py
from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash
from datetime import datetime
import pytz

def get_current_time():
    """Retorna la hora actual con la zona horaria de Argentina."""
    return datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

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