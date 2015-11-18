from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Sequence
from sqlalchemy import Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import PrimaryKeyConstraint

import settings

Engine = create_engine(settings.DB_STRING, echo=settings.DEBUG)
Session = sessionmaker(bind=Engine)
Base = declarative_base()

class TWProject(Base):
    __table__ = Table('tw_project', Base.metadata,
        Column('tw_project_id', String(16), unique=True),
        Column('company_abbr', String(16), unique=False),
        Column('company_job_id', Integer),
        PrimaryKeyConstraint('company_job_id', 'company_abbr', name='tw_projects_pk')
    )


def dbsetup():
    """
    Setup Database (for deployment)
    """
    Session().close()
    Base.metadata.drop_all(bind=Engine, checkfirst=True)
    Base.metadata.create_all(Engine)
