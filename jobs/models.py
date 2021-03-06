from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Sequence
from sqlalchemy import Table

from sqlalchemy import create_engine
from sqlalchemy import UniqueConstraint
from sqlalchemy import sql

from sqlalchemy.engine.url import URL

from sqlalchemy.ext.declarative import declarative_base

import settings

Base = declarative_base()


def default_company_job_id(context):
    return context.connection.execute(
        sql.select(
            [sql.func.ifnull(sql.func.max(TWProject.company_job_id), 99) + 1]
        ).where(
            TWProject.company_abbr == context.current_parameters[
                'company_abbr']
        )
    ).scalar()


def connect_to_database():
    """
    Creates an instance of ``Engine`` (sqlalchemy.engine.base.Engine)

    Example:
        >>> from jobs.models import *
        >>> engine = connect_to_database()
    """
    return create_engine(URL(**settings.DATABASE), echo=settings.DEBUG)


class TWProject(Base):

    __table__ = Table('tw_project', Base.metadata,
                      Column('tw_project_id',
                             String(16),
                             primary_key=True,
                             nullable=False),
                      Column('company_abbr', String(16), unique=False),
                      Column('company_job_id',
                             Integer,
                             default=default_company_job_id,
                             onupdate=default_company_job_id),
                      UniqueConstraint('company_job_id',
                                       'company_abbr',
                                       name='tw_project_uk'))

    def __repr__(self):
        return 'tw_project_id = {0}, company_abbr = {1}, company_job_id = {2}'.format(
            self.tw_project_id, self.company_abbr, self.company_job_id)
