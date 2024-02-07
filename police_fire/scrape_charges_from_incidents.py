import re
from pprint import pprint

from tqdm import tqdm

from database import get_database_session
from models.incident import Incident
from models.charges import Charges

from police_fire.data_normalization.split_incidents_with_multiple_accused import split_incident

DBsession, engine = get_database_session(environment='dev')


def categorize_charges(incident_id, charges, accused_name):
    # Regular expression to match charge descriptions
    # The regex captures all text up to target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|midemeanor|misdemean-or|traffic infractions?|traffic violations|violations|violation|infractions?)"
    # Find all matches
    matches = re.findall(regex, charges, re.IGNORECASE | re.DOTALL)

    categorized_charges = {
        'felonies': [],
        'misdemeanors': [],
        'violations': [],
        'traffic_infraction': [],
        'uncategorized': []
    }

    if len(matches) == 0:
        categorized_charges['uncategorized'].append({
            'original_charge_description': charges,
            'cleaned_charge_description': charges,
            'charge_type': 'uncategorized',
            'incident_id': incident_id,
            'accused_name': accused_name
        })

    for match in matches:
        charge_description, charge_type = match
        original_charge_description = charge_description

        charge_description = charge_description.strip().rstrip(',')

        # get rid of ', a' at the end of the charge description
        if charge_description.endswith(', a '):
            charge_description = charge_description[:-4]

        if charge_description.endswith(', a'):
            charge_description = charge_description[:-3]

        if charge_description.startswith('; '):
            charge_description = charge_description[2:]

        if charge_description.endswith(', '):
            charge_description = charge_description[:-2]

        cleaned_charge_description = charge_description

        # Categorize based on charge type
        if 'felony' in charge_type.lower():
            categorized_charges['felonies'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident_id,
                'accused_name': accused_name
            })
        elif 'felonies' in charge_type.lower():
            categorized_charges['felonies'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident_id,
                'accused_name': accused_name
            })
        elif 'misdemeanor' in charge_type.lower():
            categorized_charges['misdemeanors'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'misdemeanor',
                'incident_id': incident_id,
                'accused_name': accused_name
            })
        elif 'violation' in charge_type.lower():
            categorized_charges['misdemeanors'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'violation',
                'incident_id': incident_id,
                'accused_name': accused_name
            })
        elif 'infraction' in charge_type.lower():
            categorized_charges['traffic_infraction'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'traffic_infraction',
                'incident_id': incident_id,
                'accused_name': accused_name
            })
        else:
            raise Exception(f'Incident ID=={incident_id} - Charge type not found: ' + charge_description)

    return categorized_charges


def separate_charges_from_charge_descriptions(charges):
    if not charges:
        return None
    # fix missing spaces

    separated_charges = charges.split(', ')

    # clean separated charges
    separated_charges = [charge.strip() for charge in separated_charges]
    separated_charges = [charge.lstrip('.') for charge in separated_charges]
    separated_charges = [charge.lstrip('; ') for charge in separated_charges]
    separated_charges = [charges.replace('and ', '') for charges in separated_charges]

    return separated_charges


def split_charges_by_and(charges, charge_type):
    charges_to_rename = {
        # occasionally, the word 'and' is part of a charge description
        # and not a separator.  In these cases, we'll remove the word
        # and replace it with 'or'.
        'speed not reasonable and prudent': 'speed not reasonable or prudent',
        'one count of failure to provide proper food and drink to an impounded animal': 'one count of failure to provide proper food or drink to an impounded animal',
    }
    for key, value in charges_to_rename.items():
        if key in charges:
            charges = charges.replace(key, value)

    split_charges_by_and = charges.split(' and ')
    split_charges = []
    for split_charge in split_charges_by_and:
        split_charge = split_charge.strip()
        if split_charge.startswith('and '):
            split_charge = split_charge[4:]
        if len(split_charge) == 0:
            continue
        else:
            split_charges.append(split_charge)

    return split_charges


