from asyncio import run
from dataclasses import is_dataclass

from botocore.exceptions import ClientError
from sqlalchemy import select

from commons.task_typing import Artifact
from commons.util import deserialize
from scheduler2.config import plan_key, s3_buckets
from scheduler2.s3 import read_file
from scripts.db.env import *
from scripts.update_plans import gen

s = Session()

class ArtifactFound(Exception): pass

def visit(obj):
    if isinstance(obj, Artifact):
        raise ArtifactFound
    if isinstance(obj, list):
        for v in obj:
            visit(v)
    elif is_dataclass(obj):
        for v in obj.__dict__.values():
            visit(v)

async def process_problem(problem_id):
    try:
        plan = await read_file(s3_buckets.problems, plan_key(problem_id))
        plan = deserialize(plan)
    except ClientError:
        print(f'Unable to get judge plan for problem {problem_id}')
        return
    try:
        visit(plan)
    except ArtifactFound:
        print(f'Regenerating judge plan for problem {problem_id}')
        await gen(problem_id)

async def main():
    problems = s.scalars(select(Problem.id).order_by(Problem.id.asc())).all()
    for problem in problems:
        await process_problem(problem)

if __name__ == '__main__':
    run(main())

