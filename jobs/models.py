from sqlalchemy import Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import settings

Engine = create_engine(settings.DB_STRING, echo=settings.DEBUG)
Session = sessionmaker(bind=Engine)
Base = declarative_base()

class TWProject(Base):
    __tablename__ = 'tw_projects'

    # fields
    id = Column(Integer, Sequence('pk_seq'), primary_key=True)
    tw_project_id = Column(String)
    client_code = Column(String(3))
    client_job_id = Column(Integer)

def dbsetup():
    """Setup Database (for deployment)
    """

    Base.metadata.create_all(Engine)
