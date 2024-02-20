"""add data license agreed to user

Revision ID: ae57b081a531
Revises: 73e16ec2d7ea
Create Date: 2024-02-20 08:09:28.495082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae57b081a531'
down_revision: Union[str, None] = '73e16ec2d7ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('data_license_agreed', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'data_license_agreed')
    # ### end Alembic commands ###