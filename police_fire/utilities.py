# contains helper functions that are useful for both structured and unstructured data.
import ast
import os
import re

import sqlalchemy
from openai import OpenAI
from openai.types.chat.completion_create_params import ResponseFormat
from tqdm import tqdm

from models.incident import Incident
from models.incidents_with_errors import IncidentsWithErrors
from models.article import Article


def delete_table_contents(DBsession, engine):
    if sqlalchemy.inspect(engine).has_table("incidents_with_errors"):
        DBsession.query(IncidentsWithErrors).delete()

    DBsession.query(Incident).delete()
    DBsession.query(Article).delete()
    DBsession.commit()

    return


def add_incident_with_error_if_not_already_exists(article, DBsession):
    if DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 0:
        incidentWithError = IncidentsWithErrors(
            article_id=article.id,
            url=article.url
        )
        DBsession.add(incidentWithError)
        DBsession.commit()

    return


def clean_up_charges_details_and_legal_actions_records(charges_str, details_str, legal_actions_str):
    if charges_str.startswith(': '):
        charges_str = charges_str[2:]
    else:
        charges_str = charges_str.replace('Charges: ', '')
    if details_str.startswith(': '):
        details_str = details_str[2:]
    else:
        details_str = details_str.replace('Details: ', '')
    if legal_actions_str.startswith(': '):
        legal_actions_str = legal_actions_str[2:]
    else:
        legal_actions_str = re.sub(r'Legal [Aa]ctions: ', '', legal_actions_str)

    return charges_str, details_str, legal_actions_str


client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def search_for_day_of_week_in_details(details_str):
    """if the details contain a day of the week, return the day that matched"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days:
        if day in details_str:
            return day


def get_response_for_query(query):
    completion = client.chat.completions.create(
        model='gpt-4-1106-preview',
        messages=[
            {'role': 'system',
             'content': query},
        ],
        temperature=0,
        response_format=ResponseFormat(type='json_object')
    )
    response = completion.choices[0].message.content.strip()
    print('response', response)

    return response


def get_last_date_of_day_of_week_before_date(day_of_week, date):
    # find the last time that day of the week occurred before the date
    query = "What was the most recent date that " + day_of_week + " occurred before " + str(
        date) + "? Return ONLY the date in JSON format, with the key as 'date', as a string formatted YYYY-MM-DD. If none, return N/A."

    response = get_response_for_query(query)
    response = ast.literal_eval(response)

    return response['date']


def check_if_details_references_a_relative_date(details_str, incident_reported_date):
    day_in_incident_details = search_for_day_of_week_in_details(details_str)
    if day_in_incident_details is None:
        return None
    # if day_in_incident_details is not None, find the last time that day of the week occurred before the
    # incident_reported_date.
    response = get_last_date_of_day_of_week_before_date(day_in_incident_details, incident_reported_date)

    return response


def check_if_details_references_an_actual_date(details_str, article_published_date):
    """if the details contain a date, return the date that matched + the year the article was published"""
    query = f"What was the date of the incident: {details_str}? Return only the date as YYYY-MM-DD as JSON with the key 'date'. Use the year in the article published date as the year: {article_published_date}"
    response = get_response_for_query(query)
    response = ast.literal_eval(response)

    return response['date']


def update_incident_date_if_necessary(DBsession, incident_date_response, details_str):
    if not incident_date_response:
        print('No incident date found.  Not updating database.')
        return
    elif not incident_date_response[0].isdigit():
        print(f'Incident date found was not date-formatted: {incident_date_response}.  Not updating database.')
        return
    existing_incident = DBsession.query(Incident).filter_by(details=details_str).first()
    if existing_incident:
        print('incident date response', incident_date_response)
        existing_incident.incident_date = incident_date_response
        DBsession.add(existing_incident)
        DBsession.commit()
        print('Incident date updated for ' + existing_incident.source)

    return


def get_incident_location_from_details(details_str):
    """if the details contain a location, return the location that matched"""
    query = "What was the location of the incident: " + details_str + "? Return only the address, city and state (full name, not abbreviation) where available in JSON format, with 'location' as the only key. If none, return N/A."
    response = get_response_for_query(query)
    response = response.replace('The location of the incident was ', '')
    response = response.replace('The location of the incident is ', '')
    response = response.replace(' in ', ', ')
    response = ast.literal_eval(response)

    if ' sorry' in response['location']:
        return 'N/A'

    if type(response['location']) == dict:
        address = response['location'].get('address')
        if address is None:
            address = response['location'].get('street')
        response['location'] = f"{address}, {response['location']['city']}, {response['location']['state']}"

    return response['location']


def link_persons_to_incident(DBsession):
    index = 0
    persons = DBsession.query(Persons).all()
    for person in tqdm(persons):
        incidents = DBsession.query(Incident).filter_by(accused_name=person.name).all()
        for incident in incidents:
            incident.accused_person_id = person.id
            DBsession.add(incident)
            DBsession.commit()
            print(f"Person ID: {person.id} linked to Incident ID: {incident.id}")
            index += 1

    return


def add_or_get_person(session, name):
    person = session.query(Persons).filter_by(name=name).first()
    if person is None:
        person = Persons(name=name)
        session.add(person)
        session.commit()
    return person.id


def main():
    DBsession, engine = get_database_session(environment='prod')
    link_persons_to_incident(DBsession)


if __name__ == '__main__':
    main()
