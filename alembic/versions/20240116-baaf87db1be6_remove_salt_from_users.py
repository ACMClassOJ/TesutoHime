"""remove salt from users

Revision ID: baaf87db1be6
Revises: 4a8c8f0327cb
Create Date: 2024-01-16 09:44:22.312863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'baaf87db1be6'
down_revision: Union[str, None] = '4a8c8f0327cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('account', 'salt')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('salt', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###