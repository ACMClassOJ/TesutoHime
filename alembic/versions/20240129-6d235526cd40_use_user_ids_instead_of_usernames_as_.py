"""use user ids instead of usernames as foreign keys

Revision ID: 6d235526cd40
Revises: 08bbf757f96b
Create Date: 2024-01-29 15:31:28.603123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d235526cd40'
down_revision: Union[str, None] = '08bbf757f96b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contest_player', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('contest_player', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.add_column('contest_player', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.alter_column('contest_player', 'contest_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.create_index(op.f('ix_contest_player_user_id'), 'contest_player', ['user_id'], unique=False)
    op.create_foreign_key(None, 'contest_player', 'user', ['user_id'], ['id'])
    op.add_column('contest_problem', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.add_column('contest_problem', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.alter_column('contest_problem', 'contest_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('contest_problem', 'problem_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('discussion', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_discussion_user_id'), 'discussion', ['user_id'], unique=False)
    op.create_foreign_key(None, 'discussion', 'user', ['user_id'], ['id'])
    op.add_column('judge_record_v1', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_judge_record_v1_user_id'), 'judge_record_v1', ['user_id'], unique=False)
    op.create_foreign_key(None, 'judge_record_v1', 'user', ['user_id'], ['id'])
    op.add_column('judge_record_v2', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_judge_record_v2_user_id'), 'judge_record_v2', ['user_id'], unique=False)
    op.create_foreign_key(None, 'judge_record_v2', 'user', ['user_id'], ['id'])

    def convert_table(table_name):
        op.execute(f'''UPDATE "{table_name}" SET user_id = (SELECT id FROM "user" WHERE "user".username = "{table_name}".username);''')
        op.alter_column(table_name, 'user_id', nullable=False)

    convert_table('contest_player')
    convert_table('discussion')
    convert_table('judge_record_v1')
    convert_table('judge_record_v2')

    op.drop_index('contest_id_username', table_name='contest_player')
    op.drop_index('ix_contest_player_username', table_name='contest_player')
    op.drop_constraint('contest_player_username_fkey', 'contest_player', type_='foreignkey')
    op.drop_column('contest_player', 'username')
    op.drop_index('ix_discussion_username', table_name='discussion')
    op.drop_constraint('discussion_username_fkey', 'discussion', type_='foreignkey')
    op.drop_column('discussion', 'username')
    op.drop_index('ix_judge_record_v1_username', table_name='judge_record_v1')
    op.drop_constraint('judge_record_v1_username_fkey', 'judge_record_v1', type_='foreignkey')
    op.drop_column('judge_record_v1', 'username')
    op.drop_index('ix_judge_record_v2_username', table_name='judge_record_v2')
    op.drop_constraint('judge_record_v2_username_fkey', 'judge_record_v2', type_='foreignkey')
    op.drop_column('judge_record_v2', 'username')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('judge_record_v2', sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key('judge_record_v2_username_fkey', 'judge_record_v2', 'user', ['username'], ['username'])
    op.create_index('ix_judge_record_v2_username', 'judge_record_v2', ['username'], unique=False)
    op.add_column('judge_record_v1', sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key('judge_record_v1_username_fkey', 'judge_record_v1', 'user', ['username'], ['username'])
    op.create_index('ix_judge_record_v1_username', 'judge_record_v1', ['username'], unique=False)
    op.add_column('discussion', sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key('discussion_username_fkey', 'discussion', 'user', ['username'], ['username'])
    op.create_index('ix_discussion_username', 'discussion', ['username'], unique=False)
    op.alter_column('contest_problem', 'problem_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('contest_problem', 'contest_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.add_column('contest_player', sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key('contest_player_username_fkey', 'contest_player', 'user', ['username'], ['username'])
    op.create_index('ix_contest_player_username', 'contest_player', ['username'], unique=False)
    op.create_index('contest_id_username', 'contest_player', ['contest_id', 'username'], unique=False)
    op.alter_column('contest_player', 'contest_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    def convert_table(table_name):
        op.execute(f'''UPDATE "{table_name}" SET username = (SELECT id FROM "user" WHERE "user".id = "{table_name}".user_id);''')
        op.alter_column(table_name, 'username', nullable=False)

    convert_table('contest_player')
    convert_table('discussion')
    convert_table('judge_record_v1')
    convert_table('judge_record_v2')

    op.drop_constraint('judge_record_v2_user_id_fkey', 'judge_record_v2', type_='foreignkey')
    op.drop_index(op.f('ix_judge_record_v2_user_id'), table_name='judge_record_v2')
    op.drop_column('judge_record_v2', 'user_id')
    op.drop_constraint('judge_record_v1_user_id_fkey', 'judge_record_v1', type_='foreignkey')
    op.drop_index(op.f('ix_judge_record_v1_user_id'), table_name='judge_record_v1')
    op.drop_column('judge_record_v1', 'user_id')
    op.drop_constraint('discussion_user_id_fkey', 'discussion', type_='foreignkey')
    op.drop_index(op.f('ix_discussion_user_id'), table_name='discussion')
    op.drop_column('discussion', 'user_id')
    op.drop_column('contest_problem', 'updated_at')
    op.drop_column('contest_problem', 'created_at')
    op.drop_constraint('contest_player_user_id_fkey', 'contest_player', type_='foreignkey')
    op.drop_index(op.f('ix_contest_player_user_id'), table_name='contest_player')
    op.drop_column('contest_player', 'updated_at')
    op.drop_column('contest_player', 'created_at')
    op.drop_column('contest_player', 'user_id')
    # ### end Alembic commands ###
