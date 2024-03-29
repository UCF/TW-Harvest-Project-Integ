from flask import abort
from flask import Flask
from flask import request

from logging import handlers
from logging import Formatter

from harvest import Harvest

from jobs.models import connect_to_database
from jobs.models import TWProject

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from teamwork import Teamwork

import datetime
import logging
import re
import settings
import sys

application = Flask(__name__)


log_handler = handlers.TimedRotatingFileHandler(
    settings.LOG_LOCATION,
    when=settings.LOG_ROTATE,
    interval=1,
    backupCount=3)
log_handler.setFormatter(
    Formatter(
        settings.LOG_TEXT_FMT,
        datefmt=settings.LOG_DATE_FMT))
log_handler.setLevel(settings.LOG_LVL)

application.logger.setLevel(settings.LOG_LVL)
application.logger.addHandler(log_handler)

Engine = connect_to_database()
Session = sessionmaker(bind=Engine)


@application.route("/", methods=['POST'])
def post():
    application.logger.debug('Retrieved webhook')
    teamwork_handler = TeamworkHandler()
    teamwork_handler.process_request(request)
    return "Thank you!"


class TeamworkHandler(object):

    def __init__(self):
        """
        Initializes the handler
        """
        application.logger.debug('Initiating Handlers...')
        self.teamwork = Teamwork(
            settings.TEAMWORK_BASE_URL,
            settings.TEAMWORK_USER,
            settings.TEAMWORK_PASS)
        self.harvest = Harvest(
            settings.HARVEST_BASE_URL,
            settings.HARVEST_USER,
            settings.HARVEST_PASS)
        application.logger.debug('Finished Initialization')

    def process_request(self, request):
        """
        Process Teamwork POST
        """
        application.logger.debug('Processing request...')
        post_values = request.form
        application.logger.debug('Retrieved form data')

        for key, val in post_values.items():
            application.logger.debug('key: ' + key)
            application.logger.debug('val: ' + val)

        event = post_values[Teamwork.EVENT]
        application.logger.info('Received event type: ' + event)

        if event == Teamwork.PROJECT_CREATED or event == Teamwork.PROJECT_UPDATED or event == Teamwork.PROJECT_COPIED:
            self.set_project_code(post_values[Teamwork.OBJECT_ID])
        elif event == Teamwork.COMPANY_CREATED:
            self.create_company(post_values[Teamwork.OBJECT_ID])
        elif event == Teamwork.COMPANY_UPDATED:
            self.update_company(post_values[Teamwork.OBJECT_ID])

        application.logger.debug('Finished processing request')

    def set_project_code(self, tw_project_id):
        """Prepends the project code to the project name.

        :param tw_project_id: The ID of the project
        """
        session = Session()
        try:
            tw_project = self.teamwork.get_project(tw_project_id)
            if tw_project is not None:
                project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
                q = session.query(TWProject).filter(
                    TWProject.tw_project_id == tw_project_id)
                if not session.query(q.exists()).scalar():
                    application.logger.debug('Webhook project create or copied')
                    self.create_project(tw_project)
                else:
                    application.logger.debug('Webhook project update')
                    self.update_project(tw_project)
            else:
                # may be deleted
                application.logger.warning(
                    'Teamwork project does not exist with TeamworkPM ID of ' +
                    tw_project_id)
        except KeyError:
            application.logger.exception(
                'Could not update project with TeamworkPM ID of ' +
                tw_project_id)
        finally:
            session.close()

    def update_project(self, tw_project):
        """Updates the project in TeamworkPM and Harvest

        :param tw_project: Teamwork project
        """
        project_name = tw_project[Teamwork.PROJECT][Teamwork.NAME]
        tw_company = self.teamwork.get_company(
            tw_project[
                Teamwork.PROJECT][
                Teamwork.COMPANY][
                Teamwork.ID])

        # Update project name if a valid Teamwork Company is provided otherwise
        # do nothing
        if Teamwork.COMPANY in tw_company and Teamwork.COMPANY_ABBR in tw_company[
                Teamwork.COMPANY] and tw_company[Teamwork.COMPANY][Teamwork.COMPANY_ABBR]:
            new_company_abbr = tw_company[
                Teamwork.COMPANY][
                Teamwork.COMPANY_ABBR]
            tw_project_id = tw_project[Teamwork.PROJECT][Teamwork.ID]
            if not re.match(
                    settings.TEAMWORK_PROJECT_NAME_SCHEME, project_name):
                application.logger.debug(
                    'Project name does not match schema ' +
                    project_name)
                new_project_name = self.add_project_prefix(project_name, new_company_abbr,
                                                           tw_project_id)
                # Update Teamwork project
                self.update_project_name(
                    new_project_name, new_company_abbr, tw_project_id)
                application.logger.debug(
                    'Project schema appended to name ' +
                    new_project_name)

                self.update_project_users(new_company_abbr, tw_project_id)
            else:
                new_project_name = project_name
                company_abbr = re.sub("^[0-9]{4}-", "", project_name)
                company_abbr = re.sub("-[0-9]+ .*$", "", company_abbr)
                if new_company_abbr != company_abbr:
                    new_project_name = self.update_project_name(project_name, new_company_abbr,
                                                                tw_project_id)
                    # Update Harvest project
                    project_prefix = self.get_project_prefix(
                        company_abbr, tw_project_id)
                    new_h_client = self.harvest.get_client_by_name(new_company_abbr)
                    h_project = self.harvest.get_project_by_prefix(
                        project_prefix, company_abbr)
                    if h_project:
                        h_client = self.harvest.get_client_by_name(company_abbr)
                        if h_client:
                            self.harvest.update_project(h_project[Harvest.PROJECT][Harvest.ID],
                                                        new_project_name,
                                                        new_h_client[Harvest.CLIENT][Harvest.ID])
                            self.update_project_users(new_company_abbr, tw_project_id)
                            application.logger.debug('Updating Harvest project name ' + project_name +
                                                ' to new name ' + new_project_name)
                        else:
                            application.logger.error('Could not update Harvest project because Client ' +
                                            company_abbr + ' does not exist.')
                    else:
                        application.logger.error('Could not update Harvest project because matching Project name ' +
                                        project_name + ' does not exist')
                else:
                    # Do nothing otherwise run into an infinite loop situation
                    application.logger.debug(
                        'Project company does not need to be updated ' +
                        company_abbr)

    def update_project_name(self, project_name, company_abbr, tw_project_id):
        """Update the project name in TeamworkPM and Harvest

        :param project_name: Project name
        :param company_abbr: Company abbreviation
        :param tw_project_id: TeamworkPM project ID
        """
        project_date = re.sub("-[A-Z]+-[0-9]+ .*$", "", project_name)
        postfix_project_name = re.sub(
            "^[0-9]{4}-[A-Z]+-[0-9]+ ", "", project_name)

        new_project_name = self.add_project_prefix(
            postfix_project_name, company_abbr, tw_project_id, project_date)
        application.logger.debug(
            'Updating Teamwork project name ' +
            project_name +
            ' to new name ' +
            new_project_name)

        # Update Teamwork project
        self.teamwork.update_project(new_project_name, tw_project_id)

        # Update Harvest project
        project_prefix = self.get_project_prefix(company_abbr, tw_project_id)
        h_project = self.harvest.get_project_by_prefix(
            project_prefix, company_abbr)
        if h_project:
            h_client = self.harvest.get_client_by_name(company_abbr)
            if h_client:
                self.harvest.update_project(h_project[Harvest.PROJECT][Harvest.ID],
                                            new_project_name,
                                            h_client[Harvest.CLIENT][Harvest.ID])
                application.logger.debug('Updating Harvest project name ' + project_name +
                                 ' to new name ' + new_project_name)
            else:
                application.logger.error('Could not update Harvest project because Client ' + company_abbr +
                                 ' does not exist.')
        else:
            application.logger.error('Could not update Harvest project because matching Project name ' + project_name +
                             ' does not exist')

        return new_project_name

    def update_project_users(self, company_abbr, tw_project_id):
        """Update the project users

        :param company_abbr: Company Appreviation
        :param tw_project_id: TeamworkPM project ID
        """
        tw_emails = self.get_tw_project_emails(tw_project_id)
        application.logger.debug('Teamwork assigned people: ' + str(tw_emails))

        try:
            project_prefix = self.get_project_prefix(
                company_abbr, tw_project_id)
            h_project = self.harvest.get_project_by_prefix(
                project_prefix, company_abbr)
            if h_project is not None:
                h_project_id = h_project[Harvest.PROJECT][Harvest.ID]
                h_project_name = h_project[Harvest.PROJECT][Harvest.NAME]
                h_emails = self.get_h_project_emails(h_project_id)
                application.logger.debug('Harvest assigned people: ' + str(h_emails))

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
                            if tw_email.lower() == h_email.lower():
                                match = True
                        if not match:
                            h_person = self.harvest.get_person_by_email(
                                tw_email)
                            if h_person:
                                add_people.append(
                                    h_person[
                                        Harvest.USER][
                                        Harvest.ID])
                            else:
                                application.logger.warning(
                                    'No user with this email "' + tw_email + '" exists in Harvest.')

                application.logger.debug(
                    'Adding people to project "' +
                    h_project_name +
                    '" ' +
                    str(add_people))
                for person_id in add_people:
                    self.harvest.add_user_assignment(h_project_id, person_id)
                application.logger.debug(
                    'Removing people from project "' +
                    h_project_name +
                    '" ' +
                    str(remove_people))
                for person_id in remove_people:
                    self.harvest.remove_user_assignment(
                        h_project_id, person_id)
            else:
                application.logger.error(
                    'Harvest project does not exist ' +
                    project_prefix)
        except KeyError:
            application.logger.exception(
                'Could not update project users for project prefix ' +
                project_prefix)

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
        tw_company = self.teamwork.get_company(
            tw_project[
                Teamwork.PROJECT][
                Teamwork.COMPANY][
                Teamwork.ID])

        # Create project prefix and Harvest project if a Teamwork company is
        # found
        if Teamwork.COMPANY in tw_company and Teamwork.COMPANY_ABBR in tw_company[
                Teamwork.COMPANY] and tw_company[Teamwork.COMPANY][Teamwork.COMPANY_ABBR]:
            company_abbr = tw_company[Teamwork.COMPANY][Teamwork.COMPANY_ABBR]
            application.logger.debug(
                'Creating new project ' +
                project_name +
                ' for client ' +
                company_abbr)
            # Remove Teamwork project name prefix if it exists
            if re.match(
                    settings.TEAMWORK_PROJECT_NAME_SCHEME, project_name):
                project_name = re.sub(
                    r'^[0-9]{4}-[A-Z]+-[0-9]+',
                    '',
                    project_name,
                    count=1).lstrip()

            # Update Teamwork project with new name
            new_project_name = self.add_project_prefix(
                project_name, company_abbr, tw_project_id)
            self.teamwork.update_project(new_project_name, tw_project_id)

            # Check to see if Harvest project already exists first.
            project_prefix = self.get_project_prefix(
                company_abbr, tw_project_id)
            h_project = self.harvest.get_project_by_prefix(
                project_prefix, company_abbr)
            if h_project:
                application.logger.error('Harvest project name ' + new_project_name +
                                 ' already exist. Project not created in Harvest.')
            else:
                # Create Harvest project
                h_client = self.harvest.get_client_by_name(company_abbr)
                if h_client:
                    self.harvest.create_project(
                        new_project_name, h_client[
                            Harvest.CLIENT][
                            Harvest.ID])
                    application.logger.debug(
                        'Harvest project created: ' +
                        new_project_name)
                else:
                    application.logger.error(
                        'Could not Create Harvest project because Client ' +
                        company_abbr +
                        ' does not exist.')

    def add_project_prefix(self, project_name, company_abbr,
                           tw_project_id, project_date=None, project_number=None):
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
            project_number = self.get_project_number(
                company_abbr, tw_project_id)

        project_name = project_date + "-" + company_abbr + \
            "-" + str(project_number) + " " + project_name
        return project_name

    def get_project_prefix(self, company_abbr,
                           tw_project_id, project_date=None, project_number=None):
        """Adds the project prefix to the project name

        :param project_name: Project name
        :param company_abbr: Company abbreviation
        :param project_date: Project creation date
        :param project_number: Project number
        :return: Project Prefix
        :rtype: str
        """
        if project_date is None:
            project_date = datetime.datetime.now().strftime('%y%m')

        if project_number is None:
            project_number = self.get_project_number(
                company_abbr, tw_project_id)

        project_prefix = project_date + "-" + company_abbr + \
            "-" + str(project_number)
        return project_prefix

    def get_project_number(self, company_abbr, tw_project_id):
        """Assigns a company_job_id for the Teamwork project

        :param company_abbr: Company abbreviation
        :param tw_project_id: Project ID
        :return: The assigned company_job_id for the project
        :rtype: int
        """
        session = Session()
        data = dict(tw_project_id=tw_project_id,
                    company_abbr=company_abbr)
        record = TWProject(**data)
        session.merge(record)

        try:
            session.commit()
        except SQLAlchemyError as error:
            session.rollback()
            application.logger.critical(
                'Failed to commit TW project to database: {0}'.format(
                    str(error)))
            abort(404)

        fetched = session.query(TWProject).filter(
            TWProject.tw_project_id == tw_project_id).one()
        project_number = fetched.company_job_id

        application.logger.debug(
            'Successfully committed record: {0}'.format(
                str(fetched)))
        session.close()
        return int(project_number)

    def create_company(self, company_id):
        """Create a company in Harvest

        :param company_id: Teamwork company ID
        """
        application.logger.debug(
            'Creating company with Teamwork ID ' +
            str(company_id))
        tw_company = self.teamwork.get_company(company_id)
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.COMPANY_ABBR]

        if company_abbr:
            self.harvest.create_client(company_abbr)
        else:
            application.logger.warning('Could not create company in Harvest because the abbreviation (addr one) is empty for ' +
                               tw_company[Teamwork.COMPANY][Teamwork.NAME])

    def update_company(self, company_id):
        """Update a company in Harvest

        :param company_id: Teamwork company ID
        """
        application.logger.debug(
            'Updating company with Teamwork ID ' +
            str(company_id))
        tw_company = self.teamwork.get_company(company_id)
        company_abbr = tw_company[Teamwork.COMPANY][Teamwork.COMPANY_ABBR]

        h_company = self.harvest.get_client_by_name(company_abbr)
        if not h_company and company_abbr:
            self.harvest.create_client(company_abbr)
        else:
            application.logger.warning('Company already exists in Harvest or the abbreviation (addr one) is empty ("' +
                               str(company_abbr) + '") for company ' + tw_company[Teamwork.COMPANY][Teamwork.NAME])


if __name__ == '__main__':
    application.run()
