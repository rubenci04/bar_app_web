# Archivo: app/utils.py
from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash
from datetime import datetime, date
import pytz

def get_current_time():
    """Retorna la hora actual en UTC."""
    return datetime.now(pytz.utc)

def convert_to_local_time(utc_dt, fmt=None):
    """Convierte un datetime UTC a la zona horaria local de Argentina y lo formatea si se pasa fmt."""
    if utc_dt is None:
        return '' if fmt else None
    
    # If it's a date object, just format it or return as is
    if isinstance(utc_dt, date) and not isinstance(utc_dt, datetime):
        if fmt:
            return utc_dt.strftime(fmt)
        return utc_dt

    # If it's a datetime object, proceed with timezone conversion
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