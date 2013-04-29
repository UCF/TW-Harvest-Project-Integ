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
    logging.basicConfig(filename='logfile.log', level=settings.LOG_LVL)
    handler = TeamworkHandler
    httpd = SocketServer.TCPServer(('127.0.0.1', 8181), handler)
    logging.debug('Serving at port 8181')
    # try:
    httpd.serve_forever()
    # except KeyboardInterrupt:
    #     print('Shutting down server...')
    #     httpd.shutdown()


class TeamworkHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    PROJ_NAME_PATTERN = "^[0-9]*-[A-Z]*-[0-9]* .*$"

    def __init__(self, request, client_address, server):
        """Initializes the handler.

        :param request: HTTP Request
        :param client_address: HTTP Client address
        :param server: HTTP Server
        """
        logging.debug('Initiating TeamworkHandler...')
        self.teamwork = Teamwork(settings.TEAMWORK_BASE_URL, settings.TEAMWORK_USER, settings.TEAMWORK_PASS)
        self.harvest = Harvest(settings.HARVEST_BASE_URL, settings.HARVEST_USER, settings.HARVEST_PASS)
        self.project_num = self.get_project_number()
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_POST(self):
        """Teamwork webhook API for POST
        """
        logging.debug('Retrieved webhook')
        form = cgi.FieldStorage(fp=self.rfile,
                                headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST',
                                         'CONTENT_TYPE': self.headers['Content-Type']})

        post_values = self.get_tw_post_values(form)
        event = post_values[Teamwork.EVENT]
        if event == Teamwork.PROJECT_CREATED or event == Teamwork.PROJECT_UPDATED:
            self.set_project_code(post_values[Teamwork.OBJECT_ID])
        elif event == Teamwork.COMPANY_CREATED:
            self.create_company(post_values[Teamwork.OBJECT_ID])
        elif event == Teamwork.COMPANY_UPDATED:
            self.update_company(post_values[Teamwork.OBJECT_ID])

        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def set_project_code(self, tw_project_id):
        """Prepends the project code to the project name.

        :param tw_project_id: The ID of the project
        """
        try:
            tw_project = self.teamwork.get_project(tw_project_id)
            project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]

            if not re.match(TeamworkHandler.PROJ_NAME_PATTERN, project_name):
                self.create_project(tw_project)
            else:
                self.update_project(tw_project)
        except KeyError:
            logging.error('Could not retrieve data for Project. ID: ' + tw_project_id)

    def update_project(self, tw_project):
        """Updates the project in TeamworkPM and Harvest

        :param tw_project: Teamwork project
        """
        project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
        tw_company = self.teamwork.get_company(tw_project[Teamwork.PROJECT][Teamwork.COMPANY][Teamwork.ID])
        new_company_abbr = tw_company[Teamwork.COMPANY][Teamwork.PHONE]
        company_abbr = re.sub("^[0-9]*-", "", project_name)
        company_abbr = re.sub("-[0-9]* .*$", "", company_abbr)
        new_project_name = project_name
        if new_company_abbr != company_abbr:
            new_project_name = self.update_project_name(project_name, company_abbr, tw_project[Teamwork.PROJECT][Teamwork.ID])

        self.update_project_users(new_project_name, tw_project[Teamwork.PROJECT][Teamwork.ID])

    def update_project_name(self, project_name, company_abbr, tw_project_id):
        """Update the project name in TeamworkPM and Harvest

        :param project_name: Project name
        :param company_abbr: Company abbreviation
        :param tw_project_id: TeamworkPM project ID
        """
        project_number = re.sub("^[0-9]*-[A-Z]*-", "", project_name)
        project_number = re.sub(" .*$", "", project_number)

        project_date = re.sub("-[A-Z]*-[0-9]* .*$", "", project_name)

        postfix_project_name = re.sub("^.* ", "", project_name)

        new_project_name = self.add_project_prefix(postfix_project_name, company_abbr, project_date, project_number)

        # Update Teamwork project
        self.teamwork.update_project(new_project_name, tw_project_id)

        # Update Harvest project
        h_project = self.harvest.get_project_by_name(project_name)
        if h_project:
            h_client = self.harvest.get_client_by_name(company_abbr)
            if h_client:
                self.harvest.update_project(h_project[Harvest.PROJECT][Harvest.ID],
                                            new_project_name,
                                            h_client[Harvest.CLIENT][Harvest.ID])
            else:
                logging.error('Could not update Harvest project because Client ' + company_abbr +
                              ' does not exist.')
        else:
            logging.error('Could not update Harvest project because matching Project name ' + project_name +
                          ' does not exist')

        return new_project_name

    def update_project_users(self, project_name, tw_project_id):
        """Update the project users

        :param project_name: Project name
        :param tw_project_id: TeamworkPM project ID
        """
        tw_emails = self.get_tw_project_emails(tw_project_id)
        logging.debug('Harvest assigned people: ' + str(tw_emails))

        h_project = self.harvest.get_project_by_name(project_name)
        h_emails = self.get_h_project_emails(h_project[Harvest.PROJECT][Harvest.ID])
        logging.debug('Harvest assigned people: ' + str(h_emails))

        add_people = []
        remove_people = []

        if not tw_emails:
            remove_people.extend(h_emails.keys())
        else:
            for h_id, h_email in h_emails.iteritems():
                if h_email not in tw_emails.values():
                    remove_people.append(h_id)

            for tw_email in tw_emails.values():
                for h_id, h_email in h_emails.iteritems():
                    if tw_email == h_email:
                        add_people.append(h_id)

        logging.debug('Adding people to project "' + project_name + '" ' + str(add_people))
        logging.debug('Removing people from project "' + project_name + '" ' + str(remove_people))

    def get_tw_project_emails(self, project_id):
        """Get a list of assigned emails to the given project

        :param project_id: Project ID
        :return: Assigned email list
        :rtype: list
        """
        people = self.teamwork.get_project_people(project_id)
        emails = {}
        for person in people[Teamwork.PEOPLE]:
            emails[person[Teamwork.PERSON][Teamwork.ID]] = person[Teamwork.PERSON][Teamwork.EMAIL_DASH_ADDRESS]

        return emails

    def get_h_project_emails(self, project_id):
        """Get a list of assigned emails to the given project

        :param project_id: Project ID
        :return: Assigned email list
        :rtype: list
        """
        people = self.harvest.get_project_people(project_id)
        emails = {}
        for person in people:
            emails[person[Harvest.USER_ASSIGNMENT][Harvest.USER_ID]] = person[Harvest.USER_ASSIGNMENT][Harvest.EMAIL]

        return emails


    def create_project(self, tw_project):
        """Create the project with the appropriate name

        :param tw_project: Teamwork project
        """
        tw_project_id = tw_project[Teamwork.PROJECT][Teamwork.ID]
        project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
        tw_company = self.teamwork.get_company(tw_project[Teamwork.PROJECT][Teamwork.COMPANY][Teamwork.ID])
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.PHONE]
        logging.debug('Creating new project ' + project_name + ' for client ' + company_abbr)

        # Update Teamwork project
        new_project_name = self.add_project_prefix(project_name, company_abbr)
        self.teamwork.update_project(new_project_name, tw_project_id)

        # Create Harvest project
        h_client = self.harvest.get_client_by_name(company_abbr)
        if h_client:
            self.harvest.create_project(new_project_name, h_client[Harvest.CLIENT][Harvest.ID])
        else:
            logging.error('Could not Create Harvest project because Client ' + company_abbr + ' does not exist.')

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
            self.project_num += 1
            project_number = self.project_num

        project_name = project_date + "-" + company_abbr + "-" + str(project_number) + " " + project_name
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

        projects = self.teamwork.get_projects()
        if projects:
            for project in projects[Teamwork.PROJECTS]:
                name = project[Teamwork.NAME]
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