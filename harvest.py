import httplib
import json
from requests.auth import HTTPBasicAuth
import logging
import requests


class Harvest(object):

    ID = 'id'
    NAME = 'name'
    LOCATION = 'location'

    PROJECTS_URL = '/projects'
    PROJECT = 'project'
    PROJECTS = 'projects'

    CLIENTS_URL = '/clients'
    CLIENT = 'client'
    CLIENTS = 'clients'
    CLIENT_ID = 'client_id'

    USER_ASSIGNMENTS_URL = '/user_assignments'

    def __init__(self, base_url, username, password):
        """Initializes the handler.

        :param base_url: base URL to make requests against
        :param username: API Username
        :param pass: API Password
        """
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}

    def get_clients(self):
        """Retrieves all the clients

        :return: dictionary of clients
        :rtype: dict
        """
        return self.get_request(self.base_url + Harvest.CLIENTS_URL)

    def get_client_by_name(self, name):
        """Retrieves client by name

        :param name: name of client
        :return: client
        :rtype: dict
        """
        clients = self.get_clients()
        for client in clients:
            if client[Harvest.CLIENT][Harvest.NAME] == name:
                return client
        return None

    def create_client(self, name):
        """Creates a client

        :param name: Client name
        :return: Client ID
        :rtype: str
        """
        data = {Harvest.CLIENT: {Harvest.NAME: name}}
        location = self.post_request(self.base_url + Harvest.CLIENTS_URL, data)

        if location is None:
            return location
        return location.replace(Harvest.CLIENTS_URL + '/', '')

    def update_client(self, id, name):
        """Updates a client based on the client ID

        :param id: Client ID
        :param name: the new client's name
        :return: Client ID
        :rtype: str
        """
        data = {Harvest.CLIENT: {Harvest.NAME: name}}
        location = self.put_request(self.base_url + Harvest.CLIENT_URL + '/' + id, data)

        if location is None:
            return location
        return location.replace(Harvest.CLIENTS_URL + '/', '')

    def get_projects(self):
        """Retrieves all projects

        :return: Projects
        :rtype: dict
        """
        return self.get_request(self.base_url + Harvest.PROJECTS_URL)

    def get_project(self, project_id):
        """Retrieves project by ID

        :param project_id: ID of the project
        :return: Projects
        :rtype: dict
        """
        return self.get_request(self.base_url + Harvest.PROJECTS_URL + '/' + project_id)

    def get_project_by_name(self, name):
        """Retrieves project by name

        :param name: Name of project
        :return: Project
        :rtype: dict
        """
        projects = self.get_projects()
        for project in projects:
            if project[Harvest.PROJECT][Harvest.NAME] == name:
                return project
        return None

    def update_project(self, project_id, name, client_id):
        """Updates a project using the project ID

        :param project_id: Project ID
        :param name: Name of project
        :param client_id: ID of client to assign to project
        :return: Project ID
        :rtype: str
        """
        data = {Harvest.PROJECT: {Harvest.NAME: name, Harvest.CLIENT_ID: client_id}}
        location = self.put_request(self.base_url + Harvest.PROJECTS_URL + '/' + project_id, data)

        if location is None:
            return location
        return location.replace(Harvest.PROJECTS_URL + '/', '')

    def create_project(self, name, client_id):
        """Creates a project using the name and client ID

        :param name: Name of project
        :param client_id: ID of client to assign to project
        :return: Project ID
        :rtype: str
        """
        data = {Harvest.PROJECT: {Harvest.NAME: name, Harvest.CLIENT_ID: client_id}}
        location = self.post_request(self.base_url + Harvest.PROJECTS_URL, data)

        if location is None:
            return location
        return location.replace(Harvest.PROJECTS_URL + '/', '')

    def user_assignment(self, project_id, user_id):
        """Assigns a user to a project

        :param project_id: Project ID
        :param user_id: User ID to assign to the project
        :return: Assignment location
        :rtype: str
        """
        return self.post_request(self.base_url + Harvest.PROJECTS_URL + '/' + project_id +
                                 Harvest.USER_ASSIGNMENTS_URL + '/' + user_id)

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
                          '\nResponse headers: ' + str(req.headers))
            return None

        return req.json()

    def post_request(self, url, data):
        """Performs a POST request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: Response location
        :rtype: str
        """
        req = requests.post(url=url,
                            auth=self.auth,
                            data=json.dumps(data),
                            headers=self.headers)

        if req.status_code != httplib.CREATED:
            logging.error("Could not make POST request using url: " + url + " with data: " + json.dumps(data) +
                          "\nResponse header: " + str(req.headers))
            return None

        return req.headers[Harvest.LOCATION]

    def put_request(self, url, data):
        """Performs a PUT request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: Response location
        :rtype: str
        """
        req = requests.put(url=url,
                           auth=self.auth,
                           data=json.dumps(data),
                           headers=self.headers)

        if req.status_code != httplib.OK:
            logging.error("Could not make PUT request using url: " + url + " with data: " + json.dumps(data) +
                          "\nResponse headers: " + str(req.headers))
            return None

        return req.headers[Harvest.LOCATION]