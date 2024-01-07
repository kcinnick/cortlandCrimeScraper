import os
from pprint import pprint
from time import sleep

import requests
from sqlalchemy import or_
from tqdm import tqdm

from database import get_database_session, Incident
from police_fire.utilities import get_incident_location_from_details


def get_lat_lng_of_address(address):
    response = requests.get(
        f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={os.getenv("GOOGLE_MAPS_API_KEY")}')
    resp_json_payload = response.json()

    if resp_json_payload['status'] == 'OK':
        lat = resp_json_payload['results'][0]['geometry']['location']['lat']
        lng = resp_json_payload['results'][0]['geometry']['location']['lng']
        return lat, lng
    else:
        print('get_lat_lng_of_address: ', resp_json_payload['status'])
        with open('get_lat_lng_of_address_errors.txt', 'a') as f:
            f.write(f'{address}\n')
        return None, None


def get_incident_location(DBsession, incident):
    if incident.incident_location:
        return incident.incident_location
    else:
        incident_location = get_incident_location_from_details(incident.details)
        if incident_location:
            incident.incident_location = incident_location
            DBsession.add(incident)
            DBsession.commit()
            return incident_location
        else:
            return None


def choose_location_to_append(incident, incident_location, DBsession):
    print('Press 1 to append \'Cortland, New York\' to incident location.')
    print('Press 2 to append \'New York\' to incident location.')
    print('Press Enter to skip.')
    choice = input()
    if choice == '1':
        incident_location = incident_location + ', Cortland, New York'
        incident.incident_location = incident_location
        DBsession.add(incident)
        DBsession.commit()
    elif choice == '2':
        incident_location = incident_location + ', New York'
        incident.incident_location = incident_location
        DBsession.add(incident)
        DBsession.commit()
    else:
        return


def main():
    with open('get_lat_lng_of_address_errors.txt', 'w') as f:
        f.write('address\n')
    DBsession, engine = get_database_session(environment='prod')
    incidents = DBsession.query(Incident).filter(Incident.incident_location_lat == None,).all()
    for incident in tqdm(incidents):
        incident_location = get_incident_location(DBsession, incident)
        if incident_location.strip() == 'N/A':
            continue
        if incident_location:
            print(incident_location)
            choose_location_to_append(incident, incident_location, DBsession)

    return


if __name__ == '__main__':
    main()
