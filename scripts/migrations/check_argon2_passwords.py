import os
from threading import Thread

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

ph = PasswordHasher()
thread_count = 128

def work(users):
    for uid, password, new_password in users:
        prefix = '$SHA512$'
        new_prefix = '$argon2+sha512$'
        if not password.startswith(prefix):
            msg = f'Bad password format for user {uid}; perhaps database is not migrated by alembic?'
            raise Exception(msg)
        if not new_password.startswith(new_prefix):
            raise Exception(f'Bad new password format for user {uid}')
        salt, password = password[len(prefix):].split('$')
        new_password = new_password[len(new_prefix):].split('$')
        new_salt = new_password[0]
        new_password = '$'.join(new_password[1:])
        if salt != new_salt:
            raise Exception(f'Salt mismatch for user {uid}')
        try:
            if not ph.verify(new_password, password):
                raise VerificationError()
        except VerificationError as e:
            raise Exception(f'Password mismatch for user {uid}') from e
        os.write(1, f'{uid}\n'.encode())

def main():
    users = open('users.tsv').readlines()
    users = [x.strip().split('\t') for x in users]
    new_passwords = open('users-migrated.tsv').readlines()
    new_passwords = dict(x.strip().split('\t') for x in new_passwords)
    if len(users) != len(new_passwords):
        raise Exception('Length mismatch')
    workqueues = [[] for _ in range(thread_count)]
    while len(users) > 0:
        for w in workqueues:
            if len(users) > 0:
                uid, password = users.pop()
                new_password = new_passwords[uid]
                w.append((uid, password, new_password))
    threads = []
    for w in workqueues:
        t = Thread(target=work, args=[w])
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

if __name__ == '__main__':
    main()
