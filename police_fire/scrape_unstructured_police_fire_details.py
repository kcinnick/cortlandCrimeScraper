import json
import os

from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

from database import Article, Incident, get_database_session

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class get_incident_metadata(BaseModel):
    """Event information"""

    article_url: str = Field(description="URL of the article")
    accused_name: str = Field(description="Name of the accused.")
    accused_age: int = Field(description="Age of the accused if given.")
    accused_location: str = Field(description="Location of the accused if given.")
    charges: str = Field(description="Charges against the accused.")
    details: str = Field(description="Details of the incident.")
    legal_actions: str = Field(description="Legal actions taken against the accused.")


# returns a dict, with keys ordered as in the schema

def scrape_unstructured_incident_details(article_id, article_url, article_content, article_date_published, DBsession):
    # print('Article content: ', article.content)

    completion = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system',
             'content': 'You provide information on incidents that occurred in the following article: ' + article_content},
            {'role': 'system',
             'content': 'There may be multiple incidents listed in a single article.  When this is the case, you must use a list of JSON responses. Multiple names, ages, and addresses may be listed in a single incident.'},
            {'role': 'system',
             'content': 'All output must be provided as an array of objects in dictionary or hashmap format, with the following keys: accused_name, accused_age, accused_location, charges, details, legal_actions.  All values must be strings.  If the article is not about a crime, the output should be N/A.'},
            {'role': 'system',
             'content': 'The JSON output should be an array of objects, with each object representing a single incident.  If there is only one incident, the array should contain only one object. Do not include a dictionary or hashmap as the root object.'},
            {'role': 'system',
             'content': "Do not include any incidents that contain Accused: or contain Charges:"},
            {'role': 'system',
             'content': "The accused location should include any street, road, avenue, or other location information along with the city or town.  If the accused location is not given, the value should be N/A."},
        ],
        temperature=0
    )

    response = completion.choices[0].message.content.strip()
    jsonified_response = json.loads(response)

    for incident in jsonified_response:
        print('incident: ', incident)
        incident = Incident(
            source=article_url,
            incident_reported_date=article_date_published,
            accused_name=incident['accused_name'],
            accused_age=incident['accused_age'],
            accused_location=incident['accused_location'],
            charges=incident['charges'],
            details=incident['details'],
            legal_actions=incident['legal_actions'],
        )
        incidents = DBsession.query(Incident).filter(
            Incident.source == article_url,
            Incident.accused_name == incident.accused_name,
            Incident.accused_age == incident.accused_age,
            Incident.accused_location == incident.accused_location,
            Incident.charges == incident.charges
        ).all()

        if len(incidents) > 0:
            print('Potential duplicate incident found.  Not adding to database.')
            continue
        else:
            print('No potential duplicate incidents found.  Filtering for nulls before adding to database.')
            nulls_found = 0
            if incident.accused_name == 'N/A':
                nulls_found += 1
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

    return


def main():
    DBsession, engine = get_database_session(environment='prod')
    police_fire_articles = DBsession.query(Article).where(Article.section == 'Police/Fire')
    police_fire_articles = list(police_fire_articles)
    # reverse list
    police_fire_articles = police_fire_articles[::-1]
    index = 0
    for article in tqdm(police_fire_articles):
        article_id, article_url, article_content, article_date_published = article.id, article.url, article.content, article.date_published
        index += 1
        scrape_unstructured_incident_details(article_id, article_url, article_content, article_date_published,
                                             DBsession)

    DBsession.close()


if __name__ == '__main__':
    main()
