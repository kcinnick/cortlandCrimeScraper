import re

from database import get_database_session, Charges, Incident

DBsession, engine = get_database_session(environment='dev')
columns = [
    Incident.id,
    Incident.incident_reported_date,
    Incident.accused_name,
    Incident.accused_age,
    Incident.accused_location,
    Incident.charges,
    Incident.details,
    Incident.legal_actions,
    Incident.incident_date,
    Incident.incident_location,
]

all_incidents = DBsession.query(*columns).all()


def categorize_charges(incident):
    # Regular expression to match charge descriptions
    # The regex captures all text up to your target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|midemeanor|misdemean-or|traffic infractions?|traffic violations|violations|violation)"
    text = incident.charges
    # Find all matches
    matches = re.findall(regex, text, re.IGNORECASE | re.DOTALL)

    categorized_charges = {
        'felonies': [],
        'misdemeanors': [],
        'violations': [],
        'traffic_infraction': [],
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
            categorized_charges['felonies'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident.id
            })
        elif 'felonies' in charge_type.lower():
            categorized_charges['felonies'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'felony',
                'incident_id': incident.id
            })
        elif 'misdemeanor' in charge_type.lower():
            categorized_charges['misdemeanors'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'misdemeanor',
                'incident_id': incident.id
            })
        elif 'violation' in charge_type.lower():
            categorized_charges['misdemeanors'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'violation',
                'incident_id': incident.id
            })
        elif 'traffic infraction' in charge_type.lower():
            categorized_charges['traffic_infraction'].append({
                'original_charge_description': original_charge_description,
                'cleaned_charge_description': cleaned_charge_description,
                'charge_type': 'traffic_infraction',
                'incident_id': incident.id
            })
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

    return separated_charges


def split_charges_by_and(charges, charge_type):
    split_charges_by_and = charges.split(' and ')
    split_charges = []
    for split_charge in split_charges_by_and:
        split_charge = split_charge.strip()
        if split_charge.startswith('and '):
            split_charge = split_charge[4:]
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
    for incident in all_combined_incidents:
        print(incident)
        if ',' in incident.accused_name:
            print('Accused name contains more than one name. Incident should be scraped manually. Skipping.')
            continue
        categorized_charges = categorize_charges(incident)
        # pprint(categorized_charges)
        # add charges to charges table
        add_charges_to_charges_table(incident, categorized_charges)


def add_charges_to_charges_table(incident, categorized_charges):
    print(categorized_charges)
    for charge_type, charges in categorized_charges.items():
        if len(charges) == 0:
            continue
        for charge in charges:
            separated_charges_by_comma = charge['cleaned_charge_description'].split(',')
            for c in separated_charges_by_comma:
                charges_split_by_and = split_charges_by_and(c, charge_type)
                for split_charge in charges_split_by_and:
                    split_charge = split_charge.strip()
                    if split_charge.startswith('and '):
                        split_charge = split_charge[4:]

                    if ';' in split_charge:
                        split_charge = split_charge.split(';')
                        for s in split_charge:
                            print('179 ', s)
                            continue
                            print('------')
                            print('incident id: ', incident.id)
                            add_or_get_charge(
                                session=DBsession,
                                charge_str=s,
                                charge_type=charge_type,
                                incident_id=incident.id,
                            )
                    else:
                        print('190 ', split_charge)
                        add_or_get_charge(
                            session=DBsession,
                            charge_str=split_charge,
                            charge_type=charge_type,
                            incident_id=incident.id,
                        )

    return


def add_or_get_charge(session, charge_str, charge_type, incident_id):
    charge_description, charge_degree = process_charge(charge_str)
    print('------')
    print('incident id: ', incident_id)
    print('charge_description: ', charge_description)
    print('charge_degree: ', charge_degree)

    charge = session.query(Charges).filter(
        Charges.charge_description == charge_str,
        Charges.charge_class == charge_type,
        Charges.degree == charge_degree,
        incident_id == incident_id
    ).first()
    if charge:
        return charge.id
    else:
        charge = Charges(
            charge_description=charge_str,
            charge_class=charge_type,
            degree=charge_degree,
            incident_id=incident_id
        )
        session.add(charge)
        session.commit()
        return charge.id


if __name__ == '__main__':
    main()
