from pprint import pprint

from police_fire.scrape_structured_police_fire_details import check_if_details_references_a_relative_date
from database import get_database_session, Article, Incidents


def test_check_if_details_references_a_relative_date():
    db_session, engine = get_database_session(test=False)
    # get article with ID 184
    incident = db_session.query(Incidents).filter(
        Incidents.url == 'https://www.cortlandstandard.com/stories/syracuse-man-charged-with-burglary-assault,20103?'
    ).filter(Incidents.accused_name =='Alene D. Heath').first()

    response = check_if_details_references_a_relative_date(incident.details, incident.incident_reported_date)
    assert response == '2022-03-12'

    return


