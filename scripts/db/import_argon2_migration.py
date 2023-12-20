from scripts.db.env import *

from sqlalchemy import update

def main():
    users = open('users-migrated.tsv').readlines()
    users = [x.strip().split('\t') for x in users]
    with Session() as db:
        for uid, password in users:
            stmt = update(User) \
                .where(User.id == int(uid)) \
                .values(password=password)
            db.execute(stmt)
        input()
        db.commit()

if __name__ == '__main__':
    main()
