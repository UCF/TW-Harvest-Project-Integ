import SimpleHTTPServer
import SocketServer
import cgi
import json
import requests
import settings
import datetime
import re


def main():
    handler = TeamworkHandler
    httpd = SocketServer.TCPServer(('127.0.0.1', 8181), handler)
    print("Serving at port", 8181)
    # try:
    httpd.serve_forever()
    # except KeyboardInterrupt:
    # 	print('Shutting down server...')
    # 	httpd.shutdown()


class TeamworkHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    class TeamworkException(Exception):
        pass

    class InsufficientPostDataException(TeamworkException):
        pass

    class UpdateException(TeamworkException):
        pass

    class GetException(TeamworkException):
        pass

    def __init__(self, request, client_address, server):
        """Initializes the handler.

        :param request: HTTP Request
        :param client_address: HTTP Client address
        :param server: HTTP Server
        """
        self.projectNum = self.getProjectNumber()
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_POST(self):
        """Teamwork webhook API for POST
        """
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']})

        postValues = self.getPostValues(form)

        if postValues[settings.EVENT] == settings.PROJECT_CREATED or postValues[settings.EVENT] == \
                settings.PROJECT_UPDATED:
            self.setProjectCode(postValues[settings.OBJECT_ID])

        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def setProjectCode(self, id):
        """Prepends the project code to the project name.

        :param id: The ID of the project
        """
        try:
            projectData = self.getProject(id)
            projectName = projectData[settings.PROJECT][settings.NAME]

            companyData = self.getCompany(projectData[settings.PROJECT][settings.COMPANY][settings.ID])
            companyAbbr = companyData[settings.COMPANY][settings.PHONE]

            if not re.match(settings.PROJ_NAME_PATTERN, projectName):
                projectName = self.addProjectPrefix(projectName, companyAbbr)
                self.updateProject(projectName, id)
            else:
                # Update the project name if client has been updated
                companyCode = re.sub("^[0-9]*-", "", projectName)
                companyCode = re.sub("-[0-9]* .*$", "", companyCode)
                if companyAbbr != companyCode:
                    projectNumber = re.sub("^[0-9]*-[A-Z]*-", "", projectName)
                    projectNumber = re.sub(" .*$", "", projectNumber)

                    projectDate = re.sub("-[A-Z]*-[0-9]* .*$", "", projectName)

                    projectName = re.sub("^.* ", "", projectName)

                    projectName = self.addProjectPrefix(projectName, companyAbbr, projectDate, projectNumber)
                    self.updateProject(projectName, id)

        except KeyError:
            raise self.UpdateException('Could not retrieve data for Project. ID: ' + id)

    def addProjectPrefix(self, projectName, companyAbbr, projectDate=None, projectNumber=None):
        """Adds the project prefix to the project name

        :param projectName: Project name
        :param companyAbbr: Company abbreviation
        :param projectDate: Project creation date
        :param projectNumber: Project number
        :return: New project name
        :rtype: str
        """
        if projectDate is None:
            projectDate = datetime.datetime.now().strftime('%y%m')

        if projectNumber is None:
            self.projectNum += 1
            projectNumber = self.projectNum

        projectName = projectDate + "-" + companyAbbr + "-" + projectNumber + " " + projectName
        return projectName

    def getPostValues(self, form):
        """Retrieves the POST values

        :author:
        :param form: The POST form
        :return: Dictionary of the POST values
        :rtype: Dictionary
        """
        postValues = {}
        try:
            if form[settings.EVENT].value and \
                    form[settings.OBJECT_ID].value and \
                    form[settings.ACCOUNT_ID].value and \
                    form[settings.USER_ID].value:
                postValues[settings.EVENT] = form[settings.EVENT].value
                postValues[settings.OBJECT_ID] = form[settings.OBJECT_ID].value
                postValues[settings.ACCOUNT_ID] = form[settings.ACCOUNT_ID].value
                postValues[settings.USER_ID] = form[settings.USER_ID].value
            else:
                raise self.InsufficientPostDataException('Missing post data.')
        except KeyError:
            raise self.InsufficientPostDataException('Missing post data.')

        return postValues

    def getProjectNumber(self):
        """Returns the last known project number

        :return: Last project number
        :rtype: int
        :raise GetException: Failed to get project list
        """
        projectNum = 0

        req = requests.get(settings.TEAMWORK_BASE_URL + settings.PROJECTS + settings.REQ_TYPE,
                           auth=(settings.TEAMWORK_USER, settings.TEAMWORK_PASS))

        if req.status_code == settings.SUCCESS_CODE:
            projects = req.json()
            for project in projects[settings.PROJECTS]:
                name = project[settings.NAME]
                if re.match(settings.PROJ_NAME_PATTERN, name):
                    name = re.sub("^[0-9]*-[A-Z]*-", "", name)
                    tempProjectStr = re.search("^[0-9]", name).group(0)
                    try:
                        if projectNum < int(tempProjectStr):
                            projectNum = int(tempProjectStr)
                    except ValueError:
                        pass
        else:
            raise self.GetException('Could not retrieve initial project information.')

        return projectNum

    def getProject(self, id):
        """Retrieves a JSON representation of the project based on the ID

        :param id: Project ID
        :return: JSON of the project data
        :rtype: JSON
        :raise GetException: If the project could not be retrieved
        """
        req = requests.get(settings.TEAMWORK_BASE_URL + settings.URL_PROJECTS + id + settings.REQ_TYPE,
                           auth=(settings.TEAMWORK_USER, settings.TEAMWORK_PASS))

        if req.status_code != settings.SUCCESS_CODE:
            raise self.GetException('Could not retrieve data for Project ID:' + id)

        return req.json()

    def getCompany(self, id):
        """Retrieves a JSON representation of the company based on the ID

        :param id: Company ID
        :return: JSON of the company data
        :rtype: JSON
        :raise: If the company could not be retrieved
        """
        req = requests.get(settings.TEAMWORK_BASE_URL + settings.URL_COMPANY + id + settings.REQ_TYPE,
                           auth=(settings.TEAMWORK_USER, settings.TEAMWORK_PASS))

        if req.status_code != settings.SUCCESS_CODE:
            raise self.GetException('Could not retrieve data for Company ID:' + id)
        return req.json()

    def updateProject(self, projectName, id):
        """Sends a project update request to Teamwork

        :param projectName: New project name
        :param id: Project ID
        :raise UpdateException: If the project name could not be updated
        """
        payload = {settings.PROJECT: {settings.NAME: projectName}}
        headers = {settings.POST_CONTENT_HEADER: settings.POST_CONTENT_TYPE}
        req = requests.put(settings.TEAMWORK_BASE_URL + settings.URL_PROJECTS + id + settings.REQ_TYPE,
                           auth=(settings.TEAMWORK_USER, settings.TEAMWORK_PASS),
                           data=json.dumps(payload),
                           headers=headers)

        if req.status_code != settings.SUCCESS_CODE:
            self.projectNum -= 1
            raise self.UpdateException('Could not update the Project name. ID:' + id)


if __name__ == '__main__':
    main()