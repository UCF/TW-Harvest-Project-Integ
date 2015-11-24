from teamwork import Teamwork

from sqlalchemy import exc

from jobs.models import TWProject
from jobs.models import Session

from flask import abort
from flask import Flask

import re
import settings

app = Flask(__name__)

class AddTWProjects(object):

    VALID_PROJECT_NAME = '^[0-9]{4}-[A-Z]+-[0-9]+ .*$'

    def __init__(self):
        app.logger.debug('Initiating Handlers...')
        self.teamwork = Teamwork(settings.TEAMWORK_BASE_URL, settings.TEAMWORK_USER, settings.TEAMWORK_PASS)
        self.session = Session()
        app.logger.debug('Finished Initialization')

    def import_teamwork_projects(self):
        projects = self.teamwork.get_projects()
        if projects:
            for project in projects[Teamwork.PROJECTS]:
                name = project[Teamwork.NAME]
                tw_project_id = project[Teamwork.ID]

                if re.match(AddTWProjects.VALID_PROJECT_NAME, name) != None:
                    temp_company_abbr = re.sub('^[0-9]{4}-', '', name)
                    temp_company_abbr = re.sub('-[0-9]+ .*$', '', temp_company_abbr)

                    temp_company_job_id = re.sub('^[0-9]{4}-[A-Z]+-', '', name)
                    temp_company_job_id = re.search('^[0-9]+', temp_company_job_id).group(0)

                    self.session.add(TWProject(
                        tw_project_id=tw_project_id,
                        company_abbr=temp_company_abbr,
                        company_job_id=int(temp_company_job_id))
                    )

                    try:
                        self.session.commit()
                    except exc.SQLAlchemyError:
                            app.logger.critical('Failed to commit Teamwork project ID to database: ' + str(tw_project_id))
                            self.session.rollback()
                    finally:
                            self.session.close()
        else:
            app.logger.critical('Could not retrieve project(s) from Teamwork.')
            abort(404)
