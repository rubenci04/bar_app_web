# Archivo: update_products.py (Versión Corregida para Stock Masivo)

import os
import sys

# Esta parte es importante para que el script sepa dónde encontrar tu aplicación y sus modelos.
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Product

def set_massive_stock():
    """
    Mi nueva función: busca TODOS los productos en la base de datos
    y establece su stock en 5,000,000.
    """
    # Creo una instancia de la aplicación para poder trabajar con la base de datos.
    app = create_app()
    with app.app_context():
        # Primero, obtengo todos los productos que existen actualmente.
        all_products = Product.query.all()
        
        if not all_products:
            print("No se encontraron productos en la base de datos. No se realizó ninguna acción.")
            return

        print(f"Se encontraron {len(all_products)} productos. Actualizando stock a 5,000,000...")

        # Recorro cada producto y actualizo su campo 'stock'.
        for product in all_products:
            product.stock = 5000000
        
        # Guardo todos los cambios en la base de datos de una sola vez.
        db.session.commit()
        
        print("-" * 30)
        print("¡Éxito! El stock de todos los productos ha sido actualizado.")
        print("-" * 30)

# Esta parte asegura que la función se ejecute solo cuando yo llame al script directamente.
if __name__ == "__main__":
    set_massive_stock()