from flask import current_app
import click
from . import db

def register_commands(app):
    @app.cli.command('fix-sequences')
    def fix_sequences():
        """Repara las secuencias de todas las tablas."""
        with app.app_context():
            # Reparar la secuencia de la tabla order
            result = db.session.execute(
                """
                SELECT setval('order_id_seq', 
                    COALESCE((SELECT MAX(id) FROM "order"), 0) + 1, 
                    false
                );
                """
            )
            db.session.commit()
            click.echo('Secuencias reparadas correctamente.')