# run.py (Versión de Emergencia para Arreglar DB)
import eventlet
eventlet.monkey_patch()  # [Yo]: Necesario para Gunicorn + Eventlet

import os
from app import create_app, db
from sqlalchemy import text

app, socketio = create_app()

def fix_database_schema():
    """
    [Yo]: Esta función verifica si falta la columna 'status' en 'order_item'
    y la agrega automáticamente si no existe. Es un salvavidas.
    """
    with app.app_context():
        try:
            # Verificamos si la columna ya existe
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='order_item' AND column_name='status';")
            result = db.session.execute(check_sql).fetchone()
            
            if not result:
                print("⚠️ ALERTA: La columna 'status' NO existe en order_item. Intentando agregarla...")
                # Agregamos la columna manualmente
                add_column_sql = text("ALTER TABLE order_item ADD COLUMN status VARCHAR(20) DEFAULT 'Pendiente';")
                db.session.execute(add_column_sql)
                db.session.commit()
                print("✅ ÉXITO: Columna 'status' agregada correctamente.")
            else:
                print("ℹ️ La columna 'status' ya existe. Todo en orden.")
        except Exception as e:
            print(f"❌ Error intentando arreglar la BD: {str(e)}")

# [Yo]: Ejecutamos la corrección ANTES de que arranque el servidor
if os.environ.get('RENDER'):
    fix_database_schema()

if __name__ == '__main__':
    # Esta sección es principalmente para pruebas locales. Gunicorn la ignora en producción.
    debug = not os.environ.get('RENDER', False)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)