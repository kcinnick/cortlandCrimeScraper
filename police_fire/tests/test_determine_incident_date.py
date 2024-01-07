import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from database import Incident, Base, Persons
from police_fire.scrape_structured_police_fire_details import check_if_details_references_a_relative_date
from police_fire.utilities import add_or_get_person

database_username = os.getenv('DATABASE_USERNAME')
database_password = os.getenv('DATABASE_PASSWORD')


@pytest.fixture(scope="function")
def setup_database():
    # Connect to your test database
    engine = create_engine(
        f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_test')
    Base.metadata.create_all(engine)  # Create tables

    # Create a new session for testing
    db_session = scoped_session(sessionmaker(bind=engine))

    # add test person for incident
    fake_person = Persons(name='Fake Person')
    db_session.add(fake_person)
    db_session.commit()

    fake_incident = Incidents(
        accused_name='Fake Person',
        incident_reported_date='2022-11-02',
        incident_date='2022-10-28',
        accused_age=52,
        accused_location='Cortland',
        charges='Third-degree burglary, a felony; petit larceny, a misdemeanor',
        details="Heath stole items Friday from Walmart on Bennie Road in Cortlandville, Cortland County sheriff's officers said. She had previously been issued a trespass order barring her from the property.",
        legal_actions='Heath was arraigned via Cortland County central arraignment and released without bail pending an appearance today in Cortlandville Town Court.',
        incident_location='Walmart on Bennie Road, Cortlandville, Cortland County',
        url='https://www.fakeurl.com',
    )

    db_session.add(fake_incident)
    db_session.commit()

    yield db_session  # Provide the session for testing

    db_session.close()
    Base.metadata.drop_all(engine)  # Drop tables after tests are done


def test_check_if_details_references_a_relative_date(setup_database):
    db_session = setup_database
    incident = db_session.query(Incidents).filter(
        Incidents.url == 'https://www.fakeurl.com'
    ).filter(Incidents.accused_name == 'Fake Person').first()

    response = check_if_details_references_a_relative_date(incident.details, incident.incident_reported_date)
    assert response == '2022-10-28'

    return
