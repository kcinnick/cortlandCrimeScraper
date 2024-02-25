from models.incident import Incident

from police_fire.test_database import setup_database


def test_person_incident_link(setup_database):
    # test set up
    # add person, add incident
    DBsession = setup_database

    fake_incident = Incident(
        accused_name='Fake J. Faker',
        incident_reported_date='2020-01-01',
        incident_date='2020-01-01',
        accused_age=99,
        accused_location='Fakeville, NY',
        charges='Fake charges',
        details='Fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeville, NY',
        source='https://www.fakeurl.com',
    )

    second_fake_incident = Incident(
        accused_name='Fake J. Faker',
        incident_reported_date='2020-01-02',
        incident_date='2020-01-02',
        accused_age=100,
        accused_location='Fakeville, NY',
        charges='More fake charges',
        details='More fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeland County, NY',
        source='https://www.fakeurl.com',
    )

    DBsession.add(fake_incident)
    DBsession.add(second_fake_incident)
    DBsession.commit()
