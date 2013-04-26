from requests.auth import HTTPBasicAuth
import httplib
import json
import logging
import requests


class Teamwork(object):

    # Webhook strings
    PROJECT_CREATED = 'PROJECT.CREATED'
    PROJECT_UPDATED = 'PROJECT.UPDATED'
    COMPANY_CREATED = 'COMPANY.CREATED'
    COMPANY_UPDATED = 'COMPANY.UPDATED'

    EVENT = 'event'
    OBJECT_ID = 'objectId'
    ACCOUNT_ID = 'accountId'
    USER_ID = 'userId'

    # API strings
    REQ_TYPE = '.json'

    ID = 'id'
    NAME = 'name'
    LOCATION = 'location'

    PROJECTS_URL = '/projects'
    PROJECT = 'project'
    PROJECTS = 'projects'

    COMPANIES_URL = '/companies'
    COMPANY = 'company'
    PHONE = 'phone'
    ADDRESS_ONE = 'address_one'

    PEOPLE = 'people'
    PERSON = 'person'
    EMAIL_DASH_ADDRESS = 'email-address'

    def __init__(self, base_url, username, password):
        """Initializes the handler.

        :param base_url: base URL to make requests against
        :param username: API Username
        :param pass: API Password
        """
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {'Content-Type': 'application/json'}

    def get_projects(self):
        """Retrieves projects based on the ID

        :return: The project
        :rtype: dict
        """
        return self.get_request(self.base_url + Teamwork.PROJECTS_URL + Teamwork.REQ_TYPE)

    def get_project(self, id):
        """Retrieves project based on the ID

        :param id: Project ID
        :return: The project
        :rtype: dict
        """
        return self.get_request(self.base_url + Teamwork.PROJECTS_URL + '/' + id + Teamwork.REQ_TYPE)

    def update_project(self, project_name, id):
        """Updates the project name based on the ID

        :param project_name: New project name
        :param id: Project ID
        """
        data = {Teamwork.PROJECT: {Teamwork.NAME: project_name}}
        return self.put_request(self.base_url + Teamwork.PROJECTS_URL + '/' + id + Teamwork.REQ_TYPE, data)

    def get_company(self, id):
        """Retrieves the company based on the ID

        :param id: Company ID
        :return: The company
        :rtype: dict
        """
        return self.get_request(self.base_url + Teamwork.COMPANIES_URL + '/' + id + Teamwork.REQ_TYPE)

    def get_project_people(self, project_id):
        """Get people assigned to a project

        :param project_id: Project ID
        :return: People assigned to the project
        :rtype: dict
        """
        return self.get_request(self.base_url + Teamwork.PROJECTS_URL + '/' + project_id +
                                '/' + Teamwork.PEOPLE + Teamwork.REQ_TYPE)

    def get_request(self, url):
        """Performs a GET request with the given url

        :param url: URL to make the request against
        :return: Response
        :rtype: dict
        """
        req = requests.get(url=url,
                           auth=self.auth,
                           headers=self.headers)

        if req.status_code != httplib.OK:
            logging.error('Could not make GET request using url: ' + url +
                          ' Response headers: ' + str(req.headers))
            return None

        return req.json()

    def post_request(self, url, data):
        """Performs a POST request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: Project ID
        :rtype: str
        """
        req = requests.post(url=url,
                            auth=self.auth,
                            data=json.dumps(data),
                            headers=self.headers)

        if req.status_code != httplib.CREATED:
            logging.error("Could not make POST request using url: " + url + " with data: " + json.dumps(data) +
                          " Response header: " + str(req.headers))
            return None

        return req.headers[Teamwork.ID]

    def put_request(self, url, data):
        """Performs a PUT request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: headers
        :rtype: str
        """
        req = requests.put(url=url,
                           auth=self.auth,
                           data=json.dumps(data),
                           headers=self.headers)

        if req.status_code != httplib.OK:
            logging.error("Could not make PUT request using url: " + url + " with data: " + json.dumps(data) +
                          " Response headers: " + str(req.headers))
            return None

        return req.headers