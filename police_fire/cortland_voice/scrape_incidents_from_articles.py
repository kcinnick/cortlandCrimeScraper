import datetime
import json
from datetime import timedelta

from sqlalchemy import and_
from tqdm import tqdm

from database import get_database_session
from models.article import Article
from models.incident import Incident
from police_fire.utilities.utilities import get_response_for_query, check_if_details_references_a_relative_date, \
    get_incident_location_from_details


def get_articles(DBsession):
    # get articles by date_published descending, and filter out articles that have already had incidents scraped
    articles = DBsession.query(Article).filter(Article.url.like('https://cortlandvoice.com%')).all()
    articles_with_incidents_not_scraped = [article for article in articles if not article.incidents_scraped]
    print(f'{len(articles_with_incidents_not_scraped)} unscraped articles found.')
    return articles_with_incidents_not_scraped


def filter_incidents(DBsession, new_incident):
    # Fetch all incidents for the person, ordered by date

    first_name, last_name = new_incident['accused_name'].split()[0], new_incident['accused_name'].split()[-1]

    incidents = DBsession.query(Incident).filter(
        and_(
            # Match records where the accused_name starts with the first name
            Incident.accused_name.ilike(f"{first_name}%"),
            # And also contains the last name at the end.
            Incident.accused_name.ilike(f"%{last_name}")
        )
    ).order_by(Incident.incident_reported_date.asc()).all()

    new_incident_reported_date = new_incident['incident_reported_date']

    for existing_incident in incidents:
        existing_incident_reported_date = existing_incident.incident_reported_date
        print('new incident reported date: ', new_incident_reported_date)
        print('existing incident reported date: ', existing_incident_reported_date)
        # if the incident_reported_date is within a week of the new incident
        if new_incident_reported_date - timedelta(
                days=5) <= existing_incident_reported_date <= new_incident_reported_date + timedelta(days=5):
            print('Duplicate incident found.  Adding cortlandVoiceSource.')
            #
            return existing_incident
        else:
            continue

    return False


def check_if_incident_already_scraped(DBsession, incident, article_url):
    # if there's an incident within the same week with the same accused name, it's probably a duplicate
    duplicate_incident = filter_incidents(DBsession, incident)
    if duplicate_incident:
        print('Duplicate incident found.  Adding cortlandVoiceSource.')
        duplicate_incident.cortlandVoiceSource = article_url
        DBsession.add(duplicate_incident)
        DBsession.commit()
        return True
    else:
        return False


def normalize_charges(charges):
    # Attempt to parse the charges as JSON
    try:
        parsed_charges = json.loads(charges)
    except (json.JSONDecodeError, TypeError):
        # If there's a parsing error or a TypeError, use the original charges string
        parsed_charges = charges

    # Normalize the parsed charges to a string
    if isinstance(parsed_charges, list):
        # If it's a list, join the elements with a comma
        return ', '.join(parsed_charges)
    elif isinstance(parsed_charges, dict):
        # If it's a dictionary, join the values with a comma
        return ', '.join(parsed_charges.values())
    elif not parsed_charges:
        # If parsed_charges is empty or None
        return 'N/A'
    elif isinstance(parsed_charges, str):
        # If it's already a string, just return it
        return parsed_charges
    else:
        # If parsed_charges is of an unexpected type
        raise ValueError('Charges not in expected format.')


def scrape_incidents_from_article(DBsession, article):
    print(article.url)
    query = ("What incidents are listed in this article? JSON response should contain the keys "
             "accused_name, incident_date, accused_age, accused_location, charges, details, and legal_actions. "
             "Dates should be formatted as YYYY-MM-DD and all JSON values should be strings."
             ) + article.content
    response = get_response_for_query(query)
    jsonified_response = json.loads(response)
    if 'incidents' in jsonified_response.keys():
        incidents = jsonified_response['incidents']
    else:
        incidents = []
        incidents.append(jsonified_response)

    errors = False
    print(str(len(incidents)) + ' incidents found.')
    for incident in incidents:
        incident['incident_reported_date'] = article.date_published
        print('incident: ', incident)
        if incident.get('error'):
            article.incidents_scraped = False
            DBsession.add(article)
            DBsession.commit()
            return
        if incident['accused_name'] in ['N/A', '']:
            continue
        duplicate_incident = check_if_incident_already_scraped(DBsession, incident, article.url)
        if duplicate_incident:
            continue
        else:
            already_scraped = False
        incident['location'] = get_incident_location_from_details(incident['details'])

        print('already scraped: ', already_scraped)
        if already_scraped:
            continue

        if not incident.get('incident_date'):
            if incident.get('error'):
                article.incidents_scraped = False
                DBsession.add(article)
                DBsession.commit()
                return
            else:
                incident['incident_date'] = check_if_details_references_a_relative_date(
                    incident['details'],
                    article.date_published
                )

        charges = incident['charges']
        jsonified_charges = normalize_charges(charges)

        try:
            possible_date = datetime.datetime.strptime(incident['incident_date'], '%Y-%m-%d')
        except (ValueError, TypeError):
            print('Incident date is not a date.  Using reported date.')
            incident['incident_date'] = incident['incident_reported_date']

        try:
            incident = Incident(
                cortlandVoiceSource=article.url,
                incident_reported_date=incident['incident_reported_date'],
                accused_name=incident['accused_name'],
                accused_age=incident['accused_age'],
                accused_location=incident['accused_location'],
                charges=jsonified_charges,
                details=incident['details'],
                legal_actions=incident['legal_actions'],
                incident_date=incident['incident_date'],
                incident_location=incident['location']
            )
            DBsession.add(incident)
            DBsession.commit()
        except Exception as e:
            print('Error adding incident to database: ', e)
            DBsession.rollback()
            errors = True

    if errors:
        return

    article.incidents_scraped = True
    DBsession.add(article)
    DBsession.commit()

    return


def main():
    DB_session, engine = get_database_session(environment='prod')
    articles = get_articles(DB_session)
    for article in tqdm(articles):
        scrape_incidents_from_article(DB_session, article)


def rescrape_article(url):
    DB_session, engine = get_database_session(environment='prod')
    article = DB_session.query(Article).filter(Article.url == url).first()
    scrape_incidents_from_article(DB_session, article)


if __name__ == '__main__':
    main()
