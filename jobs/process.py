from flask import abort
from flask import Flask

from jobs.models import TWProject
from jobs.models import create_database

from sqlalchemy.exc import SQLAlchemyError

from teamwork import Teamwork

from webhook import app
from webhook import Engine as engine 

import re
import settings


class TWProjectPipeline(object):

    VALID_PROJECT_NAME = '^[0-9]{4}-[A-Z]+-[0-9]+ .*$'

    def __init__(self, auto_drop=False):
        app.logger.debug('Kicking up the processor...')
        self.teamwork = Teamwork(settings.TEAMWORK_BASE_URL,
                                 settings.TEAMWORK_USER,
                                 settings.TEAMWORK_PASS)
        create_database(engine, auto_drop=auto_drop)
        app.logger.debug('Ready to process project(s)')

    def process_project(self, data, session):
        a_project = TWProject(**data)
        try:
            session.add(a_project)
            session.commit()
        except SQLAlchemyError:
            app.logger.critical('Failed to commit Teamwork project ID to database: {0}'
                                .format(str(a_project.tw_project_id)))
            session.rollback()
        finally:
            session.close()

    def insert_projects(self, session):
        projects = self.teamwork.get_projects()
        if projects:
            for project in projects[Teamwork.PROJECTS]:
                name = project[Teamwork.NAME]
                tw_project_id = project[Teamwork.ID]

                if re.match(TWProjectPipeline.VALID_PROJECT_NAME,
                            name) != None:
                    temp_company_abbr = re.sub('^[0-9]{4}-', '', name)
                    temp_company_abbr = re.sub(
                        '-[0-9]+ .*$', '', temp_company_abbr)

                    temp_company_job_id = re.sub('^[0-9]{4}-[A-Z]+-', '', name)
                    temp_company_job_id = re.search(
                        '^[0-9]+', temp_company_job_id).group(0)

                    data = dict(tw_project_id=tw_project_id,
                                company_abbr=temp_company_abbr,
                                company_job_id=int(temp_company_job_id))

                    self.process_project(data, session)
        else:
            app.logger.critical('Could not retrieve project(s) from Teamwork.')
            abort(404)
