from pprint import pprint

from tqdm import tqdm

from police_fire.scrape_structured_police_fire_details import scrape_structured_incident_details

import regex as re
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from main import login, scrape_article
from newspaper import Article as NewspaperArticle

from database import get_database_session, Article, Incidents, IncidentsWithErrors, create_tables, Base

create_tables(test=True)
DBsession, engine = get_database_session(test=True)


def test_structured_data_with_wrong_counts_gets_added_to_incidentsWithErrors_table():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    incidents_with_errors = DBsession.query(IncidentsWithErrors).all()
    assert len(incidents_with_errors) == 0

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?', logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?').first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents_with_errors = DBsession.query(IncidentsWithErrors).all()
    assert len(incidents_with_errors) == 1

    DBsession.close()
    return


def test_structure_data_with_matching_counts_gets_added_to_incidents_table():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?', logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?').first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incidents).all()

    assert len(incidents) == 1

    scraped_incident = incidents[0]

    assert scraped_incident.url == 'https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?'
    assert scraped_incident.accused_name == 'Julie M. Conners'
    assert scraped_incident.accused_age == '34'
    assert scraped_incident.accused_location == 'Cold Brook Road, Homer'
    assert scraped_incident.charges == 'Driving while intoxicated, a misdemeanor; parked on a highway, a violation'
    assert scraped_incident.details == 'Cortland County sheriff’s officers found Conners’ vehicle parked abut 1:38 a.m. Sunday on Riley Road in Cortlandville. Police said they found Conners intoxicated.'
    assert scraped_incident.legal_actions == 'Conners was ticketed to appear Nov. 27 in Cortlandville Town Court.'

    DBsession.close()
    return


def test_structure_data_with_multiple_incidents_gets_added_correctly():
    article_url = 'https://www.cortlandstandard.com/stories/groton-driver-charged-after-crash-causes-injury,13070?'
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incidents).all()

    assert len(incidents) == 9


def test_structure_data_with_multiple_incidents_with_span_tag_gets_added_correctly():
    article_url = 'https://www.cortlandstandard.com/stories/two-charged-with-drunken-driving,12273?'
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incidents).all()

    assert len(incidents) == 2
    for incident in incidents:
        assert incident.details is not ''

