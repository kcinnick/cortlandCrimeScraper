import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from base import Base
from police_fire.utilities.utilities import get_incident_location_from_details

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


def test_get_incident_location():
    details_str = ("Cortland police detained Axelrod about 2:05 a.m. today when they saw him urinating "
                   "in the parking lot of 110 Main St., the Cortland Standard. Police said he ran from "
                   "them and when he was apprehended he gave them a fictitious license.")
    incident_location = get_incident_location_from_details(details_str)
    assert incident_location in [
        '110 Main St., Cortland, New York', '110 Main Street, Cortland, New York'] # output is not consistent
    return
