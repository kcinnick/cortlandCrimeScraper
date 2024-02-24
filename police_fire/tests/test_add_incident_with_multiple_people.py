from police_fire.scrape_structured_police_fire_details import scrape_structured_incident_details
from police_fire.utilities import login
from scrape_articles_by_section import scrape_article

from models.article import Article
from models.incident import Incident
from police_fire.test_database import setup_database


def test_add_structured_incident_with_multiple_people(setup_database):
    DBsession = setup_database
    article_url = "https://www.cortlandstandard.com/stories/motorcyclist-dies-on-i-81,60601?"
    logged_in_session = login()
    scrape_article(article_url, logged_in_session, section='Police/Fire', DBsession=DBsession)
    article_object = DBsession.query(Article).filter(Article.url == article_url).first()
    scrape_structured_incident_details(article_object, DBsession)

    incidents = DBsession.query(Incident).all()

    last_incident = incidents[-1]
    assert last_incident.accused_name == 'Samuel J. Swan,Adrianne L. Wagoner'
    assert last_incident.accused_age == '47,40'
    assert last_incident.accused_location == 'N/A,Nye Road, Virgil'
