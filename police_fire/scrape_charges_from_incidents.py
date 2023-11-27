from database import CombinedIncidents, get_database_session
from sqlalchemy import Column, Integer, String, Date, Boolean, text
from pprint import pprint

DBsession, engine = get_database_session(test=False)
columns = [
    CombinedIncidents.incident_reported_date,
    CombinedIncidents.accused_name,
    CombinedIncidents.accused_age,
    CombinedIncidents.accused_location,
    CombinedIncidents.charges,
    CombinedIncidents.details,
    CombinedIncidents.legal_actions,
    CombinedIncidents.incident_date
]

all_combined_incidents = DBsession.query(*columns).all()


def get_people_from_incident(accused_name, accused_age, accused_location):
    pass


def get_charges_from_incident(incident):
    incident_reported_date, accused_name, accused_age, accused_location, charges, details, legal_actions, incident_date = incident

    # first - does the incident refer to multiple people or just one?
    # if it refers to multiple people, we need to split the charges, details, and legal actions
    # into separate records.
    # if it refers to just one person, we can just add the incident to the database as-is.
    # we can determine whether it refers to multiple people by checking if the accused_name
    # contains the word "and", or a comma. another way to tell is if there are multiple ages.
    # if there are multiple ages, it's likely that there are multiple people.
    # if there are multiple locations, it's likely that there are multiple people.

    people = get_people_from_incident(accused_name, accused_age, accused_location)


    return


def main():
    # charges table should have the following columns:
    # incident_id (foreign key)
    # charge
    # charge_type (misdeameanor, felony, violation, etc.)
    # charge_class (class A, class B, etc.)
    # charge_category (violent, non-violent, etc.)
    # charge_disposition (guilty, not guilty, etc.)
    # charge_disposition_date

    for incident in all_combined_incidents[0:3]:
        get_charges_from_incident(incident)


if __name__ == '__main__':
    main()
