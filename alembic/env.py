from logging.config import fileConfig

from alembic import context
from commons.models import metadata
from scripts.db.env import engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata

context.configure(
    connection=engine.connect(),
    target_metadata=target_metadata,
    dialect_opts={"paramstyle": "named"},
)

with context.begin_transaction():
    context.run_migrations()
