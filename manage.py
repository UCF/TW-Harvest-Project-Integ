from flask.ext.script import Manager
from flask.ext.script import prompt_bool

from jobs.models import TWProject
from jobs.process import TWProjectPipeline

from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import database_exists

from webhook import app
from webhook import Engine as engine
from webhook import Session

manager = Manager(app)


def contains_records(session):
    try:
        return session.query(TWProject).count() >= 1
    except ProgrammingError:
        return False


def do_work(given, session):
    teamwork_pipeline = TWProjectPipeline(auto_drop=given)
    teamwork_pipeline.insert_projects(session)


@manager.command
def db_setup(force=False):
    """Setup the Teamwork database"""
    session = Session()
    if force and database_exists(engine.url) and contains_records(session):
        if not prompt_bool('Are you sure you want to drop the existing table?',
                           yes_choices=['y', 'Y', 'Yes', 'YES'],
                           no_choices=['n', 'N', 'No', 'NO']):
            return
        session.close() 
        do_work(force, session)
    else:
        do_work(force, session)

if __name__ == '__main__':
    manager.run()
