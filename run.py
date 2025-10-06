# run.py (CORREGIDO Y FINAL)

import eventlet
eventlet.monkey_patch()  # <-- ESTA LÍNEA ES LA SOLUCIÓN. Debe estar al principio.

import os
from app import create_app

app, socketio = create_app()

if __name__ == '__main__':
    # Esta sección es principalmente para pruebas locales. Gunicorn la ignora en producción.
    debug = not os.environ.get('RENDER', False)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)