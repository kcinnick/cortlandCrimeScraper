from database import Incident, get_database_session
from police_fire.data_normalization.interactive_normalize_incident_locations import choose_location_to_append
from police_fire.maps.get_lat_lng_of_addresses import get_lat_lng_of_address

from time import sleep
# identify all the incident_lat_lngs that are not in New York state

bounding_box = {
    'lat_min': 40.502009,
    'lat_max': 45.015509,
    'lng_min': -79.763379,
    'lng_max': -71.856164,
}


def is_in_new_york_state(lat, lng):
    if float(lat) < bounding_box['lat_min']:
        return False
    elif float(lat) > bounding_box['lat_max']:
        return False
    elif float(lng) < bounding_box['lng_min']:
        return False
    elif float(lng) > bounding_box['lng_max']:
        return False
    else:
        return True


def identify_incidents_outside_bounding_box(DBsession):
    incidents = DBsession.query(Incident).filter(Incident.incident_location_lat != None,
                                                 Incident.incident_location_lng != None).all()
    incidents = [incident for incident in incidents if incident.incident_location != 'N/A']

    incidents_outside_bounding_box = []
    for incident in incidents:
        if is_in_new_york_state(incident.incident_location_lat, incident.incident_location_lng):
            continue
        else:
            incidents_outside_bounding_box.append(incident)
    return incidents_outside_bounding_box


def main():
    DBsession, engine = get_database_session(environment='prod')

    incidents_outside_bounding_box = identify_incidents_outside_bounding_box(DBsession)
    print(len(incidents_outside_bounding_box))
    for incident in incidents_outside_bounding_box:
        print(incident.incident_location)
        choose_location_to_append(incident, incident.incident_location, DBsession)
        lat_lng = get_lat_lng_of_address(incident.incident_location)
        if lat_lng:
            print(lat_lng)
            incident.incident_location_lat = lat_lng[0]
            incident.incident_location_lng = lat_lng[1]
            DBsession.add(incident)
            DBsession.commit()
            sleep(1)
        else:
            print('No lat/lng found for ' + incident.incident_location)

    return


if __name__ == '__main__':
    main()
