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
    scrape_article('https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?', logged_in_session, section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?').first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents_with_errors = DBsession.query(IncidentsWithErrors).all()
    assert len(incidents_with_errors) == 1

    DBsession.close()
    return
