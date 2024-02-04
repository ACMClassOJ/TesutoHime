from csv import reader

from scripts.db.env import *

tags = {}
terms = {}
term_times = {
    2020: [
        '9-7-1-10',
        '2-22-6-27',
        '6-28-7-25',
    ],
    2021: [
        '9-13-1-16',
        '2-14-6-19',
        '6-20-7-17',
    ],
    2022: [
        '9-12-1-15',
        '2-13-6-18',
        '6-19-7-16',
    ],
    2023: [
        '9-11-1-14',
        '2-19-6-23',
        '6-24-7-21',
    ],
}

def main():
    lines = reader(open('course.csv', 'r'))
    for course_id, _name, tag_name, term_name in lines:
        if tag_name == '':
            continue
        if tag_name not in tags:
            tag = CourseTag(name=tag_name)
            db.add(tag)
            db.flush()
            tags[tag_name] = tag
        else:
            tag = tags[tag_name]
        if term_name not in terms:
            term = Term(name=term_name)
            year, _, number = (int(x) for x in term_name.split('-'))
            start_month, start_day, end_month, end_day = (int(x) for x in term_times[year][number - 1].split('-'))
            start_year = year if number == 1 else year + 1
            end_year = year + 1
            term.start_time = datetime(start_year, start_month, start_day)
            term.end_time = datetime(end_year, end_month, end_day, 23, 59, 59)
            db.add(term)
            db.flush()
            terms[term_name] = term
        else:
            term = terms[term_name]

        course = db.get(Course, int(course_id))
        course.tag_id = tag.id
        course.term_id = term.id

    input('Press enter to continue...')
    db.commit()

if __name__ == '__main__':
    main()
