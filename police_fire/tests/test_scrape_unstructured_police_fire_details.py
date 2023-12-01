from database import get_database_session, Article, create_tables, Base, Incidents, IncidentsWithErrors
from scrape_articles_by_section import login, scrape_article

from police_fire.scrape_structured_police_fire_details import scrape_structured_incident_details
from police_fire.scrape_unstructured_police_fire_details import scrape_unstructured_incident_details

create_tables(environment='test')
DBsession, engine = get_database_session(environment='test')

def delete_table_contents():
    DBsession.query(IncidentsWithErrors).delete()
    DBsession.query(Incidents).delete()
    DBsession.query(Article).delete()
    DBsession.commit()


def test_duplicate_structured_incident_does_not_get_added():
    delete_table_contents()
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 0

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?',
                   logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/virgil-man-charged-with-sex-abuse,70554?').first()
    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 4

    article_content = test_article.content
    article_date_published = test_article.date_published
    scrape_unstructured_incident_details(test_article.id, test_article.url, article_content, article_date_published,
                                         DBsession)
    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 5


def test_multiple_unstructured_incidents_get_added():
    delete_table_contents()
    incidents = DBsession.query(Incidents).all()
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

    incidents = DBsession.query(Incidents).all()
    assert len(incidents) == 2
