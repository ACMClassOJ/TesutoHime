"""add timestamps to records

Revision ID: 12a5cd563e99
Revises: baaf87db1be6
Create Date: 2024-01-16 09:57:03.349444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12a5cd563e99'
down_revision: Union[str, None] = 'baaf87db1be6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('account', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.execute('''
        UPDATE account SET created_at = (SELECT min(x) FROM
            (VALUES
                ((SELECT min(to_timestamp(time)) FROM judge_record_v1 WHERE judge_record_v1.username = account.username)),
                ((SELECT min(created) FROM judge_record_v2 WHERE judge_record_v2.username = account.username)),
                ((SELECT min(start_time)
                  FROM contest_player
                  JOIN contest ON contest.id = contest_player.contest_id
                  WHERE contest_player.username = account.username))
            ) AS VALUES(x)
        );
    ''')
    op.execute('UPDATE account SET created_at = now() WHERE created_at IS NULL;')
    op.execute('UPDATE account SET updated_at = created_at;')

    op.add_column('contest', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('contest', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.execute('UPDATE contest SET created_at = start_time, updated_at = start_time;')

    op.add_column('discussion', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('discussion', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.execute('UPDATE discussion SET created_at = time, updated_at = time;')
    op.drop_column('discussion', 'time')

    op.add_column('judge_record_v2', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('judge_record_v2', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.drop_index('problem_id_created', table_name='judge_record_v2')
    op.create_index('problem_id_created_at', 'judge_record_v2', ['problem_id', 'created_at'], unique=False)
    op.execute('UPDATE judge_record_v2 SET created_at = created, updated_at = created;')
    op.drop_column('judge_record_v2', 'created')
    
    op.add_column('judge_runner_v2', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('judge_runner_v2', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))

    op.add_column('problem', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('problem', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.execute('''
        UPDATE problem SET created_at = (SELECT min(x) FROM
            (VALUES
                ((SELECT min(to_timestamp(time)) FROM judge_record_v1 WHERE judge_record_v1.problem_id = problem.id)),
                ((SELECT min(created_at) FROM judge_record_v2 WHERE judge_record_v2.problem_id = problem.id)),
                ((SELECT min(start_time)
                  FROM contest_problem
                  JOIN contest ON contest_problem.contest_id = contest.id
                  WHERE contest_problem.problem_id = problem.id))
            ) AS VALUES(x)
        );
    ''')
    op.execute('UPDATE problem SET created_at = now() WHERE created_at IS NULL;')
    op.execute('UPDATE problem SET updated_at = created_at;')

    op.add_column('realname_reference', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('realname_reference', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.execute('UPDATE realname_reference SET created_at = (SELECT min(created_at) FROM account WHERE account.student_id = realname_reference.student_id);')
    op.execute('UPDATE realname_reference SET created_at = now() WHERE created_at IS NULL;')
    op.execute('UPDATE realname_reference SET updated_at = created_at;')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('realname_reference', 'updated_at')
    op.drop_column('realname_reference', 'created_at')
    op.drop_column('problem', 'updated_at')
    op.drop_column('problem', 'created_at')
    op.drop_column('judge_runner_v2', 'updated_at')
    op.drop_column('judge_runner_v2', 'created_at')
    op.add_column('judge_record_v2', sa.Column('created', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True))
    op.drop_index('problem_id_created_at', table_name='judge_record_v2')
    op.create_index('problem_id_created', 'judge_record_v2', ['problem_id', 'created'], unique=False)
    op.drop_column('judge_record_v2', 'updated_at')
    op.add_column('discussion', sa.Column('time', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_column('discussion', 'updated_at')
    op.drop_column('contest', 'updated_at')
    op.drop_column('contest', 'created_at')
    op.drop_column('account', 'updated_at')
    op.drop_column('account', 'created_at')
    # ### end Alembic commands ###
    op.execute('UPDATE discussion SET time = created_at;')
    op.drop_column('discussion', 'created_at')

    op.execute('UPDATE judge_record_v2 SET created_at = created;')
    op.drop_column('judge_record_v2', 'created_at')
