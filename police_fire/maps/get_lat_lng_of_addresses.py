import os
from pprint import pprint
from time import sleep

import requests
from sqlalchemy import or_
from tqdm import tqdm

from database import get_database_session, Incidents, IncidentsFromPdf
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
        pprint(resp_json_payload)
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
    DBsession, engine = get_database_session(test=False)
    incidents = DBsession.query(IncidentsFromPdf).filter(or_(Incidents.incident_location_lat == None, Incidents.incident_location_lng == None)).all()
    for incident in tqdm(incidents):
        incident_location = get_incident_location(DBsession, incident)
        if incident_location:
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
