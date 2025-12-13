# Archivo: update_products.py
import os
import sys

# [Yo]: Configuro la ruta del proyecto para que Python sepa dónde buscar 'app'.
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Product

def update_menu_from_pdf():
    """
    [Yo]: Esta función contiene la lógica principal. He volcado todos los datos
    del PDF 'Menu imprimible diciembre' en la lista 'menu_items'.
    El script recorrerá esta lista y actualizará o creará los productos en tu base de datos.
    """
    
    # [Yo]: Defino el stock masivo aquí para poder cambiarlo fácil en el futuro si hace falta.
    MASSIVE_STOCK = 100000

    # [Yo]: Aquí está el mapeo completo del PDF.
    menu_items = [
        # --- SANDWICHS ---
        {"name": "Milanesa Común", "type": "Sandwiches", "price": 7500, "description": "Sandwich de milanesa básico"},
        {"name": "Milanesa Especial", "type": "Sandwiches", "price": 8500, "description": "Jamón, queso y papas fritas"},
        {"name": "Lomo Común", "type": "Sandwiches", "price": 8500, "description": "Sandwich de lomo básico"},
        {"name": "Lomo Cheddar", "type": "Sandwiches", "price": 8500, "description": "Lomo con queso cheddar"},
        {"name": "Lomo Especial", "type": "Sandwiches", "price": 9500, "description": "Jamón, queso, lechuga, tomate, huevo. C/Papas"},
        {"name": "Miga Jamón y Queso", "type": "Sandwiches", "price": 6500, "description": "Plancha entera"},
        {"name": "Miga Ternera y Queso", "type": "Sandwiches", "price": 8500, "description": "Plancha entera"},
        {"name": "Mexicano (1/2 para 2 pers)", "type": "Sandwiches", "price": 14000, "description": "Jamón, queso, lechuga, tomate, lomo, cubierta queso, huevo c/papas"},
        {"name": "Ternera en Sanguchero", "type": "Sandwiches", "price": 8500, "description": "Ternera, queso, lechuga y tomate"},

        # --- BURGERS ---
        {"name": "Hamburguesa Simple", "type": "Hamburguesas", "price": 6000, "description": "Cheddar, lechuga, tomate, salsa bbq. C/ papas fritas"},
        {"name": "Hamburguesa Especial", "type": "Hamburguesas", "price": 6500, "description": "Cheddar, lechuga, tomate, huevo, jamón, salsa bbq. C/ papas fritas"},
        {"name": "Hamburguesa Roque", "type": "Hamburguesas", "price": 6500, "description": "Tybo, cebolla, lechuga, tomate, roquefort, salsa bbq. C/ papas fritas"},
        {"name": "Hamburguesa Pecadora", "type": "Hamburguesas", "price": 6500, "description": "Cheddar, aros de cebolla, huevo, panceta y salsa bbq. C/ papas fritas"},
        {"name": "Especial Don Enrique Burger", "type": "Hamburguesas", "price": 7500, "description": "Doble Hamburguesa, cheddar, huevo, panceta, cebolla caramelizada y salsa bbq. C/ papas fritas"},

        # --- PAPAS ---
        {"name": "Papas Fritas", "type": "Papas", "price": 3500, "description": "Porción clásica"},
        {"name": "Papas Gratinadas", "type": "Papas", "price": 5000, "description": "Con Cheddar o queso cremoso"},
        {"name": "Papas Don Enrique", "type": "Papas", "price": 6000, "description": "Papas grandes con cheddar, panceta y verdeo"},

        # --- AGREGADOS ---
        {"name": "Agregado Jamón", "type": "Agregados", "price": 1500, "description": "Porción extra"},
        {"name": "Agregado Huevo", "type": "Agregados", "price": 1000, "description": "Unidad extra"},
        {"name": "Agregado Panceta", "type": "Agregados", "price": 1500, "description": "Porción extra"},
        {"name": "Agregado Roque o Cheddar", "type": "Agregados", "price": 1500, "description": "Porción extra"},
        {"name": "Agregado Cebolla", "type": "Agregados", "price": 1000, "description": "Porción extra"},
        {"name": "Agregado Papas", "type": "Agregados", "price": 1500, "description": "Porción extra"},
        {"name": "Agregado Hamburguesa", "type": "Agregados", "price": 2500, "description": "Medallón extra"},

        # --- PIZZAS ---
        {"name": "Pizza Muzzarela", "type": "Pizzas", "price": 8000, "description": "Salsa, muzzarela y aceitunas"},
        {"name": "Pizza Jamón y Morrones", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, jamón, morrones"},
        {"name": "Pizza Napolitana", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, rodajitas de tomate"},
        {"name": "Pizza Fugazzeta", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, cebollita salteada"},
        {"name": "Pizza Calabresa", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, rodajas de salamín"},
        {"name": "Pizza Roquefort", "type": "Pizzas", "price": 9000, "description": "Salsa, muzzarela, roquefort"},
        {"name": "Pizza Choclo", "type": "Pizzas", "price": 9500, "description": "Salsa, muzzarela, choclo, huevo, morrón"},
        {"name": "Pizza Ternera", "type": "Pizzas", "price": 12500, "description": "Salsa, muzzarela, ternera, huevo, morrón"},
        {"name": "Pizza Esp. Don Enrique", "type": "Pizzas", "price": 13000, "description": "Salsa, muzzarela, papas fritas, huevos fritos, panceta, verdeo"},
        {"name": "Recargo Pizza Mitad/Mitad", "type": "Otros", "price": 500, "description": "Costo operativo por combinación", "stock": MASSIVE_STOCK},

        # --- NAPOLITANAS (AL PLATO) ---
        {"name": "Mila Napo Clásica (1 pers)", "type": "Napolitanas", "price": 9000, "description": "Milanesa, salsa, queso, jamón. C/Fritas"},
        {"name": "Mila Napo Clásica (2 pers)", "type": "Napolitanas", "price": 15000, "description": "Milanesa, salsa, queso, jamón. C/Fritas (Para compartir)"},
        {"name": "Mila al Roquefort", "type": "Napolitanas", "price": 9000, "description": "Milanesa, salsa, queso cremoso y roquefort. C/Fritas"},
        {"name": "Mila a la Fugazzeta", "type": "Napolitanas", "price": 9000, "description": "Milanesa, queso, cebollita salteada y orégano. C/Fritas"},
        {"name": "Mila a la Americana", "type": "Napolitanas", "price": 9500, "description": "Milanesa, salsa, queso, panceta y huevo frito. C/Fritas"},

        # --- BEBIDAS S/ALCOHOL ---
        {"name": "Linea Pepsi 2lt", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Botella grande"},
        {"name": "Linea Coca 1lt", "type": "Bebidas s/Alcohol", "price": 4000, "description": "Botella mediana"},
        {"name": "Linea Pepsi lata", "type": "Bebidas s/Alcohol", "price": 2000, "description": "Lata"},
        {"name": "Pritty 1lt", "type": "Bebidas s/Alcohol", "price": 2500, "description": "Botella"},
        {"name": "Pritty 500ml", "type": "Bebidas s/Alcohol", "price": 1500, "description": "Botella chica"},
        {"name": "Agua Mineral 500ml", "type": "Bebidas s/Alcohol", "price": 2000, "description": "Botella chica"},
        {"name": "Agua Saborizada 1.5lt", "type": "Bebidas s/Alcohol", "price": 3000, "description": "Botella grande"},
        {"name": "Monster lata", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Energizante"},

        # --- BEBIDAS C/ALCOHOL ---
        {"name": "Quilmes / Salta 1lt", "type": "Bebidas c/Alcohol", "price": 5000, "description": "Cerveza Litro"},
        {"name": "Imperial 1lt", "type": "Bebidas c/Alcohol", "price": 5000, "description": "Cerveza Litro"},
        {"name": "Norte 1lt", "type": "Bebidas c/Alcohol", "price": 4500, "description": "Cerveza Litro"},
        {"name": "Quilmes lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
        {"name": "Salta lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
        {"name": "Imperial lata", "type": "Bebidas c/Alcohol", "price": 3000, "description": "Cerveza Lata"},
        {"name": "Smirnoff lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Lata"},
        {"name": "Vino Tinto 3/4", "type": "Bebidas c/Alcohol", "price": 5500, "description": "Botella"},
    ]

    # [Yo]: CORRECCIÓN CLAVE AQUÍ:
    # create_app() devuelve dos valores: (app, socketio). 
    # Usamos [0] para quedarnos solo con 'app' y descartar 'socketio' que no necesitamos aquí.
    
    # [Yo]: Mapeo manual para nombres que difieren mucho entre el PDF y la Base de Datos
    NAME_MAPPING = {
        "Mila Napo Clásica (1 pers)": "Napo para 1 persona",
        "Mila Napo Clásica (2 pers)": "Napo para 2 personas",
        "Mila al Roquefort": "Milanesa Al roquefort",
        "Mila a la Fugazzeta": "Milanesa a la fugazzeta",
        "Mila a la Americana": "Milanesa a la Americana",
        "Hamburguesa Pecadora": "Hamburguesa Peca",
        "Hamburguesa Simple": "Hamburguesa Simple", # También confirmar si existe "Hamburguesa Común"
        "Especial Don Enrique Burger": "Especial Don Enrique (Hamb.)",
        "Linea Coca 1lt": "Coca de 1lt",
        "Linea Pepsi 2lt": "Linea pepsi 2lt", # Capitalization check
        "Linea Pepsi lata": "Linea pepsi lata",
        # Agrego otros que vi en las capturas por si acaso
        "Agregado Cebolla": "Agregado Cebolla",
        "Agregado Hamburguesa": "Agregado Hamburguesa",
    }

    app = create_app()[0] 
    
    with app.app_context():
        print(f"Iniciando actualización de {len(menu_items)} productos...")
        updated_count = 0
        created_count = 0

        for item_data in menu_items:
            product = None
            
            # [Yo]: 0. Revisar Mapeo Manual primero
            if item_data['name'] in NAME_MAPPING:
                mapped_name = NAME_MAPPING[item_data['name']]
                product = Product.query.filter(Product.name.ilike(mapped_name)).first()
                if product:
                    print(f"🎯 Match por Mapeo Manual: '{item_data['name']}' -> '{product.name}'")

            # [Yo]: 1. Intento coincidencia exacta (ilike)
            if not product:
                product = Product.query.filter(Product.name.ilike(item_data['name'])).first()

            # [Yo]: 2. Si no encuentro, y es una Milanesa, intento buscar con "Sandwich " antes
            if not product and "Milanesa" in item_data['name']:
                 variation_name = f"Sandwich {item_data['name']}"
                 product = Product.query.filter(Product.name.ilike(variation_name)).first()
            
            # [Yo]: 3. Búsqueda laxa (contiene)
            if not product and len(item_data['name']) > 5:
                # Busco que la base contenga parte del nombre o viceversa
                # OJO: Esto puede dar falsos positivos, pero es el último recurso
                pass # Lo desactivo por ahora porque el mapeo manual es más seguro

            if product:
                # [Yo]: Si existe, actualizo precios y stock
                old_price = product.price
                product.price = item_data['price']
                product.type = item_data['type']
                product.description = item_data.get('description', '')
                product.stock = MASSIVE_STOCK
                updated_count += 1
                print(f"🔄 Actualizado: {product.name} (${old_price} -> ${product.price})")
            else:
                # [Yo]: Si no existe, lo creo
                new_product = Product(
                    name=item_data['name'],
                    price=item_data['price'],
                    type=item_data['type'],
                    description=item_data.get('description', ''),
                    stock=MASSIVE_STOCK
                )
                db.session.add(new_product)
                created_count += 1
                print(f"✨ Creado: {item_data['name']} -> ${item_data['price']}")

        # [Yo]: Guardo todo junto
        db.session.commit()
        
        print("-" * 40)
        print(f"PROCESO TERMINADO:")
        print(f"Productos creados: {created_count}")
        print(f"Productos actualizados: {updated_count}")
        print(f"Stock establecido en {MASSIVE_STOCK} para todos.")
        print("-" * 40)

if __name__ == "__main__":
    update_menu_from_pdf()