import os

from pydantic import BaseModel, Field
from simpleaichat import AIChat
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

from database import Article, Incidents, get_database_session

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
    query = "List all of the incident details provided in the following article, in the original language of the article where possible.  Use an array of dictionaries if there is more than one incident specified. If the article is not about a crime, the output should be N/A." + article_content
    response = ai(query, output_schema=get_incident_metadata)
    incident = Incidents(
        article_id=article_id,
        url=article_url,
        incident_reported_date=article_date_published,
        accused_name=response['accused_name'],
        accused_age=str(response['accused_age']),
        accused_location=response['accused_location'],
        charges=response['charges'],
        details=response['details'],
        legal_actions=response['legal_actions'],
        structured_source=False
    )

    # look up potentially-duplicated incidents first.
    # do not add this incident to the database if it's a duplicate.

    incidents = DBsession.query(Incidents).filter(
        Incidents.url == article_url,
        Incidents.accused_name == incident.accused_name,
        Incidents.accused_age == incident.accused_age,
        Incidents.accused_location == incident.accused_location,
        Incidents.charges == incident.charges
    ).all()

    if len(incidents) > 0:
        print('Potential duplicate incident found.  Not adding to database.')
        return
    else:
        print('No potential duplicate incidents found.  Filtering for nulls before adding to database.')
        nulls_found = 0
        print(incident.url)
        print(incident.accused_name)
        if incident.accused_name == 'N/A':
            nulls_found += 1
        if incident.accused_age in ['N/A', '0', 0]:
            nulls_found += 1
        if incident.accused_location == 'N/A':
            nulls_found += 1
        print(incident.accused_location)
        if incident.charges == 'N/A':
            nulls_found += 1
        print(incident.charges)
        if incident.details == 'N/A':
            nulls_found += 1
        print(incident.details)
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
    DBsession, engine = get_database_session(test=False)
    police_fire_articles = DBsession.query(Article).where(Article.section == 'Police/Fire')
    police_fire_articles = list(police_fire_articles)
    index = 0
    try:
        for article in tqdm(police_fire_articles):
            article_id, article_url, article_content, article_date_published = article.id, article.url, article.content, article.date_published
            index += 1
            #pprint('Article content: ', article.content)
            scrape_unstructured_incident_details(article_id, article_url, article_content, article_date_published, DBsession)
    except Exception as e:
        print(e)
    finally:
        DBsession.close()


if __name__ == '__main__':
    main()
