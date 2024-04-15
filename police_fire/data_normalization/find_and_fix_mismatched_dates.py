# occasionally, the incident_reported_date and the incident_date will be significantly different
# this is because ChatGPT sometimes assumes the date mentioned in the article is for the current year instead of the year the article was published
# this script will find and fix those discrepancies. we'll also keep a csv of the dates that we checked are correct to avoid checking them again

import os
import sys
import datetime
from sqlalchemy import func
from tqdm import tqdm

from database import get_database_session, Incident


def find_and_fix_mismatched_dates(DBsession, already_checked_incidents):
    incidents = DBsession.query(Incident).all()
    count = 0
    for incident in tqdm(incidents):
        if incident.incident_date and incident.incident_reported_date:
            incident_date = incident.incident_date
            incident_reported_date = incident.incident_reported_date
            if incident_date.year != incident_reported_date.year:
                if incident.id in already_checked_incidents:
                    continue
                print('\nIncident ID: ', incident.id)
                print('Incident Date: ', incident_date)
                print('Incident Reported Date: ', incident_reported_date)
                print('Incident Details: ', incident.details)
                print('---')
                count += 1
                replace_answer = input('Replace incident_date with incident_reported_date? (y/n): \n> ')
                if replace_answer == 'y':
                    incident.incident_date = incident_reported_date
                    DBsession.commit()
                else:
                    # add the incident id to the checked_dates.csv file
                    with open('checked_dates.csv', 'a') as f:
                        f.write(f'{incident.id}\n')
                    continue

    print(count)


def main():
    if os.path.exists('checked_dates.csv'):
        with open('checked_dates.csv', 'r') as f:
            already_checked_incidents = [int(i.strip()) for i in f.readlines()[1:]]
    DBsession, engine = get_database_session(environment='prod')
    find_and_fix_mismatched_dates(DBsession, already_checked_incidents)


if __name__ == '__main__':
    main()
