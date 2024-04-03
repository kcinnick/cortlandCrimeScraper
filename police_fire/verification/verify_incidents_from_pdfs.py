# script used to manually verify that all incidents were added correctly to the database
# step 1: collect unique PDF sources from incidents table
# step 2: for each unique PDF source, print the source and all incidents associated with the source
# step 3: for each incident, print the incident details and a y/n prompt to verify the incident
# step 4: if the incident details are incorrect, update the incident in the database
# step 5: if the incident details are correct, mark the incident as verified in the database
# step 6: repeat steps 2-5 until all incidents are verified
from pathlib import Path
import webbrowser

from tqdm import tqdm

from database import get_database_session
from models.article import Article
from models.incident import Incident
from models.pdf import Pdf
from police_fire.maps import get_lat_lng_of_addresses

DBsession, engine = get_database_session(environment='prod')


def extract_date_from_path(file_path):
    # Convert the file path to a Path object
    path = Path(file_path)

    # Extract the year, month, and day parts of the path
    # Assuming the structure is always \pdfs\year\month\day\...
    parts = path.parts
    pdfs_index = parts.index('pdfs')  # Find the index of 'pdfs' in the path
    year, month, day = parts[pdfs_index + 1:pdfs_index + 4]  # Extract year, month, day

    # Format year, month, day, ensuring day and month are zero-padded to two digits
    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return formatted_date


def get_unique_pdf_sources():
    unique_pdf_sources = (
        DBsession.query(Incident.source)
        .filter(Incident.source.like('pdf%'))
        .distinct()
        .all()
    )

    # filter out pdfs that have already been verified
    unverified_pdf_sources = []
    for pdf_source in unique_pdf_sources:
        pdf_source = pdf_source[0]
        split_pdf_source = pdf_source.split('/')
        new_pdf_source = []
        for part in split_pdf_source:
            if len(part) == 1:
                part = f'0{part}'
            new_pdf_source.append(part)
        pdf_source = '/'.join(new_pdf_source)
        print('pdf_source:', pdf_source)


        full_path = fr'C:\Users\Nick\PycharmProjects\cortlandStandardScraper\{pdf_source}\pages\police_fire_page.pdf'.replace(
            '/', '\\')
        # check if the pdf has been verified
        pdf_object = DBsession.query(Pdf).filter_by(path=full_path).first()
        if not pdf_object:
            unverified_pdf_sources.append(pdf_source)
        elif not pdf_object.incidents_verified:
            unverified_pdf_sources.append(pdf_source)
        else:
            print(f'pdf {pdf_source} has already been verified.')

    print(len(unverified_pdf_sources), 'unverified pdf sources found.')
    return unverified_pdf_sources


def handle_incorrect_number_of_incidents(pdf_object, date_published, pdf_path):
    number_of_missing_incidents = int(input("How many missing incidents are there? "))
    # if number_of_incidents == 0, delete the incidents associated with the article from the database
    # and set incidents_verified to True for the article
    if number_of_missing_incidents == 0:
        incidents = DBsession.query(Incident).filter_by(source=pdf_path).all()
        for incident in incidents:
            DBsession.delete(incident)
        pdf_object.incidents_verified = True
        DBsession.commit()
        return

    for i in range(number_of_missing_incidents):
        print(f'\nInputting details for missing incident #{str(i + 1)}.\n')
        # prompt for the details of each incident
        incident_reported_date = date_published
        accused_name = input("Accused Name: ")
        accused_age = input("Accused Age: ")
        accused_location = input("Accused Location: ")
        charges = input("Charges: ")
        details = input("Details: ")
        legal_actions = input("Legal Actions: ")
        incident_date = input("Incident Date: ")
        incident_location = input("Incident Location: ")
        incident_location_lat, incident_location_lng = get_lat_lng_of_addresses.get_lat_lng_of_address(
            incident_location)
        source = pdf_path

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


def verify_incidents_for_pdf(pdf_path):
    full_path = fr'C:\Users\Nick\PycharmProjects\cortlandStandardScraper\{pdf_path}\pages\police_fire_page.pdf'.replace(
        '/', '\\')
    date_published = extract_date_from_path(full_path)
    print(f"Opening {full_path} in web browser.")
    webbrowser.open(full_path)
    # an article's incidents are ones where the source == article.url
    pdf_object = DBsession.query(Pdf).filter_by(path=full_path).first()
    # if pdf_object doesn't exist, create a new Pdf object
    if not pdf_object:
        pdf_object = Pdf(path=full_path, date_published=date_published, incidents_verified=False)
        DBsession.add(pdf_object)
        DBsession.commit()
    incidents = DBsession.query(Incident).filter_by(source=pdf_path).all()
    article_incidents_verified = []
    print(f"Number of Incidents in database: {len(incidents)}\n")
    number_of_incidents_response = input('Is this correct? (y/n): ')
    if number_of_incidents_response == 'n':
        handle_incorrect_number_of_incidents(pdf_object, date_published, pdf_path)
        # grab the updated incidents from the database
        incidents = DBsession.query(Incident).filter_by(source=pdf_path).all()
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
            pdf_object.incidents_verified = False
            DBsession.commit()
            return

    # if all incidents are verified, mark the article as verified
    if len(article_incidents_verified) == len(incidents):
        pdf_object.incidents_verified = True
        DBsession.commit()
        print("\nArticle verified.")
    else:
        print("\nArticle not verified.")

    return


def main():
    unique_pdf_sources = get_unique_pdf_sources()
    for pdf_path in tqdm(unique_pdf_sources):
        print('pdf_path:', pdf_path)
        verify_incidents_for_pdf(pdf_path)


if __name__ == '__main__':
    main()
