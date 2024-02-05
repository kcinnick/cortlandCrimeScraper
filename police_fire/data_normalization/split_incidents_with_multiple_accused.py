# first, identify incidents with multiple accused
# split the ages, addresses if necessary, and ID which charges belong to which accused
# then, create a new incident for each accused
# finally, delete the incident with multiple accused
import re

from database import Incident, get_database_session


def split_incidents_with_multiple_accused(DBsession):
    all_incidents = DBsession.query(Incident).all()
    print(str(len(all_incidents)) + ' incidents found.')
    multiple_accused = [i for i in all_incidents if ',' in i.accused_name]
    print(str(len(multiple_accused)) + ' incidents with multiple accused found.')
    return multiple_accused


def clean_split(incident, accused_names, accused_ages, addresses, DBsession):
    #print('----')
    split_charges_by_sentence = [i for i in incident.charges.split('.') if len(i.strip()) > 1]
    raw_charges = []
    print('Splitting incident ' + str(incident.id) + ' with ' + str(len(accused_names)) + ' accused.')
    for i in range(len(accused_names)):

        try:
            address = addresses[i]
            age = accused_ages[i]
        except IndexError:
            # if the accused_names live at the same address, or the address is just the city/town name,
            # then the address list will be shorter than the accused_names list. In this case, we'll just
            # use the last address in the list.
            address = addresses[-1]
            age = accused_ages[-1]

        print('Creating new charge for ' + accused_names[i] + ' at ' + address)
        for split_charge in split_charges_by_sentence:
            print('Split charge: ' + split_charge)
            split_name = accused_names[i].split(' ')
            last_name = split_name[-1]
            if last_name in split_charge:
                #print('Name found in charge: ' + name)
                #print('Adding charge to ' + accused_names[i] + ' at ' + address)
                #print('----')
                raw_charge = {}
                raw_charge['accused_name'] = accused_names[i]
                raw_charge['accused_age'] = age
                raw_charge['accused_location'] = address
                raw_charge['charge'] = split_charge
                raw_charge['incident_id'] = incident.id
                raw_charges.append(raw_charge)
            else:
                print('Name not found in charge: ' + last_name)
                raw_charge = {}
                raw_charge['accused_name'] = accused_names[i]
                raw_charge['accused_age'] = age
                raw_charge['accused_location'] = address
                raw_charge['charge'] = split_charge
                raw_charge['incident_id'] = incident.id
                raw_charges.append(raw_charge)

    return raw_charges


def split_incident(incident, DBsession):
    accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
    accused_locations = [i.strip() for i in incident.accused_location.split(';') if i.strip() != '']
    accused_ages = [i.strip() for i in incident.accused_age.split(',') if i.strip() != '']

    # the 'cleanest split' is when the number of accused names matches the number of addresses
    if len(accused_names) == len(accused_locations):
        raw_charges = clean_split(incident, accused_names, accused_ages, accused_locations, DBsession)
    elif len(accused_locations) == 1:
        #print('Only one address found.  Splitting accused names and ages.')
        accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
        raw_charges = clean_split(incident, accused_names, accused_ages, [accused_locations[0]], DBsession)
    else:
        raise Exception(f'Unable to split incident.  Please check the following: {incident}')

    if len(raw_charges) == 0:
        raise Exception('No charges found for incident ' + str(incident.id) + '.')

    return raw_charges


def main():
    DBsession, engine = get_database_session(environment='dev')
    multiple_accused_incidents = split_incidents_with_multiple_accused(DBsession)
    for incident in multiple_accused_incidents:
        split_incident(incident, DBsession)


if __name__ == '__main__':
    main()
