# first, identify incidents with multiple accused
# split the ages, addresses if necessary, and ID which charges belong to which accused
# then, create a new incident for each accused
# finally, delete the incident with multiple accused
import re

from database import Incident, get_database_session


def split_incidents_with_multiple_accused(DBsession):
    all_incidents = DBsession.query(Incident).all()
    print(str(len(all_incidents)) + ' incidents found.')
    multiple_accused = [i for i in all_incidents if ',' in i.accused_name]
    print(str(len(multiple_accused)) + ' incidents with multiple accused found.')
    return multiple_accused


def clean_split(incident, accused_names, addresses_in_cortland, accused_ages, DBsession):
    for i in range(len(accused_names)):
        print('Creating new charge for ' + accused_names[i] + ' at ' + addresses_in_cortland[i])
        accused_age = accused_ages[i] if i < len(accused_ages) else 'N/A'
        new_incident = Incident(
            source=incident.source,
            incident_reported_date=incident.incident_reported_date,
            accused_name=accused_names[i],
            accused_age=accused_age,
            accused_location=addresses_in_cortland[i],
            charges=incident.charges,
            details=incident.details,
            legal_actions=incident.legal_actions,
        )
        try:
            DBsession.add(new_incident)
            DBsession.commit()
            print('New incident added for ' + accused_names[i])
        except Exception as e:
            print('Error adding incident to database: ', e)
            DBsession.rollback()

    if len(accused_names) == len(addresses_in_cortland):
        print(f'{len(accused_names)} accused names found. Deleting original incident.')
        try:
            DBsession.delete(incident)
            DBsession.commit()
            print('Original incident deleted.')
        except Exception as e:
            print('Error deleting incident from database: ', e)
            DBsession.rollback()


def split_incident(incident, DBsession):
    accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
    accused_location = [i.strip() for i in incident.accused_location.split(';') if i.strip() != '']
    accused_ages = [i.strip() for i in incident.accused_age.split(',') if i.strip() != '']

    # the 'cleanest split' is when the number of accused names matches the number of addresses
    if len(accused_names) == len(accused_location):
        clean_split(incident, accused_names, accused_location, accused_ages, DBsession)
    elif len(accused_location) == 1:
        print('Only one address found.  Splitting accused names and ages.')
        accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
        accused_ages = [i.strip() for i in incident.accused_age.split(',') if i.strip() != '']
        clean_split(incident, accused_names, accused_names[0], accused_ages, DBsession)
    else:
        print(incident)
        pass


def main():
    DBsession, engine = get_database_session(environment='dev')
    multiple_accused_incidents = split_incidents_with_multiple_accused(DBsession)
    for incident in multiple_accused_incidents:
        split_incident(incident, DBsession)


if __name__ == '__main__':
    main()
