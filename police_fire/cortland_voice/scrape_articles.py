from datetime import datetime

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
    r = requests.get('https://cortlandvoice.com/category/news/crime-courts/page/' + str(page), headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    article_titles = soup.find_all('h4', class_='title')
    article_urls = []
    for article_title in article_titles:
        article_urls.append(article_title.find('a').get('href'))

    return article_urls


def scrape_article(article_url, database_session):
    r = requests.get(article_url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    headline = soup.find('h1', itemprop='headline').text.strip()
    section = 'Police/Fire'
    author = soup.find('div', class_='post-author').text.lstrip('by ')
    date_published = datetime.strptime(soup.find('div', class_='post-date').text, '%B %d, %Y')
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

    database_session.add(article)
    database_session.commit()
    print('Article added to database.')

    return


def main():
    database_session, engine = get_database_session(environment='prod')
    already_scraped_articles = database_session.query(Article.url).all()
    already_scraped_articles = [url[0] for url in already_scraped_articles]
    page = 1
    while True:
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
