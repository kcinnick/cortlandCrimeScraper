from datetime import date

from models.incident import Incident

from police_fire.test_database import setup_database


def test_person_incident_link(setup_database):
    # test set up
    # add person, add incident
    DBsession = setup_database

    fake_incident = Incident(
        accused_name='Fake J. Faker',
        incident_reported_date=date(2020, 1, 1),
        incident_date=date(2020, 1, 1),
        accused_age=99,
        accused_location='Fakeville, NY',
        charges='Fake charges',
        details='Fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeville, NY',
    )

    second_fake_incident = Incident(
        accused_name='Fake J. Faker',
        incident_reported_date=date(2020, 1, 2),
        incident_date=date(2020, 1, 2),
        accused_age=100,
        accused_location='Fakeville, NY',
        charges='More fake charges',
        details='More fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeland County, NY',
    )

    DBsession.add(fake_incident)
    DBsession.add(second_fake_incident)
    DBsession.commit()
    records = DBsession.query(Incident).filter_by(accused_name='Fake J. Faker').all()
    assert len(records) == 2
    assert records[0].id != records[1].id
