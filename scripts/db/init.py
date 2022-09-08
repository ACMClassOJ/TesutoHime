from commons.models import metadata
from scripts.db.env import engine

def init_db():
    metadata.create_all(engine)

if __name__ == '__main__':
    init_db()
