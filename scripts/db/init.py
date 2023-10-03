from alembic import command
from alembic.config import Config
from commons.models import metadata
from scripts.db.env import engine


def init_db():
    metadata.create_all(engine)
    alembic_cfg = Config('alembic.ini')
    command.stamp(alembic_cfg, 'head')

if __name__ == '__main__':
    init_db()
