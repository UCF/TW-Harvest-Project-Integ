from harvest import Harvest
import settings
from teamwork import Teamwork
import time


def main():
    time_entries = TimeImport()


class TimeImport():

    def __init__(self):
        self.teamwork = Teamwork(
            settings.TEAMWORK_BASE_URL,
            settings.TEAMWORK_USER,
            settings.TEAMWORK_PASS)
        self.harvest = Harvest(
            settings.HARVEST_BASE_URL,
            settings.HARVEST_USER,
            settings.HARVEST_PASS)

        updated_projects = self.harvest.get_todays_updated_projects()

        for project in updated_projects:
            h_project_id = project[Harvest.PROJECT][Harvest.ID]
            time_entries = self.harvest.get_todays_proj_time_entries(
                h_project_id)

            project_name = project[Harvest.PROJECT][Harvest.NAME]
            tw_project = self.teamwork.get_project_by_name(project_name)
            tw_project_id = tw_project[Teamwork.ID]
            tw_project_emails = self.get_tw_project_emails(tw_project_id)

            for entry in time_entries:
                h_user_id = entry[Harvest.DAY_ENTRY][Harvest.USER_ID]
                h_user = self.harvest.get_person(h_user_id)
                user_email = h_user[Harvest.USER][Harvest.EMAIL]

                for tw_id, tw_email in tw_project_emails.iteritems():
                    if user_email.lower() == tw_email.lower():
                        self.teamwork.add_time_entry(
                            tw_project_id, tw_id, entry[
                                Harvest.DAY_ENTRY][
                                Harvest.HOURS], True)
                        break

                time.sleep(1)

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


if __name__ == '__main__':
    main()
