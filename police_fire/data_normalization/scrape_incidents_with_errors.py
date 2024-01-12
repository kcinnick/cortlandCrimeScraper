from tqdm import tqdm

from database import get_database_session, Incident, IncidentsWithErrors, Article
from police_fire.scrape_unstructured_police_fire_details import scrape_unstructured_incident_details
from scrape_articles_by_section import scrape_article
from utilities import login


DBsession, engine = get_database_session(environment='prod')
logged_in_session = login()
incidents_with_errors = list(DBsession.query(IncidentsWithErrors).all())
DBsession.close()

for incident in tqdm(incidents_with_errors):
    DBsession, engine = get_database_session(environment='prod')
    article_id, article_url, = incident.article_id, incident.url
    if article_id:
        article_content = DBsession.query(Article).filter_by(id=article_id).first().content
        article_date_published = DBsession.query(Article).filter_by(id=article_id).first().date_published
    else:
        scrape_article(article_url, logged_in_session, section='Police/Fire', DBsession=DBsession)
        article_id = DBsession.query(Article).filter_by(url=article_url).first().id
        article_content = DBsession.query(Article).filter_by(url=article_url).first().content
        article_date_published = DBsession.query(Article).filter_by(url=article_url).first().date_published

    scrape_unstructured_incident_details(article_id, article_url, article_content, article_date_published, DBsession)
    DBsession.delete(incident)
    DBsession.commit()
    DBsession.close()
