# This script is used to reload the incidents data from the source after consolidating Incidents and IncidentsFromPdf
# into Incidents. It is not used in the normal scraping process.
from database import get_database_session, Incident, Incidents, IncidentsFromPdf

prod_DBsession, prod_engine = get_database_session(environment='prod')
dev_DBsession, dev_engine = get_database_session(environment='dev')


def load_incidents_from_urls():
    # take each incident from `Incidents` and add it to `Incident` if it doesn't already exist
    for incident in prod_DBsession.query(Incidents).all():
        if dev_DBsession.query(Incident).filter_by(source=incident.url).filter_by(
                accused_name=incident.accused_name).filter_by(details=incident.details).first():
            print(f'Incident already exists for {incident.url}. Skipping.')
            continue

        new_incident = Incident(
            incident_reported_date=incident.incident_reported_date,
            accused_name=incident.accused_name,
            accused_age=incident.accused_age,
            accused_location=incident.accused_location,
            charges=incident.charges,
            details=incident.details,
            legal_actions=incident.legal_actions,
            incident_date=incident.incident_date,
            incident_location=incident.incident_location,
            incident_location_lat=incident.incident_location_lat,
            incident_location_lng=incident.incident_location_lng,
            source=incident.url,
        )
        dev_DBsession.add(new_incident)
        dev_DBsession.commit()
        print(f'Incident added for {"article_" + str(incident.article_id)}.')

    return


def load_incidents_from_pdf():
    incident_count = 0
    # take each incident from `IncidentsFromPdf` and add it to `Incident` if it doesn't already exist
    for incident in prod_DBsession.query(IncidentsFromPdf).all():
        incident_count += 1
        source_pdf_path = str(incident.incident_reported_date).replace('-', '/')
        if dev_DBsession.query(Incident).filter_by(source='pdfs/' + source_pdf_path).filter_by(
                accused_name=incident.accused_name).filter_by(details=incident.details).first():
            print(f'Incident already exists for {incident.source}. Skipping.')
            continue

        new_incident = Incident(
            incident_reported_date=incident.incident_reported_date,
            accused_name=incident.accused_name,
            accused_age=incident.accused_age,
            accused_location=incident.accused_location,
            charges=incident.charges,
            details=incident.details,
            legal_actions=incident.legal_actions,
            incident_date=incident.incident_date,
            incident_location=incident.incident_location,
            incident_location_lat=incident.incident_location_lat,
            incident_location_lng=incident.incident_location_lng,
            source="pdfs/" + source_pdf_path,
        )
        dev_DBsession.add(new_incident)
        dev_DBsession.commit()
        print(f'Incident added for {source_pdf_path}.')

    print(f'Added {incident_count} incidents from pdfs.')
    return


def main():
    load_incidents_from_urls()
    load_incidents_from_pdf()
    return


if __name__ == '__main__':
    main()
