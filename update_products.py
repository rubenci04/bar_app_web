
import os
import sys
import re

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Product

def parse_price(price_str):
    # Use regex to find numbers, allowing for optional decimal part
    match = re.search(r'\d+', str(price_str))
    if match:
        return float(match.group(0))
    return 0.0

def update_products_from_menu():
    """
    This function parses a menu, and updates the products in the database.
    If a product with the same name exists, it updates the price.
    Otherwise, it creates a new product.
    """
    products_data = [
        # SANDWICHS
        {"name": "Milanesa Común", "price": 6500, "type": "Sandwichs", "description": ""},
        {"name": "Milanesa Esp", "price": 7500, "type": "Sandwichs", "description": "Jamón, queso y papas fritas"},
        {"name": "Lomo Común", "price": 7500, "type": "Sandwichs", "description": ""},
        {"name": "Lomo Chedar", "price": 7500, "type": "Sandwichs", "description": ""},
        {"name": "Lomo Especial", "price": 9000, "type": "Sandwichs", "description": "Jamón, queso y papas fritas"},
        {"name": "Ternera en sanguchero", "price": 8000, "type": "Sandwichs", "description": ""},
        # MIGA
        {"name": "Jamón y Queso", "price": 6000, "type": "Miga", "description": ""},
        {"name": "Ternera y Queso", "price": 6500, "type": "Miga", "description": ""},
        {"name": "Mexicano 1/2", "price": 13000, "type": "Miga", "description": "Jamón, queso, lechuga, tomate, lomo, cubierta gratinada, huevo c/papas. Comparten 2 pers"},
        {"name": "Mexicano 1/4", "price": 8000, "type": "Miga", "description": "Jamón, queso, lechuga, tomate, lomo, cubierta gratinada, huevo c/papas. 1 pers"},
        # BURGERS
        {"name": "Hamburguesa Simple", "price": 5500, "type": "Burgers", "description": "Hamburguesa, cheddar, lechuga, tomate, salsa bbq. C/ papas fritas."},
        {"name": "Hamburguesa Especial", "price": 6000, "type": "Burgers", "description": "Hamburguesa, cheddar, lechuga, tomate, huevo, jamon, salsa bbq.C/ papas fritas."},
        {"name": "Hamburguesa Roque", "price": 6000, "type": "Burgers", "description": "Hamburguesa, tybo, cebolla, lechuga, tomate, roquefort, salsa bbq. C/ papas fritas."},
        {"name": "Hamburguesa Peca", "price": 6000, "type": "Burgers", "description": "Hamburguesa, cheddar, aros de cebolla, huevo, panceta y salsa bbq. C/ papas fritas."},
        {"name": "Especial Don Enrique", "price": 7000, "type": "Burgers", "description": "Doble Hamburguesa, cheddar huevo, panceta, cebolla caramelizada y salsa bbq. C/ papas fritas."},
        # PAPAS
        {"name": "Papas Fritas", "price": 3500, "type": "Papas", "description": ""},
        {"name": "Gratinadas", "price": 4500, "type": "Papas", "description": "Chedar/queso cremoso"},
        {"name": "Papas Don Enrique", "price": 5000, "type": "Papas", "description": "Papas grandes con cheddar, panceta y verdeo"},
        # AGREGADOS
        {"name": "Jamon", "price": 1000, "type": "Agregados", "description": ""},
        {"name": "Huevo", "price": 1000, "type": "Agregados", "description": ""},
        {"name": "Panceta", "price": 1000, "type": "Agregados", "description": ""},
        {"name": "Roque o cheddar", "price": 1000, "type": "Agregados", "description": ""},
        {"name": "Cebolla", "price": 500, "type": "Agregados", "description": ""},
        {"name": "Papas", "price": 1500, "type": "Agregados", "description": ""},
        {"name": "Hamburguesa", "price": 2000, "type": "Agregados", "description": ""},
        # PIZZAS
        {"name": "Muzzarela", "price": 8000, "type": "Pizzas", "description": "Salsa, muzzarela y aceitunas"},
        {"name": "Jamón y Morrones", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, jamón, morones"},
        {"name": "Napolitana", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, rodajitas de tomate"},
        {"name": "Fugazzeta", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, cebollita salteada"},
        {"name": "Calabresa", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, rodajas de salamin"},
        {"name": "Roquefort", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, roquefort"},
        {"name": "Choclo", "price": 9000, "type": "Pizzas", "description": "Salsa, muzzarela, choclo, huevo, morrón"},
        {"name": "Ternera", "price": 11500, "type": "Pizzas", "description": "Salsa, muzzarela, ternera, huevo, morron"},
        {"name": "Especial Don Enrique (Pizza)", "price": 12000, "type": "Pizzas", "description": "Salsa, muzzarela, papas fritas, huevos fritos, panceta, cebollita de verdeo"},
        # NAPOLITANAS
        {"name": "Clásica (para 1)", "price": 8000, "type": "Napolitanas", "description": ""},
        {"name": "Clásica (para 2)", "price": 14000, "type": "Napolitanas", "description": ""},
        {"name": "Milanesa Al roquefort", "price": 8500, "type": "Napolitanas", "description": "Milanesa, salsa, queso cremoso y queso roquefort. C/Fritas"},
        {"name": "Milanesa a la fugazzeta", "price": 8500, "type": "Napolitanas", "description": "Milanesa, queso, cebollita salteada y oregano. C/Fritas"},
        {"name": "Milanesa a la Americana", "price": 9500, "type": "Napolitanas", "description": "Milanesa, salsa, queso, panceta y huevo frito. C/Fritas"},
        # BEBIDAS S/ ALCOHOL
        {"name": "Linea pepsi 2lt", "price": 3500, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Linea coca 1lt", "price": 4000, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Linea Pepsi lata", "price": 2000, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Pritty 1lt", "price": 2500, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Pritty 500ml", "price": 1500, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Agua Mineral 500ml", "price": 2000, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Agua Saborizada 1,5lt", "price": 3000, "type": "Bebidas s/ alcohol", "description": ""},
        {"name": "Monster lata", "price": 3000, "type": "Bebidas s/ alcohol", "description": ""},
        # BEBIDAS C/ ALCOHOL
        {"name": "Quilmes / Salta 1lt", "price": 4500, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Imperial 1lt", "price": 5000, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Norte 1lt", "price": 4500, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Quilmes lata", "price": 3000, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Salta lata", "price": 3000, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Imperial lata", "price": 3000, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Smirnoff - lata", "price": 3000, "type": "Bebidas c/ alcohol", "description": ""},
        {"name": "Vino tinto 3/4", "price": 5000, "type": "Bebidas c/ alcohol", "description": ""},
    ]

    app = create_app()
    with app.app_context():
        for item in products_data:
            product_name = item["name"]
            product_price = parse_price(item["price"])
            product_type = item["type"]
            product_description = item["description"]

            existing_product = Product.query.filter_by(name=product_name).first()

            if existing_product:
                # Update price if product exists
                if existing_product.price != product_price:
                    print(f"Updating price for {product_name} from {existing_product.price} to {product_price}")
                    existing_product.price = product_price
            else:
                # Create new product if it does not exist
                print(f"Adding new product: {product_name}")
                new_product = Product(
                    name=product_name,
                    price=product_price,
                    type=product_type,
                    description=product_description,
                    stock=100  # Default stock
                )
                db.session.add(new_product)

        db.session.commit()
        print("Database update complete.")

if __name__ == "__main__":
    update_products_from_menu()
