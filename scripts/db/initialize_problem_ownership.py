from scripts.db.env import *

def main():
    problems = db.scalars(sa.select(Problem).where(Problem.id < 10000)).all()
    for problem in problems:
        if problem.id == 1000:
            continue
        contests = list(problem.contests)
        contests.sort(key=lambda c: c.id)
        for contest in contests:
            if contest.course_id != 1:
                problem.course_id = contest.course_id
                break

    input('Press enter to continue...')
    db.commit()

if __name__ == '__main__':
    main()
