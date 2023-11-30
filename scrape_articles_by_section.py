import os
from time import sleep

import regex as re

from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle
from newspaper import Config
from requests import Session
from tqdm import tqdm

from database import get_database_session, Article
from utilities import login

config = Config()
userAgent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 "
             "Safari/537.36")
config.browser_user_agent = userAgent

topic_ids = {
    'Lottery': 317,
    'Top Stories': 89,
    'News': 52,
    'Coronavirus': 54,
    'Communities': 154,
    'Police/Fire': 155,
    'Education': 156,
    'Crime': 59,
    'Health': 157,
    'Business': 158,
    'Ag/Environmen': 159,
    'Local': 51,
    'Sports': 55,
    'Cortland Sports': 160,
    'Homer Sports': 161,
    'Dryden Sports': 162,
    'Cincinnatus Sports': 164,
    'Marathon Sports': 163,
    'McGraw Sports': 165,
    'Regional Sports': 166,
    'Living-and-leisure': 58,
    'Entertainment': 167,
    'People': 168,
    'Food': 169,
    'Religion': 170,
    'Reader\'s opinions': 171,
    'Staff opinions': 172,
    'Obituaries': 56,
    'Death Notices': 87,
    'Elections': 325,
    'Special section stories': 327,
    'By-staff': 53,
    'Cayuga-health': 85,
    'Charity': 67,
    'Community-contests': 66,
    'Contributing-writer': 63,
    'Cortland-county-court': 62,
    'CS+': 57,
    'Milestones': 315,
    'Public Safety': 313,
    'Special sections': 372,
    'Sponsored-content': 61,
    'SUBMIT LETTER TO EDITOR': 382,
    'Tompkins': 69,
    'Uncategorized': 60,
}


def get_article_urls(topics, keywords, byline, match_type, sub_types, start_date, end_date, max_pages=9999, session=None):
    if match_type not in ['all', 'any', 'phrase']:
        print('match must be one of all, any, or phrase. defaulting to \'any\'.')
        match = 'any'

    if not keywords:
        keywords = ''

    if sub_types:
        for sub_type in sub_types:
            sub_type_string = f"sub_type%5B%5D={sub_type}&"
    else:
        sub_type_string = ''

    if start_date:
        start_date_n = start_date.split('/')[0]
        start_date_j = start_date.split('/')[1]
        start_date_Y = start_date.split('/')[2]
    else:
        start_date_n = ''
        start_date_j = ''
        start_date_Y = ''

    if end_date:
        end_date_n = end_date.split('/')[0]
        end_date_j = end_date.split('/')[1]
        end_date_Y = end_date.split('/')[2]
    else:
        end_date_n = ''
        end_date_j = ''
        end_date_Y = ''

    page_number = 1

    url = ("https://www.cortlandstandard.com/browse.html?archive_search=1&"
           "content_source=&"
           f"search_filter={','.join(keywords)}&"
           f"search_filter_mode={match_type}&"
           f"byline={byline.replace(' ', '%20')}&"
           f"{sub_type_string}"
           f"date_start_n={start_date_n}&"
           f"date_start_j={start_date_j}&"
           f"date_start_Y={start_date_Y}&"
           f"date_end_n={end_date_n}&"
           f"date_end_j={end_date_j}&"
           f"date_end_Y={end_date_Y}&"
           )

    if topics:
        for topic in topics:
            url += f"category_id%5B%5D={topic_ids[topic]}&"

    hasMore = True

    articleUrls = []

    while hasMore:
        pageUrl = url + f"page={page_number}"
        print('getting page ' + str(page_number))
        sleep(2.5)
        r = session.get(pageUrl)
        soup = BeautifulSoup(r.content, 'html.parser')
        story_container = soup.find('div', class_='container pk-layer default noear')
        story_list = story_container.find('div', class_='story_list')
        stories = story_list.find_all('div', class_='item')
        for story in stories:
            articleUrls.append('https://www.cortlandstandard.com' + story.find('a')['href'])
        if soup.find('span', class_='next'):
            page_number += 1
            if page_number > max_pages:
                hasMore = False
        else:
            print('No more pages found. Stopping.')
            hasMore = False

    return articleUrls

def scrape_article(article_url, logged_in_session, section, DBsession):
    print(article_url)
    parsed_article = NewspaperArticle(article_url, config=config)
    parsed_article.download()
    parsed_article.parse()
    parsed_article.nlp()
    print('keywords: ' + str(parsed_article.keywords))

    r = logged_in_session.get(article_url)
    soup = BeautifulSoup(r.content, 'html.parser')
    headline = soup.find('h1', id='headline').text
    try:
        byline = soup.find('div', class_='byline').text
    except AttributeError:
        byline = ''
    date_published = re.search('"datePublished": "(.*?)"', str(soup)).group(1)

    article = Article(
        headline=headline,
        section=section,
        keywords=parsed_article.keywords,
        author=byline,
        date_published=date_published,
        url=article_url,
        content=parsed_article.text,
        html_content=soup.prettify()
    )

    DBsession.add(article)
    DBsession.commit()
    DBsession.close()

    return


def main():
    DBsession, engine = get_database_session(environment='prod')
    logged_in_session = login()
    article_urls = get_article_urls(
        ['Police/Fire'], [], '', 'any',
        '', '', [], session=logged_in_session,
    )
    already_scraped_urls = [article.url for article in DBsession.query(Article).all()]
    article_urls = [article_url for article_url in article_urls if article_url not in already_scraped_urls]
    for article_url in tqdm(article_urls):
        scrape_article(article_url, logged_in_session, section='Police/Fire', DBsession=DBsession)


if __name__ == '__main__':
    main()
