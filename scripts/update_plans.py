from asyncio import run

from scheduler2.config import s3_buckets
from scheduler2.plan import generate_plan
from scheduler2.s3 import upload_str
from commons.util import serialize

def plan_key(problem_id: str) -> str:
    return f'plans/{problem_id}.json'

async def gen(problem_id):
    try:
        plan = await generate_plan(problem_id)
        plan = serialize(plan)
        await upload_str(s3_buckets.problems, plan_key(problem_id), plan)
    except BaseException as e:
        print(f'Error in {problem_id}: {e}')

async def main():
    while True:
        id = int(input())
        if id == -1: break
        await gen(id)

if __name__ == '__main__':
    run(main())
