from flask.ext.script import Manager

from jobs.models import Base

from jobs.process import TWProjectPipeline

from sqlalchemy.engine import reflection
from sqlalchemy_utils import database_exists

from webhook import app
from webhook import Engine as engine
from webhook import Session


manager = Manager(app)


def has_tables():
    inspector = reflection.Inspector.from_engine(engine)
    return any(inspector.get_table_names())

def create_tables(recreate):
    session = Session()

    if not database_exists(engine.url):
        app.logger.error('Error: manage.py:create_tables() failed, database not found.')
        print 'Error: database not found.'
        return False
  
    if has_tables():
       if recreate:
           Base.metadata.drop_all(bind=engine, checkfirst=True)
           Base.metadata.create_all(engine, checkfirst=True)
           app.logger.debug('Info: manage.py:create_tables(), tables recreated.')
           return True
       else:
           print 'tables already exist, use: "--recreate" to re-create tables'
           app.logger.debug('Info: manage.py:create_tables(), tables found, table recreation is disabled.')
           return False
    else:
        Base.metadata.create_all(engine, checkfirst=True)
        app.logger.debug('Info: manage.py:create_tables(), no tables found, tables created.')
        return True


@manager.command
def setup_db(recreate=False):                                                                                                            
    """     
    Setup the Teamwork database with records                                                                                          
    """ 
    session = Session()                                                                                                               
                                                                                                                                      
    if create_tables(recreate):                                                                                                           
        teamwork_pipeline = TWProjectPipeline()                                                                                       
        teamwork_pipeline.insert_projects(session)                                                                                    
        session.close() 
    else:
        app.logger.error('Error: manage.py:create_tables() failed, insert_projects aborted.')
        print 'insert_projects aborted due to database/table status'
                  

if __name__ == '__main__':
    manager.run()
