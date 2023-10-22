import csv
from typing import *
from uuid import UUID, uuid5

from scripts.db.env import *

db = Session()

def get_name(username):
    return uuid5(ns, str(username))

def export(contest_id, file: csv.writer):
    contest = db.query(Contest).where(Contest.id == contest_id).one()
    print(contest.name)
    problems = db.query(ContestProblem.problem_id).where(ContestProblem.contest_id == contest_id).all()
    submissions: List[JudgeRecord] = db \
        .query(JudgeRecord) \
        .where(JudgeRecord.problem_id.in_(x[0] for x in problems)) \
        .where(JudgeRecord.username.in_(x.username for x in contest.players)) \
        .where(JudgeRecord.time >= contest.start_time) \
        .where(JudgeRecord.time < contest.end_time) \
        .all()
    for submission in submissions:
        file.writerow([
            get_name(submission.username),
            submission.problem_id,
            submission.status,
            submission.score,
            submission.code,
        ])

def main():
    global ns
    ns = UUID(input('UUID namespace: '))
    with open('export.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['user', 'problem', 'status', 'score', 'code'])
        while True:
            contest_id = int(input('Contest ID: '))
            if contest_id < 0: break
            export(contest_id, writer)

if __name__ == '__main__':
    main()
