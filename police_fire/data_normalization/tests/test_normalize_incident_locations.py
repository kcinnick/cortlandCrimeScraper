from models.incident import Incident
from police_fire.data_normalization.normalize_incident_locations import main
from police_fire.test_database import setup_database


def test_main(setup_database, monkeypatch):
    # test set up
    fake_incident = Incident(
        accused_name='Test',
        incident_location='Lansing'
    )

    DBsession = setup_database
    DBsession.add(fake_incident)
    DBsession.commit()

    monkeypatch.setattr(
        'police_fire.data_normalization.normalize_incident_locations.get_database_session',
        lambda environment: (DBsession, DBsession.bind),
    )
    main(environment='test')

    # test
    incident = DBsession.query(Incident).filter(
        Incident.accused_name == 'Test',
    ).first()
    assert incident.incident_location == 'Lansing, New York'
