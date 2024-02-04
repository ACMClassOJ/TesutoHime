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

    rrs = db.scalars(sa.select(RealnameReference)).all()
    for rr in rrs:
        contests = db.scalars(
            sa.select(Contest)
              .join(ContestPlayer)
              .join(User)
              .where(User.student_id == rr.student_id)
              .order_by(Contest.id.asc())
        ).all()
        for c in contests:
            if c.course_id != 1:
                rr.course_id = c.course_id
                break

    db.execute(sa.text('''update realname_reference set student_id = student_id || '__' || (random() :: text) where id in (select r.id from realname_reference as r where r.id < (select max(rr.id) from realname_reference as rr where rr.student_id = r.student_id and rr.course_id = r.course_id));'''))

    input('Press enter to continue...')
    db.commit()

if __name__ == '__main__':
    main()
