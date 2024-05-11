# there are typically articles for when the incident occurs, and then articles for when the sentencing occurs
# if we don't link the sentencing article to the initial incident, we could double-count the incident
# to do this, we should look up each incident in the database, find the accused_name, and then look for
# all articles with 'sentence/convicted/plead guilty' and the accused_name in the html_content.

import os
import sys

from database import get_database_session

from models.article import Article
from models.incident import Incident
from police_fire.utilities.utilities import get_response_for_query


def classify_article_stage(incidents_by_accused_name, accused_name):
    for incident in incidents_by_accused_name[accused_name]:
        print('Looking for incident: {}'.format(incident.id))
        get_response_for_query(
            query=f"You will be an incident. Your task is to determine what stage of the criminal justice process the incident is in. The choices are initial report, arrest, trial, sentencing, and appeal. Please only respond with one of the choices.  If the choice cannot be determined, respond 'undetermined'."
                  f"INCIDENT START: {incident.legal_actions} INCIDENT END.",
            json=False,
        )

    return

def group_incidents_by_accused_name(incidents):
    incidents_by_accused_name = {}
    for incident in incidents:
        if incident.accused_name not in incidents_by_accused_name:
            incidents_by_accused_name[incident.accused_name] = []
        incidents_by_accused_name[incident.accused_name].append(incident)

    return incidents_by_accused_name

def main():
    session, engine = get_database_session(environment='prod')
    # group incidents by accused_name
    incidents = session.query(Incident).all()
    # incidents = [incident for incident in incidents if incident.id in [1567, 3556, 2815, 3547]]
    incidents_by_accused_name = group_incidents_by_accused_name(incidents)

    for accused_name in incidents_by_accused_name.keys():
        print('----------')
        print('Looking for accused_name: {}'.format(accused_name))
        classify_article_stage(incidents_by_accused_name, accused_name)


if __name__ == '__main__':
    main()
