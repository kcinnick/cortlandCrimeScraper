import re
from pprint import pprint

from sqlalchemy import text

from database import CombinedIncidents, get_database_session, ChargeTypes

DBsession, engine = get_database_session(environment='prod')
columns = [
    CombinedIncidents.id,
    CombinedIncidents.charges,
]

all_combined_incidents = DBsession.query(*columns).all()


def categorize_charges(incident):
    # Regular expression to match charge descriptions
    # The regex captures all text up to your target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|midemeanor|misdemean-or|violation|traffic infraction)"
    text = incident.charges
    # Find all matches
    matches = re.findall(regex, text, re.IGNORECASE | re.DOTALL)

    categorized_charges = {
        'felonies': None,
        'misdemeanors': None,
        'violations': None
    }

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
            categorized_charges['felonies'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident.id
            }
        elif 'felonies' in charge_type.lower():
            categorized_charges['felonies'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident.id
            }
        elif 'misdemeanor' in charge_type.lower():
            categorized_charges['misdemeanors'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'misdemeanor',
                'incident_id': incident.id
            }
        elif 'violation' in charge_type.lower():
            categorized_charges['misdemeanors'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'violation',
                'incident_id': incident.id
            }
        elif 'traffic infraction' in charge_type.lower():
            categorized_charges['traffic_infraction'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'traffic_infraction',
                'incident_id': incident.id
            }
        else:
            raise Exception('Charge type not found: ' + charge_description)

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

    separated_charges_with_counts_removed = []
    for charge in separated_charges:
        charge = charge.split(' counts of ')[-1]
        separated_charges_with_counts_removed.append(charge)

    return separated_charges_with_counts_removed


def main():
    for incident in all_combined_incidents:
        print('------')
        categorized_charges = categorize_charges(incident)
        pprint(categorized_charges)
        # add charges to charges table
        for charge_type, charge in categorized_charges.items():
            if charge is None:
                continue
            for c in charge['cleaned_charge_description'].split(','):
                split_charges_by_and = c.split(' and ')
                for split_charge in split_charges_by_and:
                    split_charge = split_charge.strip()
                    if split_charge.startswith('and '):
                        split_charge = split_charge[4:]
                    charge_description = split_charge
                    charge_type = charge['charge_type']
                    charge_degree = None
                    if 'First-degree' in charge_description:
                        charge_degree = 'First'
                    elif 'Second-degree' in charge_description:
                        charge_degree = 'Second'
                    elif 'Third-degree' in charge_description:
                        charge_degree = 'Third'
                    elif 'Fourth-degree' in charge_description:
                        charge_degree = 'Fourth'
                    elif 'Fifth-degree' in charge_description:
                        charge_degree = 'Fifth'
                    elif 'Sixth-degree' in charge_description:
                        charge_degree = 'Sixth'
                    elif 'Seventh-degree' in charge_description:
                        charge_degree = 'Seventh'
                    elif 'Eighth-degree' in charge_description:
                        charge_degree = 'Eighth'
                    elif 'Ninth-degree' in charge_description:
                        charge_degree = 'Ninth'
                    if 'first-degree' in charge_description:
                        charge_degree = 'First'
                    elif 'second-degree' in charge_description:
                        charge_degree = 'Second'
                    elif 'third-degree' in charge_description:
                        charge_degree = 'Third'
                    elif 'fourth-degree' in charge_description:
                        charge_degree = 'Fourth'
                    elif 'fifth-degree' in charge_description:
                        charge_degree = 'Fifth'
                    elif 'sixth-degree' in charge_description:
                        charge_degree = 'Sixth'
                    elif 'seventh-degree' in charge_description:
                        charge_degree = 'Seventh'
                    elif 'eighth-degree' in charge_description:
                        charge_degree = 'Eighth'
                    elif 'ninth-degree' in charge_description:
                        charge_degree = 'Ninth'

                    if charge_degree:
                        charge_description = charge_description.replace(f'{charge_degree}-degree ', '')
                        charge_description = charge_description.replace(f'{charge_degree.lower()}-degree ', '')

                    charge_id = add_or_get_charge(
                        DBsession, charge_description, charge_type, charge_degree
                    )
                    print(charge_id)
    return


def add_or_get_charge(session, charge_str, charge_type, charge_degree):
    charge = session.query(ChargeTypes).filter(
        ChargeTypes.charge_description == charge_str,
        ChargeTypes.charge_class == charge_type,
        ChargeTypes.degree == charge_degree
    ).first()
    if charge:
        return charge.id
    else:
        charge = ChargeTypes(
            charge_description=charge_str,
            charge_class=charge_type,
            degree=charge_degree
        )
        session.add(charge)
        session.commit()
        return charge.id


if __name__ == '__main__':
    main()
