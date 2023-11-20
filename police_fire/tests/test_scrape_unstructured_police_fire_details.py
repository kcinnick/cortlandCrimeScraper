from database import get_database_session, Article, create_tables, Base, Incidents
from main import login, scrape_article

from police_fire.scrape_structured_police_fire_details import scrape_structured_incident_details
from police_fire.scrape_unstructured_police_fire_details import scrape_unstructured_incident_details

create_tables(test=True)
DBsession, engine = get_database_session(test=True)


def test_duplicate_structured_incident_does_not_get_added():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?', logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?').first()
    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 4

    article_content = test_article.content
    article_date_published = test_article.date_published
    scrape_unstructured_incident_details(test_article.id, test_article.url, article_content, article_date_published, DBsession)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 5


