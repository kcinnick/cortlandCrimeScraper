# script used to manually verify that all incidents were added correctly to the database
# step 1: collect all Article objects from the database that do not have incidents_verified set to True
# step 2: for each article from step 1, print the article's URL and all incidents associated with the article
# step 3: for each incident, print the incident details and a y/n prompt to verify the incident
# step 4: if the incident details are incorrect, update the incident in the database
# step 5: if the incident details are correct, mark the incident as verified in the database
# step 6: repeat steps 2-5 until all incidents are verified
from tqdm import tqdm

from database import get_database_session
from models.article import Article
from models.incident import Incident
from police_fire.maps import get_lat_lng_of_addresses

DBsession, engine = get_database_session(environment='prod')

# filter by both if incidents_scraped == True and incidents_verified == False
articles = DBsession.query(Article).filter_by(incidents_scraped=True, incidents_verified=False).all()


def handle_incorrect_number_of_incidents(article):
    number_of_missing_incidents = int(input("How many missing incidents are there? "))
    # if number_of_incidents == 0, delete the incidents associated with the article from the database
    # and set incidents_verified to True for the article
    if number_of_missing_incidents == 0:
        incidents = DBsession.query(Incident).filter_by(source=article.url).all()
        for incident in incidents:
            DBsession.delete(incident)
        article.incidents_verified = True
        DBsession.commit()
        return

    for i in range(number_of_missing_incidents):
        print(f'\nInputting details for missing incident #{str(i + 1)}.\n')
        # prompt for the details of each incident
        incident_reported_date = article.date_published
        accused_name = input("Accused Name: ")
        accused_age = input("Accused Age: ")
        accused_location = input("Accused Location: ")
        charges = input("Charges: ")
        details = input("Details: ")
        legal_actions = input("Legal Actions: ")
        incident_date = input("Incident Date: ")
        incident_location = input("Incident Location: ")
        incident_location_lat, incident_location_lng = get_lat_lng_of_addresses.get_lat_lng_of_address(incident_location)
        source = article.url

        # create a new Incident object and add it to the database
        new_incident = Incident(
            incident_reported_date=incident_reported_date,
            accused_name=accused_name,
            accused_age=accused_age,
            accused_location=accused_location,
            charges=charges,
            details=details,
            legal_actions=legal_actions,
            incident_location=incident_location,
            incident_date=incident_date,
            incident_location_lat=incident_location_lat,
            incident_location_lng=incident_location_lng,
            source=source
        )
        DBsession.add(new_incident)
        DBsession.commit()

    return


def verify_incidents_for_article(article):
    print(f"\nArticle URL: {article.url}")
    # an article's incidents are ones where the source == article.url
    incidents = DBsession.query(Incident).filter_by(source=article.url).all()
    article_incidents_verified = []
    print(f"Number of Incidents in database: {len(incidents)}\n")
    number_of_incidents_response = input('Is this correct? (y/n): ')
    if number_of_incidents_response == 'n':
        handle_incorrect_number_of_incidents(article)
        # grab the updated incidents from the database
        incidents = DBsession.query(Incident).filter_by(source=article.url).all()
    for incident in incidents:
        print('\n')
        print(f"Accused Name: {incident.accused_name}")
        print(f"Accused Age: {incident.accused_age}")
        print(f"Accused Location: {incident.accused_location}")
        print(f"Charges: {incident.charges}")
        print(f"Details: {incident.details}")
        print(f"Legal Actions: {incident.legal_actions}")
        # prompt to verify the incident
        print('\n')
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
        print("\nArticle verified.")
    else:
        print("\nArticle not verified.")

    return


def main():
    print(len(articles), 'articles with unverified incidents found.')
    for article in articles:
        verify_incidents_for_article(article)

    return


if __name__ == '__main__':
    main()