def process_charge(charge_description):
    degrees = [
        "First", "Second", "Third", "Fourth",
        "Fifth", "Sixth", "Seventh", "Eighth",
        "Ninth"
    ]

    charge_degree = None
    for degree in degrees:
        if degree.lower() + '-degree' in charge_description.lower():
            charge_degree = degree
            # Normalize the charge description by removing the degree part
            charge_description = charge_description.replace(f'{degree}-degree ', '', 1)
            charge_description = charge_description.replace(f'{degree.lower()}-degree ', '', 1)
            break

    charge_description = charge_description.strip()
    if charge_degree:
        charge_degree = charge_degree.strip()

    return charge_description, charge_degree


def main():
    incidents = DBsession.query(Incident).all()
    for incident in tqdm(incidents):
        # print(incident)
        if ',' in incident.accused_name:
            print('Accused name contains more than one name. Incident will be split.')
            list_of_uncategorized_charges = split_incident(incident, DBsession)
            for charges in list_of_uncategorized_charges:
                uncategorized_charges = charges['charge']
                accused_name = charges['accused_name']
                print('uncategorized_charges: ', uncategorized_charges)
                categorized_charges = categorize_charges(
                    incident_id=incident.id,
                    charges=uncategorized_charges,
                    accused_name=accused_name
                )
                pprint(categorized_charges)
                add_charges_to_charges_table(incident, categorized_charges)
        else:
            continue
            uncategorized_charges = incident.charges
            accused_name = incident.accused_name
            categorized_charges = categorize_charges(
                incident_id=incident.id,
                charges=uncategorized_charges,
                accused_name=accused_name
            )
            add_charges_to_charges_table(incident, categorized_charges)


def add_charges_to_charges_table(incident, categorized_charges):
    print('categorized_charges: ', categorized_charges)
    for charge_type, charges in categorized_charges.items():
        if len(charges) == 0:
            continue
        print('charges: ', charges)
        for charge in charges:
            accused_name = charge['accused_name']
            # remove any commas from dollar amounts
            charge['cleaned_charge_description'] = re.sub(r'\$(\d+),(\d+)', r'$\1\2', charge['cleaned_charge_description'])
            separated_charges_by_comma = charge['cleaned_charge_description'].split(',')
            for c in separated_charges_by_comma:
                charges_split_by_and = split_charges_by_and(c, charge_type)
                for split_charge in charges_split_by_and:
                    split_charge = split_charge.strip()
                    if len(split_charge) == 0:
                        continue
                    if split_charge.startswith('and '):
                        split_charge = split_charge[4:]

                    if ';' in split_charge:
                        split_charge = [i for i in split_charge.split(';') if len(i.strip()) > 0]
                        for s in split_charge:
                            print('225 ', s)
                            add_or_get_charge(
                                session=DBsession,
                                charge_str=s,
                                charge_type=charge_type,
                                accused_name=accused_name,
                                incident_id=incident.id,
                            )
                    else:
                        add_or_get_charge(
                            session=DBsession,
                            charge_str=split_charge,
                            charge_type=charge_type,
                            accused_name=accused_name,
                            incident_id=incident.id,
                        )

    return


def add_or_get_charge(session, charge_str, charge_type, accused_name, incident_id):
    name_used = re.search('(\w+) was charged with', charge_str, re.IGNORECASE)
    try:
        name_used = name_used.group(1)
    except AttributeError:
        name_used = None
    if name_used:
        # if the name used in the charge description is different from the accused name,
        # don't add the charge to the charges table
        if name_used.lower() != accused_name.split()[-1].lower():
            print('Name used in charge description is different from accused name. Charge will not be added to charges table.')
            return
    charge_description, charge_degree = process_charge(charge_str)
    print('------')
    print('incident id: ', incident_id)
    print('charge_description: ', charge_description)
    print('charge_type: ', charge_type)
    print('charge_degree: ', charge_degree)
    print('accused_name: ', accused_name)
    charge = session.query(Charges).filter(
        Charges.charge_description == charge_str,
        Charges.charge_class == charge_type,
        Charges.degree == charge_degree,
        Charges.charged_name == accused_name,
        incident_id == incident_id
    ).first()
    if charge:
        return charge.id
    else:
        charge = Charges(
            charged_name=accused_name,
            charge_description=charge_str,
            charge_class=charge_type,
            degree=charge_degree,
            incident_id=incident_id,
        )
        session.add(charge)
        session.commit()
        return charge.id


if __name__ == '__main__':
    main()
