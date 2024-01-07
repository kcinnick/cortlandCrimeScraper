import os
from time import sleep

import requests
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
            lat_lng = get_lat_lng_of_address(incident_location)
            if lat_lng:
                print(lat_lng)
                incident.incident_location_lat = lat_lng[0]
                incident.incident_location_lng = lat_lng[1]
                DBsession.add(incident)
                DBsession.commit()
                sleep(1)
            else:
                print('No lat/lng found for ' + incident_location)
        else:
            print('No incident location found for ' + incident.url)
    return


if __name__ == '__main__':
    main()
