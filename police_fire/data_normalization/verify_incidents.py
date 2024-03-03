# script used to manually verify that all incidents were added correctly to the database
# step 1: collect all Article objects from the database that do not have incidents_verified set to True
# step 2: for each article from step 1, print the article's URL and all incidents associated with the article
# step 3: for each incident, print the incident details and a y/n prompt to verify the incident
# step 4: if the incident details are incorrect, update the incident in the database
# step 5: if the incident details are correct, mark the incident as verified in the database
# step 6: repeat steps 2-5 until all incidents are verified

from database import get_database_session
from models.article import Article
from models.incident import Incident

DBsession, engine = get_database_session(environment='dev')

# filter by both if incidents_scraped == True and incidents_verified == False
articles = DBsession.query(Article).filter_by(incidents_scraped=True, incidents_verified=False).all()


def verify_incidents_for_article(article):
    print(f"\nArticle URL: {article.url}")
    # an article's incidents are ones where the source == article.url
    incidents = DBsession.query(Incident).filter_by(source=article.url).all()
    article_incidents_verified = []
    print(f"Number of Incidents: {len(incidents)}")
    number_of_incidents_response = 'Is this correct? (y/n): '
    if input(number_of_incidents_response) == 'n':
        print("Please update the incidents in the database.")
        return
    for incident in incidents:
        print(f"Accused Name: {incident.accused_name}")
        print(f"Accused Age: {incident.accused_age}")
        print(f"Accused Location: {incident.accused_location}")
        print(f"Charges: {incident.charges}")
        print(f"Details: {incident.details}")
        print(f"Legal Actions: {incident.legal_actions}")
        # prompt to verify the incident
        verified = input("Is this incident correct? (y/n): ")
        if verified == 'y':
            article_incidents_verified.append(incident)
        else:
            print("Please update the incident in the database.")
            article.incidents_verified = False
            DBsession.commit()
            return

    # if all incidents are verified, mark the article as verified
    if len(article_incidents_verified) == len(incidents):
        article.incidents_verified = True
        DBsession.commit()
        print("Article verified.")
    else:
        print("Article not verified.")

    return


def main():
    for article in articles:
        verify_incidents_for_article(article)

    return


if __name__ == '__main__':
    main()
