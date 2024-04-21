# occasionally, the incident_reported_date and the incident_date will be significantly different
# this is because ChatGPT sometimes assumes the date mentioned in the article is for the current year instead of the year the article was published
# this script will find and fix those discrepancies. we'll also keep a csv of the dates that we checked are correct to avoid checking them again

import os

from tqdm import tqdm

from database import get_database_session, Incident


def get_replace_date_input(incident, DBsession):
    print('13')
    replace_answer = input('Replace incident_date with incident_reported_date or use a custom date? (y/n/c): \n> ')
    if replace_answer == 'y':
        incident.incident_date = incident.incident_reported_date
        DBsession.commit()
        with open('checked_dates.csv', 'a') as f:
            f.write(f'{incident.id}\n')
    elif replace_answer == 'c':
        custom_date = input('Enter custom date (YYYY-MM-DD): \n> ')
        incident.incident_date = custom_date
        DBsession.commit()
        with open('checked_dates.csv', 'a') as f:
            f.write(f'{incident.id}\n')
    else:
        # add the incident id to the checked_dates.csv file
        with open('checked_dates.csv', 'a') as f:
            f.write(f'{incident.id}\n')

    return


def find_mismatched_dates(DBsession, already_checked_incidents):
    incidents = DBsession.query(Incident).all()
    mismatched_dates = []
    for incident in tqdm(incidents):
        if incident.incident_date and incident.incident_reported_date:
            incident_date = incident.incident_date
            incident_reported_date = incident.incident_reported_date
            # check for cases when years are different
            if incident_date.year != incident_reported_date.year:
                if incident.id in already_checked_incidents:
                    continue
                else:
                    mismatched_dates.append(incident)
            # check for cases when incident_date is after incident_reported_date
            elif incident_date > incident_reported_date:
                if incident.id in already_checked_incidents:
                    continue
                else:
                    mismatched_dates.append(incident)

    return mismatched_dates


def fix_mismatched_dates(incident, DBsession):
    print('\nIncident ID: ', incident.id)
    print('Incident Date: ', incident.incident_date)
    print('Incident Reported Date: ', incident.incident_reported_date)
    print('Incident Details: ', incident.details)
    print('---')

    get_replace_date_input(incident, DBsession)
    return


def main():
    if os.path.exists('checked_dates.csv'):
        with open('checked_dates.csv', 'r') as f:
            already_checked_incidents = [int(i.strip()) for i in f.readlines()[1:]]
    DBsession, engine = get_database_session(environment='prod')
    mismatched_dates = find_mismatched_dates(DBsession, already_checked_incidents)
    print(f'{len(mismatched_dates)} mismatched dates found.')
    for incident in tqdm(mismatched_dates):
        fix_mismatched_dates(incident, DBsession)


if __name__ == '__main__':
    main()
