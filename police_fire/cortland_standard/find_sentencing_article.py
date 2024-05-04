# there are typically articles for when the incident occurs, and then articles for when the sentencing occurs
# if we don't link the sentencing article to the initial incident, we could double-count the incident
# to do this, we should look up each incident in the database, find the accused_name, and then look for
# all articles with 'sentence/convicted/plead guilty' and the accused_name in the html_content.

import os
import sys

from database import get_database_session

from models.article import Article
from models.incident import Incident


def find_sentencing_article(session):
    articles = session.query(Article).all()
    sentencing_articles = []

    for article in articles:
        if 'sentenc' in article.content:
            print('Found sentenc in article {}'.format(article.id))
            sentencing_articles.append(article)

    print('Found {} sentencing articles'.format(len(sentencing_articles)))

    return sentencing_articles


def main():
    session, engine = get_database_session(environment='prod')
    sentencing_articles = find_sentencing_article(session)
    incidents = session.query(Incident).all()
    for incident in incidents:
        for article in sentencing_articles:
            if incident.accused_name in article.content:
                #incident.sentencing_article_id = article.id
                #session.commit()
                print('linked article {} to incident {}'.format(article.id, incident.id))
                break


if __name__ == '__main__':
    main()
