from asyncio import run
from traceback import print_exception

from botocore.exceptions import ClientError
from sqlalchemy import select, update

from commons.util import deserialize, dump_dataclass
from scheduler2.config import plan_key, s3_buckets
from scheduler2.plan.summary import summarize
from scheduler2.s3 import read_file
from scripts.db.env import *

s = Session()

async def process_problem(problem_id):
    try:
        plan = await read_file(s3_buckets.problems, plan_key(problem_id))
        plan = deserialize(plan)
        summary = dump_dataclass(summarize(plan))
    except ClientError:
        print(f'Unable to get judge plan for problem {problem_id}')
        summary = None
    except Exception as e:
        print(f'Unable to generate plan summary for problem {problem_id}')
        print_exception(e)
        summary = None
    stmt = update(Problem) \
        .where(Problem.id == problem_id) \
        .values(plan_summary=summary)
    s.execute(stmt)

async def main():
    problems = s.scalars(select(Problem.id).order_by(Problem.id.asc())).all()
    for problem in problems:
        await process_problem(problem)

    input('Press enter to continue...')
    s.commit()

if __name__ == '__main__':
    run(main())
