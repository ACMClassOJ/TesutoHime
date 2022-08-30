from os import environ

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from commons.models import *

engine = create_engine(environ.get('DB'))
Session = sessionmaker(bind=engine)
s = Session()
