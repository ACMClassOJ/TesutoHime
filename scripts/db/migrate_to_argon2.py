from argon2 import PasswordHasher
from sqlalchemy import select, update

from scripts.db.env import *

def main():
    ph = PasswordHasher()
    with Session() as db:
        users = db.execute(select(User.id, User.password)).all()
        for uid, password in users:
            prefix = '$SHA512$'
            new_prefix = '$argon2+sha512$'
            if not password.startswith(prefix):
                msg = f'Bad password format for user {uid}; perhaps database is not migrated by alembic?'
                raise Exception(msg)
            salt, password = password[len(prefix):].split('$')
            hash = ph.hash(password)
            new_password = f'{new_prefix}{salt}${hash}'
            stmt = update(User) \
                .where(User.id == uid) \
                .values(password=new_password)
            db.execute(stmt)
        db.commit()

if __name__ == '__main__':
    main()
