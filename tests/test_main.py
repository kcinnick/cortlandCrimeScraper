from database import get_database_session, Base, Article
from main import login, scrape_article, get_article_urls


def test_scrape_article():
    DBsession, engine = get_database_session(test=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # assert database is empty
    assert len(DBsession.query(Article).all()) == 0
    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?', logged_in_session,
                   section='Police/Fire', DBsession=DBsession)

    # assert scraped article is in database
    assert len(DBsession.query(Article).all()) == 1


def test_login():
    logged_in_session = login()
    r = logged_in_session.get('https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?')
    assert 'My account' in r.text


def test_get_articles():
    logged_in_session = login()
    article_urls = get_article_urls(
        ['Police/Fire'], [], '', 'any',
        '', '', [], session=logged_in_session,
        max_pages=1
    )
    assert len(article_urls) > 0
