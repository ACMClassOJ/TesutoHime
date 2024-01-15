from datetime import datetime
from inspect import isclass

from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, create_engine, insert, select, text
from sqlalchemy.orm import Session, sessionmaker

import scripts.db.mysql_to_pg.mysql_models as mysql_models
import scripts.db.mysql_to_pg.pg_models as pg_models


def create_session(db_name, init=False) -> Session:
    url = input(f'Connection URL for {db_name}: ')
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)

    try:
        with Session() as db:
            one = db.query(1).one()
            if one[0] != 1:
                raise Exception('Invalid database return value')
    except Exception as e:
        raise Exception(f'Invalid database connection {url}') from e

    if init:
        class FakeEnv:
            metadata = pg_models.metadata
            engine = None
        FakeEnv.engine = engine
        import sys
        sys.modules['commons.models'] = sys.modules['scripts.db.env'] = FakeEnv()

        pg_models.metadata.create_all(engine)
        alembic_cfg = Config('alembic.ini')
        command.stamp(alembic_cfg, '4d92921b834b')

    return Session()

mysql_session = create_session('MySQL')
pg_session = create_session('PostgreSQL', True)

username_database = {}

def migrate_model(my_model, pg_model):
    print(f'Migrating table {my_model.__tablename__}')
    query = select(my_model).execution_options(yield_per=1000)
    for (row,) in mysql_session.execute(query):
        data = dict(filter(lambda e: e[0][0] != '_', row.__dict__.items()))
        for k in data:
            if isinstance(data[k], int) and \
               isinstance(pg_model.__dict__[k].expression.type, DateTime):
                data[k] = datetime.fromtimestamp(data[k])
            elif isinstance(data[k], mysql_models.JudgeStatus):
                data[k] = pg_models.JudgeStatus.__dict__[data[k].name]
            elif isinstance(data[k], str):
                data[k] = data[k].replace('\x00', '\ufffd')
        if my_model == mysql_models.User:
            username = data['username']
            username_database[username.lower().strip()] = username
        elif 'username' in data:
            data['username'] = username_database[data['username'].lower().strip()]
        model = pg_model(**data)
        pg_session.add(model)
        pg_session.flush()

    # technically there is an SQL injection here, but it would not hurt anyways.
    pg_session.execute(text(f'SELECT setval(pg_get_serial_sequence(\'{pg_model.__tablename__}\', \'id\'), max(id)) FROM "{pg_model.__tablename__}"'))
    pg_session.flush()

def migrate_contest_player():
    print('Migrating table Contest_Player')
    c = mysql_models.ContestPlayer.c
    query = select(c.tempID, c.Belong, c.Username).execution_options(yield_per=1000)
    for id, contest_id, username in mysql_session.execute(query):
        username = username_database[username.lower().strip()]
        pg_session.execute(
            insert(pg_models.ContestPlayer) \
                .values(id=id, contest_id=contest_id, username=username)
        )
        pg_session.flush()

    pg_session.execute(text('SELECT setval(pg_get_serial_sequence(\'contest_player\', \'id\'), max(id)) FROM "contest_player"'))
    pg_session.flush()

def main():
    for k in mysql_models.__dict__:
        Model = mysql_models.__dict__[k]
        if not isclass(Model): continue
        if issubclass(Model, mysql_models.Base) and Model != mysql_models.Base:
            migrate_model(Model, pg_models.__dict__[k])

    migrate_contest_player()

    input('Press enter to continue...')
    pg_session.commit()

if __name__ == '__main__':
    main()
