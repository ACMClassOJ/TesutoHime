from commons.models import Term
from scripts.db.env import Session
from sqlalchemy import select
import datetime

name = input('Term name? ')

print("print enter term time range [start, end)")

start = input('Term start date? (yyyy-mm-dd): ')
start = datetime.datetime.strptime(start, '%Y-%m-%d')

end = input('Term end date? (yyyy-mm-dd): ')
end = datetime.datetime.strptime(end, '%Y-%m-%d')


if start >= end:
    print('Invalid time range.')
    exit()

print(f"""Please confirm:
Term name: \x1b[32m{name}\x1b[0m
Term start date: \x1b[32m{start}\x1b[0m
Term end date: \x1b[32m{end}\x1b[0m
Y/N?""")

x = input()
if x.lower() != 'y':
    print('Aborted.')
    exit()

with Session() as db:
    # TODO: make sure no term is overlapping
    db.add(Term(name=name, start_time=start, end_time=end))
    db.commit()
