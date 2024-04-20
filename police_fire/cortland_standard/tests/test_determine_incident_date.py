from models.incident import Incident
from police_fire.cortland_standard.scrape_structured_police_fire_details import check_if_details_references_a_relative_date
from police_fire.test_database import setup_database


def test_check_if_details_references_a_relative_date(setup_database):
    db_session = setup_database
    # add fake incident
    fake_incident = Incident(
        accused_name='Fake Person',
        incident_reported_date='2022-10-28',
        accused_age=40,
        accused_location='Groton, NY',
        charges='Fake charges',
        details='Two people called 911 about 5:35 p.m. Monday complaining',
    )
    db_session.add(fake_incident)
    db_session.commit()
    incident = db_session.query(Incident).filter(
        Incident.incident_reported_date == '2022-10-28'
    ).first()

    response = check_if_details_references_a_relative_date(incident.details, incident.incident_reported_date)
    assert response == '2022-10-24'

    return
