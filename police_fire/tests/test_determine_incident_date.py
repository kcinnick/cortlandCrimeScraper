import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from police_fire.scrape_structured_police_fire_details import check_if_details_references_a_relative_date
from database import get_database_session, Article, Incidents, Base

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

def test_check_if_details_references_a_relative_date():
    db_session, engine = get_database_session(environment='test')
    # get article with ID 184
    incident = db_session.query(Incidents).filter(
        Incidents.url == 'https://www.cortlandstandard.com/stories/syracuse-man-charged-with-burglary-assault,20103?'
    ).filter(Incidents.accused_name =='Alene D. Heath').first()

    response = check_if_details_references_a_relative_date(incident.details, incident.incident_reported_date)
    assert response == '2022-03-12'

    return


