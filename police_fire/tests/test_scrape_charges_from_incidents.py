from models.incident import Incident
from police_fire.scrape_charges_from_incidents import categorize_charges

from police_fire.test_database import setup_database


def test_assert_all_charges_are_categorized(setup_database):
    # test set up
    # add person, add incident
    db_session = setup_database

    fake_incident = Incident(
        accused_name='Christian M. Seaman',
        incident_reported_date='2020-05-21',
        incident_date='2020-05-21',
        accused_age=40,
        accused_location='Groton, NY',
        charges='Aggravated driving while intoxicated with a blood alcohol content of 0.18% or more, driving with a blood alcohol content of 0.08% or more, driving while intoxicated, third-degree aggravated unlicensed operation of a motor vehicle, misdemeanors; inadequate brake lamps, a violation.',
        details='Two people called 911 about 5:35 p.m. Monday complaining an intoxicated man left Triphammer Wine and Spirits in a black Volvo station wagon',
        legal_actions='Seamans was ticketed to appear June 9 in Lansing Town Court.',
        incident_location='Route 13 near Warren Road, Cayuga Heights, Tompkins County, New York',
        source='https://www.fakeurl.com',
    )

    db_session.add(fake_incident)
    db_session.commit()

    # test
    incident = db_session.query(Incident).filter(Incident.accused_name == 'Christian M. Seaman').first()
    categorized_charges = categorize_charges(incident, incident.charges, incident.accused_name)
    assert categorized_charges['felonies'] == []
    assert len(categorized_charges['misdemeanors']) == 2

