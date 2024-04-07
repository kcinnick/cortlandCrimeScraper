import datetime
import json
from datetime import timedelta
from pprint import pprint

from tqdm import tqdm

from database import get_database_session
from models.article import Article
from models.incident import Incident
from police_fire.utilities import get_response_for_query, check_if_details_references_a_relative_date, \
    get_incident_location_from_details


def get_articles(DBsession):
    # get articles by date_published descending, and filter out articles that have already had incidents scraped
    articles = DBsession.query(Article).filter(Article.url.like('https://cortlandvoice.com%')).all()
    articles_with_incidents_not_scraped = [article for article in articles if not article.incidents_scraped]
    print(f'{len(articles_with_incidents_not_scraped)} unscraped articles found.')
    return articles_with_incidents_not_scraped


def filter_incidents(DBsession, new_incident):
    # Fetch all incidents for the person, ordered by date
    incidents = DBsession.query(Incident).filter(
        Incident.accused_name == new_incident['accused_name'],
    ).order_by(Incident.incident_reported_date.asc()).all()

    new_incident_reported_date = new_incident['incident_reported_date']

    for existing_incident in incidents:
        existing_incident_reported_date = existing_incident.incident_reported_date
        print('new incident reported date: ', new_incident_reported_date)
        print('existing incident reported date: ', existing_incident_reported_date)
        # if the incident_reported_date is within a week of the new incident, check if the details are the same
        if new_incident_reported_date - timedelta(
                days=7) <= existing_incident_reported_date <= new_incident_reported_date + timedelta(days=7):
            print('Duplicate incident found.  Not adding to database.')
            return True
        else:
            continue

    return False


def check_if_incident_already_scraped(DBsession, incident):
    # if there's an incident within the same week with the same accused name, it's probably a duplicate
    duplicate_incident = filter_incidents(DBsession, incident)

    if duplicate_incident:
        print('Potential duplicate incident found.  Not adding to database.')
        return True
    else:
        print('No potential duplicate incidents found.  Filtering for nulls before adding to database.')
        nulls_found = 0
        if incident['accused_name'] in ['N/A', None]:
            print('No accused name found.  Not adding to database.')
            return True
        if incident['accused_age'] in ['N/A', '0', 0, None]:
            nulls_found += 1
        if incident['accused_location'] in ['N/A', None]:
            nulls_found += 1
        if incident['charges'] in ['N/A', None]:
            nulls_found += 1
        if incident['details'] in ['N/A', None]:
            nulls_found += 1
        if incident['legal_actions'] in ['N/A', None]:
            nulls_found += 1

        if nulls_found > 4:
            print('Too many nulls found.  Not adding to database.')
            return True
        else:
            return False


def scrape_incidents_from_article(DBsession, article):
    print(article.url)
    query = ("What incidents are listed in this article? JSON response should contain the keys "
             "accused_name, incident_date, accused_age, accused_location, charges, details, and legal_actions. "
             "Dates should be formatted as YYYY-MM-DD and all JSON values should be strings."
             "If there is more than one person listed in an incident, each person should have "
             "their own incident: ") + article.content
    response = get_response_for_query(query)
    jsonified_response = json.loads(response)
    if 'incidents' in jsonified_response.keys():
        incidents = jsonified_response['incidents']
    else:
        incidents = []
        incidents.append(jsonified_response)

    errors = False
    for incident in incidents:
        incident['incident_reported_date'] = article.date_published
        print('incident: ', incident)
        already_scraped = check_if_incident_already_scraped(DBsession, incident)
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
        try:
            jsonified_charges = json.loads(charges)
        except json.JSONDecodeError:
            jsonified_charges = charges
        except TypeError:
            jsonified_charges = charges
        if type(jsonified_charges) == list:
            jsonified_charges = ', '.join(jsonified_charges)
        elif type(jsonified_charges) == str:
            jsonified_charges = charges
        elif not jsonified_charges:
            jsonified_charges = 'N/A'
        elif type(charges) == dict:
            jsonified_charges = ', '.join(charges.values())
        else:
            raise ValueError('Charges not in expected format.')

        # check if incident_date is a date
        try:
            possible_date = datetime.datetime.strptime(incident['incident_date'], '%Y-%m-%d')
        except ValueError:
            print('Incident date is not a date.  Using reported date.')
            incident['incident_date'] = incident['incident_reported_date']

        try:
            incident = Incident(
                source=article.url,
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


if __name__ == '__main__':
    main()
