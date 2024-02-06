from asyncio import run

from botocore.exceptions import ClientError
from sqlalchemy import select, update

from commons.util import deserialize
from scheduler2.config import plan_key, s3_buckets
from scheduler2.plan.languages import languages_accepted
from scheduler2.s3 import read_file
from scripts.db.env import *

s = Session()

async def process_problem(problem_id):
    try:
        plan = await read_file(s3_buckets.problems, plan_key(problem_id))
        plan = deserialize(plan)
        languages = languages_accepted(plan)
    except ClientError:
        print(f'Unable to get judge plan for problem {problem_id}')
        languages = []
    stmt = update(Problem) \
        .where(Problem.id == problem_id) \
        .values(languages_accepted=languages)
    s.execute(stmt)

async def main():
    problems = s.scalars(select(Problem.id).order_by(Problem.id.asc())).all()
    for problem in problems:
        await process_problem(problem)

    input('Press enter to continue...')
    s.commit()

if __name__ == '__main__':
    run(main())
