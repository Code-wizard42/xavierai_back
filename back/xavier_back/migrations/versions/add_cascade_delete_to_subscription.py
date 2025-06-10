"""Add CASCADE delete to subscription_user_id_fkey

Revision ID: add_cascade_delete_to_subscription
Revises: 
Create Date: 2023-11-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cascade_delete_to_subscription'
down_revision = None  # Update this with your previous migration ID if applicable
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.drop_constraint('subscription_user_id_fkey', 'subscription', type_='foreignkey')
    
    # Re-create the foreign key constraint with ON DELETE CASCADE
    op.create_foreign_key(
        'subscription_user_id_fkey',
        'subscription',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Drop the CASCADE foreign key constraint
    op.drop_constraint('subscription_user_id_fkey', 'subscription', type_='foreignkey')
    
    # Re-create the original foreign key constraint without CASCADE
    op.create_foreign_key(
        'subscription_user_id_fkey',
        'subscription',
        'user',
        ['user_id'],
        ['id']
    ) 