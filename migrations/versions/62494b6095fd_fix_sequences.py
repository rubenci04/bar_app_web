"""fix_sequences

Revision ID: 62494b6095fd
Revises: 34fba3506796
Create Date: 2025-09-21 14:18:47.111609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62494b6095fd'
down_revision = '34fba3506796'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        tables = [
            'user', 'product', 'table', 'order', 'order_item', 'cash_session'
        ]
        for table in tables:
            op.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 1), max(id) IS NOT NULL) FROM {table};")




def downgrade():
    pass
