import os

from database import get_database_session, Persons, Incidents

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database import Base  # Import your Base from SQLAlchemy models

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

    yield db_session  # Provide the session for testing

    db_session.close()
    Base.metadata.drop_all(engine)  # Drop tables after tests are done


def test_person_incident_link(setup_database):
    # test set up
    # add person, add incident
    DBsession = setup_database
    fake_person = Persons(name='Fake J. Faker')
    DBsession.add(fake_person)
    DBsession.commit()

    fake_incident = Incidents(
        accused_person_id=fake_person.id,
        incident_reported_date='2020-01-01',
        incident_date='2020-01-01',
        accused_age=99,
        accused_location='Fakeville, NY',
        charges='Fake charges',
        details='Fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeville, NY',
        url='https://www.fakeurl.com',
    )

    second_fake_incident = Incidents(
        accused_person_id=fake_person.id,
        incident_reported_date='2020-01-02',
        incident_date='2020-01-02',
        accused_age=100,
        accused_location='Fakeville, NY',
        charges='More fake charges',
        details='More fake details',
        legal_actions='Fake legal actions',
        incident_location='Fakeland County, NY',
        url='https://www.fakeurl.com',
    )

    DBsession.add(fake_incident)
    DBsession.add(second_fake_incident)
    DBsession.commit()

    # test incident was properly linked to person, and vice versa

    assert len(fake_person.incidents) == 2
