import re

from sqlalchemy import text

from database import CombinedIncidents, get_database_session

DBsession, engine = get_database_session(environment='prod')
columns = [
    CombinedIncidents.charges,
]

all_combined_incidents = DBsession.query(*columns).all()


def categorize_charges(text):
    # Regular expression to match charge descriptions
    # The regex captures all text up to your target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|violation|infraction)"

    # Find all matches
    matches = re.findall(regex, text, re.IGNORECASE | re.DOTALL)

    categorized_charges = {
        'felonies': None,
        'misdemeanors': None,
        'violations': None
    }

    for match in matches:
        charge_description, charge_type = match
        charge_description = charge_description.strip().rstrip(',')

        # Categorize based on charge type
        if 'felony' in charge_type.lower():
            categorized_charges['felonies'] = charge_description
        elif 'felonies' in charge_type.lower():
            categorized_charges['felonies'] = charge_description
        elif 'misdemeanor' in charge_type.lower():
            categorized_charges['misdemeanors'] = charge_description
        elif 'violation' in charge_type.lower():
            categorized_charges['violations'] = charge_description

    return categorized_charges


def separate_charges_from_charge_descriptions(charges):
    if not charges:
        return None
    # fix missing spaces
    charges = charges.replace('  ', ' ')
    charges = charges.replace('offirst', 'of first')
    charges = charges.replace('ofsecond', 'of second')
    charges = charges.replace('ofthird', 'of third')
    charges = charges.replace('afelony', 'a felony')
    charges = charges.replace('controlledsubstance', 'controlled substance')
    charges = charges.replace('mis-demeanors', 'misdemeanors')

    charges = charges.replace(', a', '')
    charges = charges.replace(' and ', ', ')
    charges.replace('; ', '')
    charges = charges.replace(' Those are in additions to ', '')

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
        print(incident.charges)
        charges = categorize_charges(incident.charges)
        # clean up charge descriptions
        for key, value in charges.items():
            print(key)
            charges[key] = separate_charges_from_charge_descriptions(value)
            print(charges[key])
            # add charges to database


if __name__ == '__main__':
    main()
