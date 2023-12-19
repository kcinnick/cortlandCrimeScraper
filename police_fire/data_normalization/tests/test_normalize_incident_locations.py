import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from database import Base, Incidents
from police_fire.data_normalization.normalize_incident_locations import main

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
    # try:
    #     drop_view_sql = text("""DROP VIEW public.combined_incidents""")
    #     db_session.execute(drop_view_sql)
    #     db_session.commit()
    # except:
    #     db_session.rollback()

    yield db_session  # Provide the session for testing

    db_session.close()
    Base.metadata.drop_all(engine)  # Drop tables after tests are done


def test_main(setup_database):
    # test set up
    fake_incident = Incidents(
        accused_name='Test',
        incident_location='Lansing'
    )

    DBsession = setup_database
    DBsession.add(fake_incident)
    DBsession.commit()

    main(environment='test')

    # test
    incident = DBsession.query(Incidents).filter(
        Incidents.accused_name == 'Test',
    ).first()
    assert incident.incident_location == 'Lansing, New York'
