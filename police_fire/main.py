from datetime import date

from tqdm import tqdm

import scrape_structured_police_fire_details
import scrape_unstructured_police_fire_details
from database import get_database_session
from models.article import Article
from models.incident import Incident

from scrape_articles_by_section import main as scrape_articles_by_section
from scrape_charges_from_incidents import main as scrape_charges_from_incidents
from data_normalization.fix_charge_descriptions_with_misspellings import spellcheck_charges
from data_normalization.categorize_charges import main as categorize_charges


def main(environment='dev'):
    scrape_articles_by_section(max_pages=1, environment=environment)
    database_session, engine = get_database_session(environment=environment)
    # get articles by date_published descending, and filter out articles that have already had incidents scraped
    articles = database_session.query(Article).order_by(Article.date_published.desc()).all()
    articles_with_incidents_not_scraped = [article for article in articles if not article.incidents_scraped]
    print(f'{len(articles_with_incidents_not_scraped)} unscraped articles found.')
    for article in tqdm(articles_with_incidents_not_scraped, desc='Scraping incidents from article content.'):
        scrape_structured_police_fire_details.scrape_structured_incident_details(article, database_session)
        article_id, article_url, article_content, article_date_published = article.id, article.url, article.content, article.date_published
        scrape_unstructured_police_fire_details.scrape_unstructured_incident_details(
            article_id,
            article_url,
            article_content,
            article_date_published,
            database_session
        )
        article.incidents_scraped = True
        database_session.commit()

    spellcheck_charges()
    scrape_charges_from_incidents()
    categorize_charges()

    return


if __name__ == '__main__':
    main(environment='prod')
