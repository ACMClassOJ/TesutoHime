from commons.models import Course, Term, CourseTag
from scripts.db.env import Session
from sqlalchemy import select

name = input('Course name? ')
description = input('Course description? ')

term_name = input('Term name? ')
tag = input('Course tag? ')

course = Course(name=name, description=description)

with Session() as db:
	if len(term_name) > 0:
		term = db.scalar(select(Term).where(Term.name == term_name))
		if term is None:
			print('Term not found.')
			exit()
		course.term_id = term.id
	if len(tag) > 0:
		tag = db.scalar(select(CourseTag).where(CourseTag.name == tag))
		if tag is None:
			print('Tag not found.')
			exit()
		course.tag_id = tag.id
	db.add(course)
	db.commit()

