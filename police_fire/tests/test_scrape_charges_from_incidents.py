import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from database import Base, Incident
from police_fire.scrape_charges_from_incidents import categorize_charges, add_charges_to_charges_table

database_username = os.getenv('DATABASE_USERNAME')
database_password = os.getenv('DATABASE_PASSWORD')
print("database_username: ", database_username)
print("database_password: ", database_password)


def test_assert_all_charges_are_categorized():
    # test set up
    # add person, add incident
    engine = create_engine(
        f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_dev')
    Base.metadata.create_all(engine)
    # Create a new session for testing
    db_session = scoped_session(sessionmaker(bind=engine))

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
    incidents = db_session.query(Incident).all()
    incident = incidents[0]
    categorized_charges = categorize_charges(incident)
    assert categorized_charges['felonies'] == []
    assert len(categorized_charges['misdemeanors']) == 2


