from flask.ext.script import Manager

from jobs.models import Base

from jobs.process import TWProjectPipeline

from sqlalchemy.engine import reflection
from sqlalchemy_utils import database_exists

from webhook import app
from webhook import Engine as engine
from webhook import Session

import sys

manager = Manager(app)


def has_tables():
    inspector = reflection.Inspector.from_engine(engine)
    return any(inspector.get_table_names())


def create_tables(recreate):
    session = Session()

    if not database_exists(engine.url):
        app.logger.error(
            'manage.py:create_tables() failed, database not found.')
        raise Exception('database not found')

    if has_tables():
        if recreate:
            sys.stdout.write('re-creating Teamwork tables...' + '\n')
            Base.metadata.drop_all(bind=engine, checkfirst=True)
            Base.metadata.create_all(engine, checkfirst=True)
            app.logger.debug(
                'manage.py:create_tables(), tables re-created.')
            return
        else:
            app.logger.warning(
                'manage.py:create_tables(), tables found, table recreation is disabled.')
            raise Exception(
                'tables already exist, use: "--recreate" to re-create tables' + '\n')
    else:
        Base.metadata.create_all(engine, checkfirst=True)
        sys.stdout.write('creating tables' + '\n')
        app.logger.debug(
            'manage.py:create_tables(), no tables found, tables created.')


@manager.command
def setup_db(recreate=False):
    """
    Setup the Teamwork database with records
    """
    session = Session()
    try:
        create_tables(recreate)
        teamwork_pipeline = TWProjectPipeline()
        teamwork_pipeline.insert_projects(session)
        session.close()
    except Exception as error:
        print 'Error: {0}'.format(error)
        app.logger.warning(
            'manage.py:create_tables() failed, insert_projects aborted.')
        session.close()

if __name__ == '__main__':
    manager.run()
