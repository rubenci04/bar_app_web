# Archivo: update_products.py
import os
import sys

# [Yo]: Configuro la ruta del proyecto para que Python sepa dónde buscar 'app'.
# Esto me evita problemas de importación cuando ejecute el script suelto desde la terminal del servidor.
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Product

def update_menu_from_pdf():
    """
    [Yo]: Esta función contiene la lógica principal. He volcado todos los datos
    del PDF 'Menu imprimible marzo' en la lista 'menu_items' con los valores
    actualizados tras la subida de la carne y demás insumos.
    El script recorrerá esta lista y actualizará o creará los productos en la base de datos de producción.
    """
    
    # [Yo]: Defino el stock masivo aquí para poder cambiarlo fácil en el futuro si hace falta.
    MASSIVE_STOCK = 100000

    # [Yo]: Aquí está el mapeo completo del PDF de marzo con sus descripciones precisas.
    # Agregué también el Mexicano 1/4 por si algún cliente pide el formato individual.
    menu_items = [
        # --- SANDWICHS ---
        {"name": "Milanesa Común", "type": "Sandwiches", "price": 8000, "description": "Sandwich de milanesa básico"},
        {"name": "Milanesa Especial", "type": "Sandwiches", "price": 10000, "description": "Jamón, queso y papas fritas"},
        {"name": "Lomo Común", "type": "Sandwiches", "price": 10000, "description": "Sandwich de lomo básico"},
        {"name": "Lomo Cheddar", "type": "Sandwiches", "price": 10000, "description": "Lomo con queso cheddar"},
        {"name": "Lomo Especial", "type": "Sandwiches", "price": 12000, "description": "Jamón, queso, huevo y papas fritas"},
        {"name": "Miga Jamón y Queso", "type": "Sandwiches", "price": 7000, "description": "Plancha entera"},
        {"name": "Miga Ternera y Queso", "type": "Sandwiches", "price": 10000, "description": "Plancha entera"},
        {"name": "Mexicano (1/2 para 2 pers)", "type": "Sandwiches", "price": 17000, "description": "Jamón, queso, lechuga, tomate, lomo, cubierta queso, huevo c/papas"},
        {"name": "Mexicano (1/4 para 1 pers)", "type": "Sandwiches", "price": 11000, "description": "Jamón, queso, lechuga, tomate, lomo, cubierta queso, huevo c/papas"},
        {"name": "Ternera en Sanguchero", "type": "Sandwiches", "price": 10000, "description": "Ternera, queso, lechuga y tomate"},

        # --- BURGERS ---
        {"name": "Hamburguesa Simple", "type": "Hamburguesas", "price": 7000, "description": "Cheddar, lechuga, tomate, ketchup C/ papas fritas"},
        {"name": "Hamburguesa Especial", "type": "Hamburguesas", "price": 8000, "description": "Cheddar, lechuga, huevo, jamon, ketchup.C/ papas fritas"},
        {"name": "Hamburguesa Roque", "type": "Hamburguesas", "price": 8000, "description": "Tybo, cebolla, lechuga, tomate, roquefort, ketchup. C/ papas fritas"},
        {"name": "Hamburguesa Pecadora", "type": "Hamburguesas", "price": 8000, "description": "Cheddar, aros de cebolla, huevo, panceta y ketchup. C/ papas fritas"},
        {"name": "Especial Don Enrique Burger", "type": "Hamburguesas", "price": 9000, "description": "Doble Hamburguesa, cheddar, huevo, panceta, cebolla caramelizada y ketchup. C/ papas fritas"},

        # --- PAPAS ---
        {"name": "Papas Fritas", "type": "Papas", "price": 4000, "description": "Porción clásica"},
        {"name": "Papas Gratinadas", "type": "Papas", "price": 6000, "description": "Con Cheddar o queso cremoso"},
        {"name": "Papas Don Enrique", "type": "Papas", "price": 7000, "description": "Papas grandes con cheddar, panceta y verdeo"},

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
        {"name": "Pizza Calabresa", "type": "Pizzas", "price": 9500, "description": "Salsa, muzzarela, rodajas de salamín"},
        {"name": "Pizza Roquefort", "type": "Pizzas", "price": 9500, "description": "Salsa, muzzarela, roquefort"},
        {"name": "Pizza Choclo", "type": "Pizzas", "price": 10000, "description": "Salsa, muzzarela, choclo, huevo, morrón"},
        {"name": "Pizza Ternera", "type": "Pizzas", "price": 13000, "description": "Salsa, muzzarela, ternera, huevo, morrón"},
        {"name": "Pizza Esp. Don Enrique", "type": "Pizzas", "price": 13000, "description": "Salsa, muzzarela, papas fritas, huevos fritos, panceta, verdeo"},
        {"name": "Recargo Pizza Mitad/Mitad", "type": "Otros", "price": 500, "description": "Costo operativo por combinación", "stock": MASSIVE_STOCK},

        # --- NAPOLITANAS (AL PLATO) ---
        {"name": "Mila Napo Clásica (1 pers)", "type": "Napolitanas", "price": 10000, "description": "Milanesa, salsa, queso, jamón. C/Fritas"},
        {"name": "Mila Napo Clásica (2 pers)", "type": "Napolitanas", "price": 17000, "description": "Milanesa, salsa, queso, jamón. C/Fritas (Para compartir)"},
        {"name": "Mila al Roquefort", "type": "Napolitanas", "price": 10000, "description": "Milanesa, salsa, queso cremoso y roquefort. C/Fritas"},
        {"name": "Mila a la Fugazzeta", "type": "Napolitanas", "price": 10000, "description": "Milanesa, queso, cebollita salteada y orégano. C/Fritas"},
        {"name": "Mila a la Americana", "type": "Napolitanas", "price": 11000, "description": "Milanesa, salsa, queso, panceta y huevo frito. C/Fritas"},

        # --- BEBIDAS S/ALCOHOL ---
        {"name": "Linea Pepsi 2lt", "type": "Bebidas s/Alcohol", "price": 4000, "description": "Botella grande"},
        {"name": "Linea Coca 1lt", "type": "Bebidas s/Alcohol", "price": 5000, "description": "Botella mediana"},
        {"name": "Linea Pepsi lata", "type": "Bebidas s/Alcohol", "price": 2500, "description": "Lata"},
        {"name": "Pritty 1lt", "type": "Bebidas s/Alcohol", "price": 3000, "description": "Botella"},
        {"name": "Pritty 500ml", "type": "Bebidas s/Alcohol", "price": 2000, "description": "Botella chica"},
        {"name": "Agua Saborizada 1.5lt", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Botella grande"},
        {"name": "Monster lata", "type": "Bebidas s/Alcohol", "price": 3500, "description": "Energizante"},

        # --- BEBIDAS C/ALCOHOL ---
        {"name": "Quilmes / Salta 1lt", "type": "Bebidas c/Alcohol", "price": 6000, "description": "Cerveza Litro"},
        {"name": "Imperial 1lt", "type": "Bebidas c/Alcohol", "price": 6000, "description": "Cerveza Litro"},
        {"name": "Norte 1lt", "type": "Bebidas c/Alcohol", "price": 5500, "description": "Cerveza Litro"},
        {"name": "Quilmes lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Cerveza Lata"},
        {"name": "Salta lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Cerveza Lata"},
        {"name": "Imperial lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Cerveza Lata"},
        {"name": "Smirnoff lata", "type": "Bebidas c/Alcohol", "price": 3500, "description": "Lata"},
        {"name": "Vino Tinto 3/4", "type": "Bebidas c/Alcohol", "price": 6000, "description": "Botella"},
    ]

    # [Yo]: CORRECCIÓN CLAVE AQUÍ:
    # create_app() devuelve dos valores: (app, socketio). 
    # Usamos [0] para quedarnos solo con 'app' y descartar 'socketio' que no necesitamos para manejar la BD por terminal.
    
    # [Yo]: Dejo configurado el mapeo manual para nombres que difieren mucho entre el PDF y la Base de Datos.
    # Esto es vital para no generar duplicados (ejemplo: que cree "Hamburguesa Pecadora" nueva si ya existe como "Hamburguesa Peca").
    NAME_MAPPING = {
        "Mila Napo Clásica (1 pers)": "Napo para 1 persona",
        "Mila Napo Clásica (2 pers)": "Napo para 2 personas",
        "Mila al Roquefort": "Milanesa Al roquefort",
        "Mila a la Fugazzeta": "Milanesa a la fugazzeta",
        "Mila a la Americana": "Milanesa a la Americana",
        "Hamburguesa Pecadora": "Hamburguesa Peca",
        "Hamburguesa Simple": "Hamburguesa Simple", 
        "Especial Don Enrique Burger": "Especial Don Enrique (Hamb.)",
        "Linea Coca 1lt": "Coca de 1lt",
        "Linea Pepsi 2lt": "Linea pepsi 2lt",
        "Linea Pepsi lata": "Linea pepsi lata",
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

            # [Yo]: 1. Intento coincidencia exacta (ilike) para buscar la existencia previa
            if not product:
                product = Product.query.filter(Product.name.ilike(item_data['name'])).first()

            # [Yo]: 2. Si no encuentro, y es una Milanesa, busco el formato "Sandwich de ..."
            if not product and "Milanesa" in item_data['name']:
                 variation_name = f"Sandwich {item_data['name']}"
                 product = Product.query.filter(Product.name.ilike(variation_name)).first()
            
            if product:
                # [Yo]: Si lo encuentra, solamente machaco el precio, la descripción y le renuevo el stock máximo.
                old_price = product.price
                product.price = item_data['price']
                product.type = item_data['type']
                product.description = item_data.get('description', '')
                product.stock = MASSIVE_STOCK
                updated_count += 1
                print(f"🔄 Actualizado: {product.name} (${old_price} -> ${product.price})")
            else:
                # [Yo]: Si definitivamente es nuevo, lo instancio y lo agrego a la sesión.
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

        # [Yo]: Aplico todos los cambios de golpe en la base de datos (Commit).
        db.session.commit()
        
        print("-" * 40)
        print(f"PROCESO TERMINADO:")
        print(f"Productos creados: {created_count}")
        print(f"Productos actualizados: {updated_count}")
        print(f"Stock establecido en {MASSIVE_STOCK} para todos.")
        print("-" * 40)

if __name__ == "__main__":
    update_menu_from_pdf()