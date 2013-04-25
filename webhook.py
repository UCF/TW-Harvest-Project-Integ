import cgi
import datetime
from harvest import Harvest
import json
import logging
import re
import settings
import SimpleHTTPServer
import SocketServer
import sys
from teamwork import Teamwork


def main():
    handler = TeamworkHandler
    httpd = SocketServer.TCPServer(('127.0.0.1', 8181), handler)
    print("Serving at port", 8181)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down server...')
        httpd.shutdown()


class TeamworkHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    PROJ_NAME_PATTERN = "^[0-9]*-[A-Z]*-[0-9]* .*$"

    def __init__(self, request, client_address, server):
        """Initializes the handler.

        :param request: HTTP Request
        :param client_address: HTTP Client address
        :param server: HTTP Server
        """
        self.projectNum = self.get_project_number()
        self.teamwork = Teamwork(settings.TEAMWORK_BASE_URL, settings.TEAMWORK_USER, settings.TEAMWORK_PASS)
        self.harvest = Harvest(settings.HARVEST_BASE_URL, settings.HARVEST_USER, settings.HARVEST_PASS)
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_POST(self):
        """Teamwork webhook API for POST
        """
        form = cgi.FieldStorage(fp=self.rfile,
                                headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST',
                                         'CONTENT_TYPE': self.headers['Content-Type']})

        postValues = self.get_tw_post_values(form)

        if postValues[Teamwork.EVENT] == Teamwork.PROJECT_CREATED or postValues[Teamwork.EVENT] == \
                Teamwork.PROJECT_UPDATED:
            self.set_project_code(postValues[Teamwork.OBJECT_ID])

        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def set_project_code(self, project_id):
        """Prepends the project code to the project name.

        :param project_id: The ID of the project
        """
        try:
            project_data = self.harvest.get_project(project_id)
            project_name = project_data[Teamwork.PROJECT][Teamwork.NAME]

            company_data = self.harvest.get_company(project_data[Teamwork.PROJECT][Teamwork.COMPANY][Teamwork.ID])
            company_abbr = company_data[Teamwork.COMPANY][Teamwork.PHONE]

            if not re.match(TeamworkHandler.PROJ_NAME_PATTERN, project_name):
                project_name = self.add_project_prefix(project_name, company_abbr)
                self.harvest.update_project(project_name, project_id)
            else:
                # Update the project name if client has been updated
                companyCode = re.sub("^[0-9]*-", "", project_name)
                companyCode = re.sub("-[0-9]* .*$", "", companyCode)
                if company_abbr != companyCode:
                    projectNumber = re.sub("^[0-9]*-[A-Z]*-", "", project_name)
                    projectNumber = re.sub(" .*$", "", projectNumber)

                    projectDate = re.sub("-[A-Z]*-[0-9]* .*$", "", project_name)

                    project_name = re.sub("^.* ", "", project_name)

                    project_name = self.add_project_prefix(project_name, company_abbr, projectDate, projectNumber)
                    self.harvest.update_project(project_name, project_id)

        except KeyError:
            logging.error('Could not retrieve data for Project. ID: ' + project_id)

    def add_project_prefix(self, project_name, company_abbr, project_date=None, project_number=None):
        """Adds the project prefix to the project name

        :param project_name: Project name
        :param company_abbr: Company abbreviation
        :param project_date: Project creation date
        :param project_number: Project number
        :return: New project name
        :rtype: str
        """
        if project_date is None:
            project_date = datetime.datetime.now().strftime('%y%m')

        if project_number is None:
            self.projectNum += 1
            project_number = self.projectNum

        project_name = project_date + "-" + company_abbr + "-" + project_number + " " + project_name
        return project_name

    def get_tw_post_values(self, form):
        """Retrieves the POST values

        :param form: The POST form
        :return: POST values
        :rtype: dict
        """
        postValues = {}
        try:
            if form[Teamwork.EVENT].value and \
                    form[Teamwork.OBJECT_ID].value and \
                    form[Teamwork.ACCOUNT_ID].value and \
                    form[Teamwork.USER_ID].value:
                postValues[Teamwork.EVENT] = form[Teamwork.EVENT].value
                postValues[Teamwork.OBJECT_ID] = form[Teamwork.OBJECT_ID].value
                postValues[Teamwork.ACCOUNT_ID] = form[Teamwork.ACCOUNT_ID].value
                postValues[Teamwork.USER_ID] = form[Teamwork.USER_ID].value
            else:
                logging.error('Missing TW post data: ' + json.dumps(form))
        except KeyError:
            logging.error('Missing TW post data: ' + json.dumps(form))

        return postValues

    def get_project_number(self):
        """Returns the last known project number

        :return: Last project number
        :rtype: int
        """
        projectNum = 0

        projects = self.harvest.get_projects()
        if projects is not None:
            for project in projects[Harvest.PROJECTS]:
                name = project[Harvest.NAME]
                if re.match(TeamworkHandler.PROJ_NAME_PATTERN, name):
                    name = re.sub("^[0-9]*-[A-Z]*-", "", name)
                    tmp_project_str = re.search("^[0-9]", name).group(0)
                    if projectNum < int(tmp_project_str):
                        projectNum = int(tmp_project_str)
        else:
            logging.critical('Could not retrieve project to determine starting project number.')
            sys.exit(1)

        return projectNum

if __name__ == '__main__':
    main()