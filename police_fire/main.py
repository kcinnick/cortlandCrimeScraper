from datetime import date

import scrape_structured_police_fire_details
import scrape_unstructured_police_fire_details
from database import get_database_session
from models.article import Article
from models.incident import Incident

from scrape_articles_by_section import main as scrape_articles_by_section


def main(environment='dev'):
    scrape_articles_by_section(max_pages=1, environment=environment)
    database_session, engine = get_database_session(environment=environment)
    articles = database_session.query(Article).order_by(Article.date_published.desc()).all()
    # reverse the list so that the most recent articles are scraped first
    # get date of last incident scraped by ordering Incident table by date_published, descending
    last_incident = database_session.query(Incident).order_by(
        Incident.incident_reported_date.desc()).first()
    if last_incident:
        last_incident_date = last_incident.incident_reported_date
    else:
        last_incident_date = date(1899, 1, 1)
    # get articles after last incident date
    articles_with_incidents = [article for article in articles if
                               article.date_published > last_incident_date]
    for article in articles_with_incidents:
        scrape_structured_police_fire_details.scrape_structured_incident_details(article, database_session)
        article_id, article_url, article_content, article_date_published = article.id, article.url, article.content, article.date_published
        scrape_unstructured_police_fire_details.scrape_unstructured_incident_details(
            article_id,
            article_url,
            article_content,
            article_date_published,
            database_session
        )

    return


if __name__ == '__main__':
    main(environment='prod')
