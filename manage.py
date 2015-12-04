from flask.ext.script import Manager
from flask.ext.script import prompt_bool

from jobs.models import TWProject
from jobs.process import TWProjectPipeline

from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

from webhook import app
from webhook import Engine as engine
from webhook import Session

import time

manager = Manager(app)


def has_records(session):
    try:
        return session.query(TWProject).count() >= 1
    except ProgrammingError:
        return False


def run_setup(given, session):
    teamwork_pipeline = TWProjectPipeline(auto_drop=given)
    teamwork_pipeline.insert_projects(session)


@manager.command
def db_setup(force=False):
    """Setup the Teamwork database"""
    session = Session()
    allowed = [['y', 'Y', 'Yes', 'YES'], ['n', 'N', 'No', 'NO']]
    if force and database_exists(engine.url) and has_records(session):
        if not prompt_bool('Are you sure you want to drop the existing table?',
                           yes_choices=allowed[0], no_choices=allowed[1]):
            return
        session.commit()
        print '...dropping DB...'
        time.sleep(1)
        run_setup(force, session)
        session.close()
    else:
        print '...creating DB...'
        time.sleep(1)
        run_setup(force, session)
        session.close()

if __name__ == '__main__':
    manager.run()
