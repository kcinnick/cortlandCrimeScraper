from sqlalchemy import func
from tqdm import tqdm

from database import get_database_session, Incidents, IncidentsFromPdf


def remove_trailing_periods(string):
    if string is None:
        return None
    if string.endswith('.'):
        return string[:-1]
    return string


def finish_or_replace_locations(incident):
    if 'The text' in incident.incident_location:
        incident.incident_location = incident.incident_location = 'N/A'
    elif ' AI ' in incident.incident_location:
        incident.incident_location = incident.incident_location = 'N/A'
    if incident.incident_location.endswith('Homer'):
        incident.incident_location = incident.incident_location.replace('Homer', 'Homer, New York')
    elif incident.incident_location.endswith('Cortland'):
        incident.incident_location = incident.incident_location.replace('Cortland', 'Cortland, New York')
    elif incident.incident_location.endswith('Cortlandville'):
        incident.incident_location = incident.incident_location.replace('Cortlandville', 'Cortlandville, New York')
    elif incident.incident_location.endswith('Lansing'):
        incident.incident_location = incident.incident_location.replace('Lansing', 'Lansing, New York')
    elif incident.incident_location.endswith('Dryden'):
        incident.incident_location = incident.incident_location.replace('Dryden', 'Dryden, New York')
    elif incident.incident_location.endswith('Ithaca'):
        incident.incident_location = incident.incident_location.replace('Ithaca', 'Ithaca, New York')
    elif incident.incident_location.endswith('Cortland County'):
        incident.incident_location = incident.incident_location.replace('Cortland County', 'Cortland County, New York')
    else:
        print(incident.incident_location)

    return incident


def main(environment='prod'):
    dbSession, engine = get_database_session(environment=environment)
    all_incident_records = dbSession.query(IncidentsFromPdf).all()
    all_incident_records.extend(dbSession.query(Incidents).all())
    for incident in tqdm(all_incident_records):
        incident.accused_location = remove_trailing_periods(incident.accused_location)
        incident.incident_location = remove_trailing_periods(incident.incident_location)
        if not incident.incident_location:
            continue
        incident = finish_or_replace_locations(incident)
        dbSession.add(incident)
        dbSession.commit()

    return


if __name__ == '__main__':
    main()
