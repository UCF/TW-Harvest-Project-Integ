import cgi
import datetime
from harvest import Harvest
import json
import logging
import logging.handlers
import re
import settings
import SimpleHTTPServer
import SocketServer
import sys
from teamwork import Teamwork


def main():
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LVL)
    log_handler = logging.handlers.TimedRotatingFileHandler('logfile.log', when='D', interval=1, backupCount=3)
    logger.addHandler(log_handler)

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
                logging.debug('Webhook project create')
                self.create_project(tw_project)
            else:
                logging.debug('Webhook project update')
                self.update_project(tw_project)
        except KeyError:
            logging.exception('Could no update project with TeamworkPM ID of ' + tw_project_id)

    def update_project(self, tw_project):
        """Updates the project in TeamworkPM and Harvest

        :param tw_project: Teamwork project
        """
        project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
        tw_company = self.teamwork.get_company(tw_project[Teamwork.PROJECT][Teamwork.COMPANY][Teamwork.ID])
        new_company_abbr = tw_company[Teamwork.COMPANY][Teamwork.ADDRESS_ONE]
        company_abbr = re.sub("^[0-9]*-", "", project_name)
        company_abbr = re.sub("-[0-9]* .*$", "", company_abbr)
        new_project_name = project_name
        if new_company_abbr != company_abbr:
            new_project_name = self.update_project_name(project_name, new_company_abbr,
                                                        tw_project[Teamwork.PROJECT][Teamwork.ID])
        else:
            logging.debug('Project name does not need to be updated ' + project_name)

        self.update_project_users(new_project_name, tw_project[Teamwork.PROJECT][Teamwork.ID])

    def update_project_name(self, project_name, company_abbr, tw_project_id):
        """Update the project name in TeamworkPM and Harvest

        :param project_name: Project name
        :param company_abbr: Company abbreviation
        :param tw_project_id: TeamworkPM project ID
        """
        project_number = re.sub("^[0-9]*-[A-Z]*-", "", project_name)
        project_number = re.search("^[0-9]", project_number).group(0)

        project_date = re.sub("-[A-Z]*-[0-9]* .*$", "", project_name)

        postfix_project_name = re.sub("^[0-9]*-[A-Z]*-[0-9]* ", "", project_name)

        new_project_name = self.add_project_prefix(postfix_project_name, company_abbr, project_date, project_number)
        logging.debug('Updating project name ' + new_project_name + ' for client ' + company_abbr)

        # Update Teamwork project
        self.teamwork.update_project(new_project_name, tw_project_id)

        # Update Harvest project
        h_project = self.get_h_project_by_number(project_number)
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
        logging.debug('Teamwork assigned people: ' + str(tw_emails))

        h_project = self.harvest.get_project_by_name(project_name)
        h_project_id = h_project[Harvest.PROJECT][Harvest.ID]
        h_emails = self.get_h_project_emails(h_project_id)
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
                match = False
                for h_email in h_emails.values():
                    if tw_email == h_email:
                        match = True
                if not match:
                    h_person = self.harvest.get_person_by_email(tw_email)
                    if h_person:
                        add_people.append(h_person[Harvest.USER][Harvest.ID])
                    else:
                        logging.warning('No user with this email "' + tw_email + '" exists in Harvest.')

        logging.debug('Adding people to project "' + project_name + '" ' + str(add_people))
        for person_id in add_people:
            self.harvest.add_user_assignment(h_project_id, person_id)
        logging.debug('Removing people from project "' + project_name + '" ' + str(remove_people))
        for person_id in remove_people:
            self.harvest.remove_user_assignment(h_project_id, person_id)

    def get_h_project_by_number(self, project_number):
        """Retrieves the project by the project number

        :param project_number: Project number
        :return: Project
        :rtype: dict
        """
        projects = self.harvest.get_projects()
        for project in projects:
            h_project_number = re.sub("^[0-9]*-[A-Z]*-", "", project[Harvest.PROJECT][Harvest.NAME])
            h_project_number = re.search("^[0-9]", h_project_number).group(0)

            if h_project_number == str(project_number):
                return project

        return None

    def get_tw_project_emails(self, project_id):
        """Get a list of assigned emails to the given project

        :param project_id: Project ID
        :return: Assigned email list
        :rtype: list
        """
        people = self.teamwork.get_project_people(project_id)
        emails = {}
        for person in people[Teamwork.PEOPLE]:
            emails[person[Teamwork.ID]] = person[Teamwork.EMAIL_DASH_ADDRESS]

        return emails

    def get_h_project_emails(self, project_id):
        """Get a list of assigned emails to the given project

        :param project_id: Project ID
        :return: Assigned email list
        :rtype: list
        """
        people = self.harvest.get_project_people(project_id)
        emails = {}
        for assigned_user in people:
            user_id = assigned_user[Harvest.USER_ASSIGNMENT][Harvest.USER_ID]
            person = self.harvest.get_person(user_id)
            emails[user_id] = person[Harvest.USER][Harvest.EMAIL]

        return emails

    def create_project(self, tw_project):
        """Create the project with the appropriate name

        :param tw_project: Teamwork project
        """
        tw_project_id = tw_project[Teamwork.PROJECT][Teamwork.ID]
        project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
        tw_company = self.teamwork.get_company(tw_project[Teamwork.PROJECT][Teamwork.COMPANY][Teamwork.ID])
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.ADDRESS_ONE]
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
            project_number = self.get_project_number(company_abbr)
            project_number += 1

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

    def get_project_number(self, company_abbr):
        """Returns the last known project number

        :return: Last project number
        :rtype: int
        """
        project_num = 0

        projects = self.teamwork.get_projects()
        if projects:
            for project in projects[Teamwork.PROJECTS]:
                name = project[Teamwork.NAME]
                if re.match(TeamworkHandler.PROJ_NAME_PATTERN, name):
                    tmp_company_abbr = re.sub("^[0-9]*-", '', name)
                    tmp_company_abbr = re.sub("-[0-9]* .*$", "", tmp_company_abbr)

                    tmp_project_num_str = re.sub("^[0-9]*-[A-Z]*-", "", name)
                    tmp_project_num_str = re.search("^[0-9]*", tmp_project_num_str).group(0)
                    if project_num < int(tmp_project_num_str) and tmp_company_abbr == company_abbr:
                        project_num = int(tmp_project_num_str)
        else:
            logging.critical('Could not retrieve project to determine starting project number.')
            sys.exit(1)
        logging.debug('Most recent project number: ' + str(project_num))
        return project_num

    def create_company(self, company_id):
        """Create a company in Harvest

        :param company_id: Teamwork company ID
        """
        logging.debug('Creating company with Teamwork ID ' + str(company_id))
        tw_company = self.teamwork.get_company(company_id)
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.ADDRESS_ONE]

        if company_abbr:
            self.harvest.create_client(company_abbr)
        else:
            logging.warning('Could not create company in Harvest because the abbreviation (addr one) is empty for ' +
                            tw_company[Teamwork.COMPANY][Teamwork.NAME])

    def update_company(self, company_id):
        """Update a company in Harvest

        :param company_id: Teamwork company ID
        """
        logging.debug('Updating company with Teamwork ID ' + str(company_id))
        tw_company = self.teamwork.get_company(company_id)
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.ADDRESS_ONE]

        h_company = self.harvest.get_client_by_name(company_abbr)
        if not h_company and company_abbr:
            self.harvest.create_client(company_abbr)
        else:
            logging.warning('Company already exists in Harvest or the abbreviation (addr one) is empty ("' +
                            str(company_abbr) + '") for company ' + tw_company[Teamwork.COMPANY][Teamwork.NAME])

if __name__ == '__main__':
    main()