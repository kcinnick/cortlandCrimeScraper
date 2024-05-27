import json
import os

from openai import OpenAI

from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

from database import get_database_session
from models.incident import Incident
from models.article import Article

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def scrape_unstructured_incident_details(article, DBsession):
    # print('Article content: ', article.content)

    completion = client.chat.completions.create(
        model='gpt-3.5-turbo-1106',
        messages=[
            {'role': 'system',
             'content': 'You provide information on incidents that occurred in the following article: ' + article.content},
            {'role': 'system',
             'content': 'There may be multiple incidents listed in a single article.  When this is the case, you must use a list of JSON responses. Multiple names, ages, and addresses may be listed in a single incident. The key for the list of incidents should always be incidents.'},
            {'role': 'system',
             'content': 'All output must be provided as an array of objects in dictionary or hashmap format, with the following keys: accused_name, accused_age, accused_location, charges, details, legal_actions.  All values must be strings.  If the article is not about a crime, the output should be N/A.'},
            {'role': 'system',
             'content': 'The JSON output should be an array of objects, with each object representing a single incident.  If there is only one incident, the array should contain only one object. Do not include a dictionary or hashmap as the root object.'},
            {'role': 'system',
             'content': "Do not include any incidents that contain Accused: or contain Charges:"},
            {'role': 'system',
             'content': "The accused location should include any street, road, avenue, or other location information along with the city or town.  If the accused location is not given, the value should be N/A."},
        ],
        response_format={'type': 'json_object'},
        temperature=0
    )

    response = completion.choices[0].message.content.strip()
    jsonified_response = json.loads(response)
    if list(jsonified_response.keys()) == ['incidents']:
        pass
    else:
        jsonified_response = {'incidents': [jsonified_response]}

    print('jsonified_response: ', jsonified_response)

    for incident in jsonified_response['incidents']:
        print('incident: ', incident)
        incident = Incident(
            cortlandStandardSource=article.url,
            incident_reported_date=article.date_published,
            accused_name=incident['accused_name'],
            accused_age=incident['accused_age'],
            accused_location=incident['accused_location'],
            charges=incident['charges'],
            details=incident['details'],
            legal_actions=incident['legal_actions'],
        )
        incidents = DBsession.query(Incident).filter(
            Incident.incident_reported_date == incident.incident_reported_date,
            Incident.accused_name == incident.accused_name,
        ).all()

        if len(incidents) > 0:
            print('Potential duplicate incident found.  Not adding to database.')
            continue
        else:
            print('No potential duplicate incidents found.  Filtering for nulls before adding to database.')
            nulls_found = 0
            if incident.accused_name == 'N/A':
                print('No accused name found.  Not adding to database.')
                return
            if incident.accused_age in ['N/A', '0', 0]:
                nulls_found += 1
            if incident.accused_location == 'N/A':
                nulls_found += 1
            if incident.charges == 'N/A':
                nulls_found += 1
            if incident.details == 'N/A':
                nulls_found += 1
            if incident.legal_actions == 'N/A':
                nulls_found += 1

            if nulls_found > 4:
                print('Too many nulls found.  Not adding to database.')
                return
            else:
                try:
                    DBsession.add(incident)
                    DBsession.commit()
                except IntegrityError as e:
                    print('Integrity error: ', e)
                    DBsession.rollback()

    article = DBsession.query(Article).filter_by(id=article.id).first()
    article.incidents_scraped = True
    DBsession.commit()

    return


def main():
    DBsession, engine = get_database_session(environment='prod')
    # get articles & sort by dates published, descending
    police_fire_articles = DBsession.query(Article).where(Article.section == 'Police/Fire').order_by(
        Article.date_published.desc()).all()
    police_fire_articles = list(police_fire_articles)
    index = 0
    for article in tqdm(police_fire_articles):
        print(article.url)
        index += 1
        scrape_unstructured_incident_details(article, DBsession)

    DBsession.close()


if __name__ == '__main__':
    main()
