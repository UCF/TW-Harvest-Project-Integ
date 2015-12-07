from flask.ext.script import Manager
from flask.ext.script import prompt_bool

from jobs.models import TWProject
from jobs.models import create_or_drop

from jobs.process import TWProjectPipeline

from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

from webhook import app
from webhook import Engine as engine
from webhook import Session

import time
import sys

manager = Manager(app)


def has_records(session):
    """
    Determine if the table ``tw_project`` contains rows
    """
    try:
        return session.query(TWProject).count() >= 1
    except ProgrammingError:
        return False


@manager.command
def setup_db():
    """Setup the Teamwork database"""
    session = Session()

    teamwork_pipeline = TWProjectPipeline()
    create_or_drop(engine)
    teamwork_pipeline.insert_projects(session)

    session.close()


@manager.command
def drop_table():
    """Drop Teamwork records if any"""
    session = Session()
    allowed = [['y', 'Y', 'Yes', 'YES'], ['n', 'N', 'No', 'NO']]

    if database_exists(engine.url) and has_records(session):
        if not prompt_bool('Are you sure you want to drop the existing table?',
                           yes_choices=allowed[0], no_choices=allowed[1]):
            return
        session.commit()
        create_or_drop(engine, auto_drop=True)
        session.close()
    else:
        print 'No database found.'

if __name__ == '__main__':
    manager.run()
