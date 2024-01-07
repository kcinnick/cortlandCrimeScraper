import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database import Article, Incident, IncidentsWithErrors, Base
from police_fire.scrape_structured_police_fire_details import scrape_structured_incident_details, \
    identify_articles_with_incident_formatting
from police_fire.scrape_unstructured_police_fire_details import scrape_unstructured_incident_details
from police_fire.utilities import add_or_get_person
from scrape_articles_by_section import login, scrape_article

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


def test_duplicate_structured_incident_does_not_get_added(setup_database):
    DBsession = setup_database
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?',
                   logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?').first()
    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 4

    article_content = test_article.content
    article_date_published = test_article.date_published
    scrape_unstructured_incident_details(test_article.id, test_article.url, article_content, article_date_published,
                                         DBsession)
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 5


def test_multiple_unstructured_incidents_get_added(setup_database):
    DBsession = setup_database
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 0

    logged_in_session = login()
    for article_url in ['https://www.cortlandstandard.com/stories/brooklyn-man-found-with-5700-in-cocaine,33840',
                        'https://www.cortlandstandard.com/stories/guns-drawn-during-arrest,70761?',
                        ]:
        scrape_article(article_url,
                       logged_in_session,
                       section='Police/Fire', DBsession=DBsession)
        test_article = DBsession.query(Article).where(
            Article.url == article_url).first()

        article_content = test_article.content
        article_date_published = test_article.date_published
        scrape_unstructured_incident_details(
            test_article.id, test_article.url, article_content, article_date_published,
            DBsession)

    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 2


def test_add_unstructured_incident_with_multiple_people(setup_database):
    DBsession = setup_database
    article_url = "https://www.cortlandstandard.com/stories/two-charged-in-drug-possession-case,65066?"
    logged_in_session = login()
    scrape_article(article_url, logged_in_session, section='Police/Fire', DBsession=DBsession)
    article_object = DBsession.query(Article).filter(Article.url == article_url).first()
    scrape_unstructured_incident_details(article_object.id, article_url, article_object.content, article_object.date_published, DBsession)

    incidents = DBsession.query(Incident).all()

    last_incident = incidents[-1]
    assert last_incident.accused_name == 'Amber L. Harris, Tammy M. Smith'
    assert last_incident.accused_age == '35, 49'
    assert last_incident.accused_location == 'Wheeler Ave., Cortland, Grove Street, Marathon'
