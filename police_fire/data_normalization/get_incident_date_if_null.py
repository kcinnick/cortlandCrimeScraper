from database import get_database_session
from models.incident import Incident
from police_fire.utilities import search_for_day_of_week_in_details, get_last_date_of_day_of_week_before_date, \
    check_if_details_references_a_relative_date, check_if_details_references_an_actual_date, \
    update_incident_date_if_necessary


def get_incidents_with_null_dates(DBsession):
    incidents = DBsession.query(Incident).filter_by(incident_date=None).all()
    return incidents


def main():
    DBsession, engine = get_database_session(environment='prod')
    incidents_with_null_dates = get_incidents_with_null_dates(DBsession)
    print(len(incidents_with_null_dates), 'incidents with null dates found.')
    for incident in incidents_with_null_dates:
        if hasattr(incident, 'url'):
            print(incident.url)
        incident_date_response = check_if_details_references_a_relative_date(incident.details,
                                                                             incident.incident_reported_date)
        if not incident_date_response:
            print('No relative date found.  Checking for actual date.')
            # check if details references an actual date
            incident_date_response = check_if_details_references_an_actual_date(incident.details,
                                                                                incident.incident_reported_date)
        try:
            update_incident_date_if_necessary(DBsession, incident_date_response, incident.details)
        except Exception as e:
            print('Error updating incident date: ', e)
            continue

    incidents_with_null_dates = get_incidents_with_null_dates(DBsession)
    print(len(incidents_with_null_dates), 'incidents with null dates found after update.')

    return


if __name__ == '__main__':
    main()
