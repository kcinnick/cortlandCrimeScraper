from sqlalchemy import func, text
from tqdm import tqdm

from database import get_database_session, Incidents, IncidentsFromPdf, ManuallyVerifiedUrls

dbSession, engine = get_database_session(environment='prod')


# for each URL in Incidents that isn't in manually_verified_urls
# print the URL, print the associated Incidents records, and ask for input
# if everything is good, add the URL to manually_verified_urls

def main():
    all_incident_records = []
    all_incident_records.extend(dbSession.query(Incidents).all())
    unique_incident_urls = []
    manually_verified_urls = [i.url for i in dbSession.query(ManuallyVerifiedUrls).all()]

    for incident in all_incident_records:
        if incident.url not in unique_incident_urls:
            if incident.url not in manually_verified_urls:
                unique_incident_urls.append(incident.url)

    for url in tqdm(unique_incident_urls):
        print(url)
        incidents = dbSession.query(Incidents).filter(Incidents.url == url).all()
        for incident in incidents:
            print(incident)
        verified = input("\nPress Enter to continue...")
        if verified.capitalize() == "Y":
            print("Adding to manually_verified_urls table.")
            dbSession.execute(text(
                f"INSERT INTO manually_verified_urls (url) VALUES ('{url}') ON CONFLICT DO NOTHING;"))
            dbSession.commit()
            print("Added to manually_verified_urls table.")
        else:
            print("Not adding to manually_verified_urls table.")

    return


if __name__ == '__main__':
    main()
