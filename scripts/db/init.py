from commons.models import DatabaseVersion, metadata
from scripts.db.env import DATABASE_VERSION, Session, engine


def init_db():
    metadata.create_all(engine)
    with Session() as db:
        v = DatabaseVersion()
        v.version = DATABASE_VERSION
        db.add(v)
        db.commit()

if __name__ == '__main__':
    init_db()
