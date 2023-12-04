import re

from sqlalchemy import text

from database import CombinedIncidents, get_database_session, Charges

DBsession, engine = get_database_session(environment='prod')
columns = [
    CombinedIncidents.id,
    CombinedIncidents.charges,
]

all_combined_incidents = DBsession.query(*columns).all()


def categorize_charges(text):
    # Regular expression to match charge descriptions
    # The regex captures all text up to your target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|violation|traffic infraction)"

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
        if charge_description.endswith(', a'):
            charge_description = charge_description[:-3]

        if charge_description.endswith(', a '):
            charge_description = charge_description[:-4]

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
                'charge_type': 'felony'
            }
        elif 'felonies' in charge_type.lower():
            categorized_charges['felonies'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony'
            }
        elif 'misdemeanor' in charge_type.lower():
            categorized_charges['misdemeanors'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'misdemeanor'
            }
        elif 'violation' in charge_type.lower():
            categorized_charges['misdemeanors'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'violation'
            }
        elif 'traffic infraction' in charge_type.lower():
            categorized_charges['traffic_infraction'] = {
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'traffic_infraction'
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
        print(incident)
        categorized_charges = categorize_charges(incident.charges)
        # add incident ID to categorized_charges
        categorized_charges['incident_id'] = incident.id

        print(categorized_charges)


def add_or_get_charge(session, charge_str, charge_type):
    charge = session.query(Charges).filter_by(charge=charge_str).first()
    if charge is None:
        charge = Charges(charge=charge_str, charge_type=charge_type)
        session.add(charge)
        session.commit()
    return charge.id


if __name__ == '__main__':
    main()
