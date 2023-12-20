import os
from threading import Thread

from argon2 import PasswordHasher

ph = PasswordHasher()
thread_count = 128

def work(users):
    for uid, password in users:
        prefix = '$SHA512$'
        new_prefix = '$argon2+sha512$'
        if not password.startswith(prefix):
            msg = f'Bad password format for user {uid}; perhaps database is not migrated by alembic?'
            raise Exception(msg)
        salt, password = password[len(prefix):].split('$')
        hash = ph.hash(password)
        new_password = f'{new_prefix}{salt}${hash}'
        os.write(1, f'{uid}\t{new_password}\n'.encode())

def main():
    users = open('users.tsv').readlines()
    users = [x.strip().split('\t') for x in users]
    workqueues = [[] for _ in range(thread_count)]
    while len(users) > 0:
        for w in workqueues:
            if len(users) > 0:
                w.append(users.pop())
    threads = []
    for w in workqueues:
        t = Thread(target=work, args=[w])
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

if __name__ == '__main__':
    main()
