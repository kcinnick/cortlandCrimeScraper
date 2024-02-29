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
    # Mapping dictionaries
    print('charge_description: ', charge_description)
    degree_number_mapping = {
        'first degree': 1, 'first-degree': 1, 'second degree': 2, 'second-degree': 2,
        'third degree': 3, 'third-degree': 3, 'fourth degree': 4, 'fourth-degree': 4,
        'fifth degree': 5, 'fifth-degree': 5, 'sixth degree': 6, 'sixth-degree': 6,
        'seventh degree': 7, 'seventh-degree': 7, 'eighth degree': 8, 'eighth-degree': 8,
        'ninth degree': 9, 'ninth-degree': 9, 'tenth degree': 10, 'tenth-degree': 10,
    }
    counts_number_mapping = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    }

    # Combined pattern to capture both counts (if present) and degree in one search
    pattern = r'(?i)(?:(\w+) counts? of )?((first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)[ -]degree)'

    match = re.search(pattern, charge_description)

    if match:
        count_str, degree_str = match.groups(default="one")[:2]  # Default count to "one" if not matched
        # Extracting and converting count and degree
        cleaned_count = counts_number_mapping.get(count_str.lower(), 1)  # Default to 1 if not found
        cleaned_degree = degree_number_mapping.get(degree_str.lower(), None)

        # Remove matched patterns from the description
        cleaned_description = re.sub(pattern, '', charge_description, count=1).strip()
    else:
        cleaned_description = charge_description
        cleaned_count = 1
        cleaned_degree = None

    return cleaned_description, cleaned_count, cleaned_degree


def add_charges_to_charges_table(incident, categorized_charges):
    print('categorized_charges: ', categorized_charges)
    for charge_type, charges in categorized_charges.items():
        if len(charges) == 0:
            continue
        print('charges: ', charges)
        for charge in charges:
            accused_name = charge['accused_name']
            # remove any commas from dollar amounts
            charge['cleaned_charge_description'] = re.sub(r'\$(\d+),(\d+)', r'$\1\2',
                                                          charge['cleaned_charge_description'])
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
    name_used = re.search('(\w+) (?:was|were) charged with ', charge_str, re.IGNORECASE)
    try:
        name_used = name_used.group(1)
    except AttributeError:
        name_used = None
    if name_used:
        # if the name used in the charge description is different from the accused name,
        # don't add the charge to the charges table
        if name_used.lower() != accused_name.split()[-1].lower():
            print(
                'Name used in charge description is different from accused name. Charge will not be added to charges table.')
            return
    charge_str_without_name = re.sub(r'(\w+) (?:was|were) charged with ', '', charge_str, re.IGNORECASE)
    charge_description, counts, charge_degree = process_charge(charge_str_without_name)
    charge = session.query(Charges).filter(
        Charges.charge_description == charge_str,
        Charges.crime == charge_description,
        Charges.charge_class == charge_type,
        Charges.degree == charge_degree,
        Charges.charged_name == accused_name,
        Charges.counts == counts,
        incident_id == incident_id
    ).first()
    if charge:
        return charge.id
    else:
        charge = Charges(
            charged_name=accused_name,
            charge_description=charge_str,
            crime=charge_description,
            charge_class=charge_type,
            degree=charge_degree,
            counts=counts,
            incident_id=incident_id,
        )
        session.add(charge)
        session.commit()
        return charge.id


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
                categorized_charges = categorize_charges(
                    incident_id=incident.id,
                    charges=uncategorized_charges,
                    accused_name=accused_name
                )
                add_charges_to_charges_table(incident, categorized_charges)
        else:
            uncategorized_charges = incident.charges
            accused_name = incident.accused_name
            categorized_charges = categorize_charges(
                incident_id=incident.id,
                charges=uncategorized_charges,
                accused_name=accused_name
            )
            add_charges_to_charges_table(incident, categorized_charges)


if __name__ == '__main__':
    main()
