from datetime import datetime
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from database import get_database_session
from models.article import Article

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def get_article_urls(page=1):
    url = 'https://cortlandvoice.com/category/news/crime-courts/page/' + str(page)
    print(url)
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    article_titles = soup.find_all('h4', class_='title')
    article_urls = []
    for article_title in article_titles:
        link = article_title.find('a', href=True)
        if link and urlsplit(link['href']).hostname == 'cortlandvoice.com':
            article_urls.append(link['href'])

    return list(dict.fromkeys(article_urls))


def fetch_article(article_url):
    if urlsplit(article_url).hostname != 'cortlandvoice.com' or urlsplit(article_url).scheme != 'https':
        raise ValueError('Expected an HTTPS Cortland Voice article URL')
    r = requests.get(article_url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    headline = soup.find('h1', itemprop='headline').text.strip()
    section = 'Police/Fire'
    author = soup.find('div', class_='post-author').text.strip().removeprefix('by ').strip()
    date_published = datetime.strptime(soup.find('div', class_='post-date').text.strip(), '%B %d, %Y').date()
    content = soup.find('div', itemprop='articleBody').text.strip()

    article = Article(
        headline=headline,
        section=section,
        author=author,
        date_published=date_published,
        url=article_url,
        content=content,
        html_content=soup.prettify()
    )

    if not headline or not content:
        raise ValueError('Article headline and body must not be empty')
    return article


def scrape_article(article_url, database_session):
    existing = database_session.query(Article).filter_by(url=article_url).first()
    if existing:
        return existing
    article = fetch_article(article_url)
    try:
        database_session.add(article)
        database_session.commit()
    except Exception:
        database_session.rollback()
        raise
    return article


def main(environment='development', max_pages=1):
    database_session, engine = get_database_session(environment=environment)
    already_scraped_articles = database_session.query(Article.url).all()
    already_scraped_articles = [url[0] for url in already_scraped_articles]
    page = 1
    while page <= max_pages:
        article_urls = get_article_urls(page=page)
        if not article_urls:
            break
        for article_url in article_urls:
            print(article_url)
            if article_url in already_scraped_articles:
                print('Article already in database.')
                continue
            scrape_article(article_url, database_session)
        page += 1

    return


if __name__ == '__main__':
    main()
