# first, identify incidents with multiple accused
# split the ages, addresses if necessary, and ID which charges belong to which accused
# then, create a new incident for each accused
# finally, delete the incident with multiple accused
import re

from database import get_database_session
from models.incident import Incident


def split_incidents_with_multiple_accused(DBsession):
    all_incidents = DBsession.query(Incident).all()
    print(str(len(all_incidents)) + ' incidents found.')
    multiple_accused = [i for i in all_incidents if ',' in i.accused_name]
    print(str(len(multiple_accused)) + ' incidents with multiple accused found.')
    return multiple_accused


def create_charge_dict(incident, accused_name, accused_age, accused_location, charge):
    charge_dict = {}
    charge_dict['incident_id'] = incident.id
    charge_dict['accused_name'] = accused_name
    charge_dict['accused_age'] = accused_age
    charge_dict['accused_location'] = accused_location
    charge_dict['charge'] = charge
    return charge_dict


def clean_split(incident, accused_names, accused_ages, addresses, DBsession):
    # print('----')
    split_charges_by_sentence = [i for i in incident.spellchecked_charges.split('.') if len(i.strip()) > 1]
    if len(split_charges_by_sentence) == 1:
        # try splitting by semicolon
        split_charges_by_sentence = [i for i in incident.spellchecked_charges.split(';') if len(i.strip()) > 1]

    raw_charges = []
    print('Splitting incident ' + str(incident.id) + ' with ' + str(len(accused_names)) + ' accused.')
    for i in range(len(accused_names)):
        print('Accused name: ' + accused_names[i])
        split_name = accused_names[i].split(' ')
        last_name = split_name[-1]

        try:
            address = addresses[i]
        except IndexError:
            # if the accused_names live at the same address, or the address is just the city/town name,
            # then the address list will be shorter than the accused_names list. In this case, we'll just
            # use the last address in the list.
            address = addresses[-1]

        if address is None:
            address = 'Unknown'

        print('Accused address: ' + address)
        try:
            age = accused_ages[i]
        except IndexError:
            # accused age is not always given. in this instance, use None
            age = None

        print('Creating new charge for ' + accused_names[i] + ' at ' + address)
        for split_charge in split_charges_by_sentence:
            print('Split charge: ' + split_charge)
            if last_name in split_charge:
                raw_charge_dict = create_charge_dict(incident, accused_names[i], age, address, split_charge)
                raw_charges.append(raw_charge_dict)
            else:
                # check if any of the other last names are in the charge
                other_last_name_found = False
                for name in accused_names:
                    if name.split(' ')[-1] in split_charge:
                        raw_charge_dict = create_charge_dict(incident, name, age, address, split_charge)
                        raw_charges.append(raw_charge_dict)
                        other_last_name_found = True
                        break
                if not other_last_name_found:
                    # if the charge doesn't contain any of the accused names, then it's likely a charge for all
                    # accused.  We'll add it to all accused.
                    raw_charge_dict = create_charge_dict(incident, accused_names[i], age, address, split_charge)
                    raw_charges.append(raw_charge_dict)

    return raw_charges


def split_incident(incident, DBsession):
    accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
    accused_locations = [i.strip() for i in incident.accused_location.split(';') if i.strip() != '']
    accused_ages = [i.strip() for i in incident.accused_age.split(',') if i.strip() != '']

    # the 'cleanest split' is when the number of accused names matches the number of addresses
    if len(accused_names) == len(accused_locations):
        raw_charges = clean_split(incident, accused_names, accused_ages, accused_locations, DBsession)
    elif len(accused_locations) == 1:
        # print('Only one address found.  Splitting accused names and ages.')
        accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
        raw_charges = clean_split(incident, accused_names, accused_ages, [accused_locations[0]], DBsession)
    elif len(accused_locations) == 0:
        # print('No addresses found.  Splitting accused names and ages.')
        accused_names = [i.strip() for i in incident.accused_name.split(',') if i.strip() != '']
        raw_charges = clean_split(incident, accused_names, accused_ages, [None] * len(accused_names), DBsession)
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
