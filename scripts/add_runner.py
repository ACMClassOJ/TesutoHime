from commons.models import JudgeRunner2
from scripts.db.env import Session


def add_runner_cli():
    runner = JudgeRunner2()
    runner.id = int(input('Runner ID? '))
    runner.name = input('Runner name? ')
    runner.hardware = input('Runner hardware? ')
    runner.provider = input('Runner provider? ')
    with Session() as db:
        db.add(runner)
        db.commit()
    print('Done.')


if __name__ == '__main__':
    add_runner_cli()
