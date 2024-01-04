import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from database import Base, Persons, Incidents
from police_fire.scrape_charges_from_incidents import categorize_charges, add_charges_to_charges_table

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


def test_assert_all_charges_are_categorized(setup_database):
    # test set up
    # add person, add incident
    DBsession = setup_database
    fake_person = Persons(name='Christian M. Seaman')
    DBsession.add(fake_person)
    DBsession.commit()

    fake_incident = Incidents(
        accused_name=fake_person.name,
        incident_reported_date='2020-05-21',
        incident_date='2020-05-21',
        accused_age=40,
        accused_location='Groton, NY',
        charges='Aggravated driving while intoxicated with a blood alcohol content of 0.18% or more, driving with a blood alcohol content of 0.08% or more, driving while intoxicated, third-degree aggravated unlicensed operation of a motor vehicle, misdemeanors; inadequate brake lamps, a violation.',
        details='Two people called 911 about 5:35 p.m. Monday complaining an intoxicated man left Triphammer Wine and Spirits in a black Volvo station wagon',
        legal_actions='Seamans was ticketed to appear June 9 in Lansing Town Court.',
        incident_location='Route 13 near Warren Road, Cayuga Heights, Tompkins County, New York',
        url='https://www.fakeurl.com',
    )

    DBsession.add(fake_incident)
    DBsession.commit()

    # test begins
    columns = [
        Incidents.id,
        Incidents.incident_reported_date,
        Incidents.accused_name,
        Incidents.accused_age,
        Incidents.accused_location,
        Incidents.charges,
        Incidents.details,
        Incidents.legal_actions,
        Incidents.incident_date,
        Incidents.incident_location,
    ]
    all_combined_incidents = DBsession.query(*columns).all()
    print("all_combined_incidents: ", all_combined_incidents)
    categorized_charges = categorize_charges(all_combined_incidents[0])
    assert len(categorized_charges['felonies']) == 0

    add_charges_to_charges_table(all_combined_incidents[0], categorized_charges)


