import os

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database import IncidentsWithErrors, Article, get_database_session, Base
from police_fire.scrape_structured_police_fire_details import scrape_separate_incident_details
from police_fire.utilities import delete_table_contents, \
    get_incident_location_from_details

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


def test_add_incident_with_error_that_does_not_already_exist(setup_database):
    DBsession = setup_database
    delete_table_contents(DBsession)
    article = Article(
        html_content="""
        <div class="body main-body clearfix">
        <p>Accused: Brian D. Tuning, 36, 2385 Stafford Road, Cincinnatus</br></br>Charges:"""
                     + """Fourth-degree criminal possession of stolen property, a felony; petit larceny, a misdemeanor</br>Details:"""
                     + """Tuning used another person's bank card to remove money from the bank twice without the victim's knowledge """
                     + """between Sept. 8 and Sept. 17, Cortland police said. Tuning was arrested Tuesday following an investigation."""
                     + """</br></br>Legal Actions: Tuning was arrainged and released without bail to appear Nov. 23"""
                       """in Cortland City Court.</p></div>""",
        url="https://www.cortlandstandard.com/stories/cincy-man-charged-with-larceny,18652",
    )
    assert DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 0

    soup = BeautifulSoup(article.html_content, 'html.parser')
    separate_incidents = soup.find_all('p')

    for separate_incident in separate_incidents:
        br_tags = str(separate_incident).split('<br/>')
        soupy_br_tags = [BeautifulSoup(br_tag, 'html.parser').text.strip() for br_tag in br_tags if
                         br_tag.strip() != '']
        scrape_separate_incident_details(soupy_br_tags, article, DBsession)
        assert DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 1
    return


def test_do_not_add_incident_with_error_if_already_exists(setup_database):
    DBsession = setup_database
    delete_table_contents(DBsession)

    article = Article(
        html_content="""
        <div class="body main-body clearfix">
        <p>Accused: Brian D. Tuning, 36, 2385 Stafford Road, Cincinnatus</br></br>Charges:"""
                     + """Fourth-degree criminal possession of stolen property, a felony; petit larceny, a misdemeanor</br>Details:"""
                     + """Tuning used another person's bank card to remove money from the bank twice without the victim's knowledge """
                     + """between Sept. 8 and Sept. 17, Cortland police said. Tuning was arrested Tuesday following an investigation."""
                     + """</br></br>Legal Actions: Tuning was arrainged and released without bail to appear Nov. 23"""
                       """in Cortland City Court.</p></div>""",
        url="https://www.cortlandstandard.com/stories/cincy-man-charged-with-larceny,18652",
    )

    assert DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 0

    soup = BeautifulSoup(article.html_content, 'html.parser')
    separate_incidents = soup.find_all('p')

    for i in range(0, 2):
        # assert that the incident does get added the first time, but not the second time
        for separate_incident in separate_incidents:
            br_tags = str(separate_incident).split('<br/>')
            soupy_br_tags = [BeautifulSoup(br_tag, 'html.parser').text.strip() for br_tag in br_tags if
                             br_tag.strip() != '']
            scrape_separate_incident_details(soupy_br_tags, article, DBsession)

        assert DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 1

    return


def test_get_incident_location():
    details_str = "Cortland police detained Axelrod about 2:05 a.m. today when they saw him urinating in the parking lot of 110 Main St., the Cortland Standard. Police said he ran from them and when he was apprehended he gave them a fictitious license."
    incident_location = get_incident_location_from_details(details_str)
    assert incident_location == '110 Main St., Cortland'
    return
