import ast
import os

from pydantic import BaseModel, Field
from simpleaichat import AIChat
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

from database import Article, Incidents, get_database_session, IncidentsWithErrors, Persons
from police_fire.utilities import add_or_get_person

ai = AIChat(
    console=False,
    save_messages=False,  # with schema I/O, messages are never saved
    model="gpt-4",
    params={"temperature": 0.0},
    api_key=os.getenv('OPENAI_API_KEY'),
)


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
    #print('Article content: ', article.content)
    query = "List all of the incident details provided in the following article that do not start with Accused:, in the original language of the article.  Use an Python style array of Python-style dictionaries with the keys \'accused_name\', \'accused_age\', \'accused_location\', \'charges\', \'details\', \'legal_actions\' if there is more than one incident specified. All values need to be strings. If the article is not about a crime, the output should be N/A." + article_content
    response = ai(query)
    print(article_url)
    if response == 'N/A':
        print('No incident details found.  Not adding to database.')
        print(article_url)
        return
    try:
        parsed_response = ast.literal_eval(response)
    except TypeError as e:
        incidentWithError = IncidentsWithErrors(
            url=article_url
        )
        DBsession.add(incidentWithError)
        DBsession.commit()
        return
    except SyntaxError as e:
        incidentWithError = IncidentsWithErrors(
            url=article_url
        )
        DBsession.add(incidentWithError)
        DBsession.commit()
        return

    for response in tqdm(parsed_response, desc='Parsing incident details'):
        charges = dict(response).get('charges')
        if charges:
            if type(response['charges']) == list:
                response['charges'] = '; '.join(response['charges'])

        accused_name = dict(response).get('accused_name')
        accused_location = dict(response).get('accused_location')
        incident = Incidents(
            article_id=article_id,
            url=article_url,
            incident_reported_date=article_date_published,
            accused_person_id=add_or_get_person(DBsession, accused_name),
            accused_age=response['accused_age'],
            accused_location=accused_location,
            charges=charges,
            details=response['details'],
            legal_actions=response['legal_actions'],
            structured_source=False
        )

        # look up potentially-duplicated incidents first.
        # do not add this incident to the database if it's a duplicate.

        incidents = DBsession.query(Incidents).filter(
            Incidents.url == article_url,
            Incidents.accused_person_id == incident.accused_person_id,
            Incidents.accused_age == incident.accused_age,
            Incidents.accused_location == incident.accused_location,
            Incidents.charges == incident.charges
        ).all()

        accused_person = DBsession.query(Persons).filter(
            Persons.id == incident.accused_person_id
        ).first()

        if accused_person:
            accused_person_name = accused_person.name
        else:
            # Handle the case where no person is found
            accused_person_name = None  # or some default value
        if len(incidents) > 0:
            print('Potential duplicate incident found.  Not adding to database.')
            continue
        else:
            print('No potential duplicate incidents found.  Filtering for nulls before adding to database.')
            nulls_found = 0
            if accused_person_name == 'N/A':
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
    index = 0
    for article in tqdm(police_fire_articles):
        article_id, article_url, article_content, article_date_published = article.id, article.url, article.content, article.date_published
        index += 1
        scrape_unstructured_incident_details(article_id, article_url, article_content, article_date_published, DBsession)

    DBsession.close()


if __name__ == '__main__':
    main()
