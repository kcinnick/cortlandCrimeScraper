from sqlalchemy import func
from tqdm import tqdm

from database import get_database_session, Incidents, IncidentsFromPdf

dbSession, engine = get_database_session(environment='prod')


def remove_trailing_periods(string):
    if string is None:
        return None
    if string.endswith('.'):
        return string[:-1]
    return string


def main():
    all_incident_records = dbSession.query(IncidentsFromPdf).all()
    all_incident_records.extend(dbSession.query(Incidents).all())
    for incident in tqdm(all_incident_records):
        incident.accused_location = remove_trailing_periods(incident.accused_location)
        incident.incident_location = remove_trailing_periods(incident.incident_location)
        dbSession.commit()

    return


if __name__ == '__main__':
    main()
