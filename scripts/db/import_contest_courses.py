from csv import reader

from scripts.db.env import *

courses = {}

def main():
    lines = reader(open('contest.csv', 'r'))
    for contest_id, _name, _type, course_name in lines:
        if course_name == '':
            continue
        if course_name not in courses:
            course = Course(name=course_name)
            db.add(course)
            db.flush()
            courses[course_name] = course
        else:
            course = courses[course_name]

        db.get(Contest, int(contest_id)).course_id = course.id

    input('Press enter to continue...')
    db.commit()

if __name__ == '__main__':
    main()
