import re
from pprint import pprint

from tqdm import tqdm

from database import get_database_session
from models.incident import Incident
from models.charges import Charges

from police_fire.data_normalization.split_incidents_with_multiple_accused import split_incident

DBsession, engine = get_database_session(environment='prod')


def clean_end_of_charge_description(charge_description):
    # get rid of ', a' at the end of the charge description
    if charge_description.endswith(', a '):
        charge_description = charge_description[:-4]

    if charge_description.endswith(', a'):
        charge_description = charge_description[:-3]

    if charge_description.startswith('; '):
        charge_description = charge_description[2:]

    if charge_description.endswith(', '):
        charge_description = charge_description[:-2]

    # get rid of ', all' at the end of the charge description
    if charge_description.endswith(', all'):
        charge_description = charge_description[:-5]

    return charge_description


def categorize_charges(incident_id, charges, accused_name):
    # Regular expression to match charge descriptions
    # The regex captures all text up to target words
    regex = r"(.*?)(felonies|felony|misdemeanors|misdemeanor|midemeanor|misdemean-or|traffic infractions?|traffic violations|violations|a? ?violation|infractions?)"
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
        print('---')
        charge_description, charge_type = match
        original_charge_description = charge_description

        charge_description = charge_description.strip().rstrip(',')

        cleaned_charge_description = clean_end_of_charge_description(charge_description)

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
            categorized_charges['violations'].append({
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
    print('split_charges_by_and: ', charges)
    charges = rename_charge_description(charges)
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


def get_counts_from_charge_description(charge_description):
    print('get counts from charge description: ', charge_description)
    counts_number_mapping = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    }

    # pattern to capture counts
    pattern = r'(\w+)[- ]counts?'

    match = re.search(pattern, charge_description.strip().lower())

    if match:
        count_str = match.groups(default="one")[0]  # Default count to "one" if not matched
        if count_str:
            count_str = count_str.strip()
        # Extracting and converting count and degree
        if count_str.isdigit():
            cleaned_count = int(count_str)
        else:
            cleaned_count = counts_number_mapping.get(count_str.lower(), 1)  # Default to 1 if not found

        # Remove matched patterns from the description
        cleaned_description = re.sub(pattern, '', charge_description, count=1).strip()
        if cleaned_description.startswith('of '):
            cleaned_description = cleaned_description[3:]
        if cleaned_description.startswith('.'):
            cleaned_description = cleaned_description[1:]
    else:
        cleaned_description = charge_description
        cleaned_count = 1

    return cleaned_description, cleaned_count


def get_degree_from_charge_description(cleaned_description):
    degree_number_mapping = {
        'first degree': 1, 'first-degree': 1, 'second degree': 2, 'second-degree': 2,
        'third degree': 3, 'third-degree': 3, 'fourth degree': 4, 'fourth-degree': 4,
        'fifth degree': 5, 'fifth-degree': 5, 'sixth degree': 6, 'sixth-degree': 6,
        'seventh degree': 7, 'seventh-degree': 7, 'eighth degree': 8, 'eighth-degree': 8,
        'ninth degree': 9, 'ninth-degree': 9, 'tenth degree': 10, 'tenth-degree': 10,
    }
    degree_pattern = r'((first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)-?degree)'
    match = re.search(degree_pattern, cleaned_description.lower())
    if match:
        degree_str = match.groups(default="first")[0]
        if degree_str:
            degree_str = degree_str.strip()
        cleaned_degree = degree_number_mapping.get(degree_str.lower(), 1)  # Default to 1 if not found
    else:
        cleaned_degree = None

    cleaned_description = re.sub(degree_pattern, '', cleaned_description, count=1).strip()

    return cleaned_description, cleaned_degree


def process_charge(charge_description):
    cleaned_description, cleaned_counts = get_counts_from_charge_description(charge_description)
    cleaned_description, cleaned_degree = get_degree_from_charge_description(cleaned_description)

    cleaned_description = cleaned_description.strip()
    if cleaned_description.startswith('. '):
        cleaned_description = cleaned_description[2:].strip()
    if cleaned_description.startswith('of '):
        cleaned_description = cleaned_description[3:].strip()

    print('charge_description: ', charge_description)
    print('cleaned_description: ', cleaned_description)
    print('cleaned_counts: ', cleaned_counts)
    print('cleaned_degree: ', cleaned_degree)
    # pattern to capture degree

    return cleaned_description, cleaned_counts, cleaned_degree


def rename_charge_description(cleaned_charge_description):
    print('cleaned_charge_description: ', cleaned_charge_description)
    charges_to_rename = {
        # occasionally, the word 'and' is part of a charge description
        # and not a separator.  In these cases, we'll remove the word
        # and replace it with 'or'.
        'All promoting prison contraband': 'Promoting prison contraband',
        'speed not reasonable and prudent': 'speed not reasonable or prudent',
        'one count of failure to provide proper food and drink to an impounded animal': 'one count of failure to provide proper food or drink to an impounded animal',
        'no distinctive, dirty, obstructed or only one license plate': 'no distinctive/dirty/obstructed or only one license plate',
        'aggravated DWI': 'Aggravated driving while intoxicated',
        'Aggravated DWI': 'Aggravated driving while intoxicated',
        'aggravated driving while in-toxicated': 'Aggravated driving while intoxicated',
        'Aggravated driving while in-toxicated': 'Aggravated driving while intoxicated',
        'DWI': 'Driving while intoxicated',
        'wrong way on a one way': 'Driving the wrong way on a one-way street',
        'wrong way on a one way street': 'Driving the wrong way on a one-way street',
        'failure to use designate lane': 'Failure to use designated lane',
        'Criminal use of drug paraphernalia': 'Criminally using drug paraphernalia',
        'Driving with 0.08% or more blood-alcohol': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'DWI with blood alcohol content of 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'DWI with blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Leaving the scene of a property damage accident': 'Leaving the scene of a property damage accident without reporting',
        'Refusal of a breath test': 'Refusal to take a breath test',
        'Refusal to take breath screening': 'Refusal to take a breath test',
        'Refusal to take breath test': 'Refusal to take a breath test',
        'Speed in zone': 'Speeding in zone',
        'Unlicensed operator': 'Unlicensed operation',
        'False presentation': 'False impersonation',
        'Illegal discharger of a firearm': 'Illegal discharge of a firearm',
        'Failure to comply with a lawful order of a police order': 'Failure to comply with a police officer',
        'Moving from lane unsafely': 'Moving from a lane unsafely',
        'No distinctive plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No distinctive plates': 'No distinctive/dirty/obstructed or only one license plate',
        'Obstructing governmental administration': 'Obstruction of governmental administration',
        'Open container in a motor vehicle': 'Open container of an alcoholic beverage in a motor vehicle',
        'Operating a motor vehicle above 0.08 percent blood alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operation of a motor vehicle with a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Unapproved stickers': 'Unauthorized stickers',
        'Unauthorized sticker': 'Unauthorized stickers',
        'Uninspected vehicle': 'Uninspected motor vehicle',
        'Unlawful manufacture methamphetamine': 'Unlawful manufacturing of methamphetamine',
        'Unlawful manufacture of methamphetamine': 'Unlawful manufacturing of methamphetamine',
        'Unsafe tire': 'Unsafe tires',
        'Wrong way on a one way': 'Driving the wrong way on a one-way street',
        'A parole': 'Parole violation',
        'A traffi': 'Traffic violation',
        'Obstruction governmental administration': 'Obstruction of governmental administration',
        'Several': 'Traffic violations',
        'Speed in excess of 55 mph': 'Speeding in excess of 55 mph',
        'Driving with 0.08% blood alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with 0.08% or more blood-alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'DWI with a blood-alcohol content of 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Failure to signal turn': 'Failure to signal a turn',
        'No license': 'No drivers license',
        'Refusal of breath test': 'Refusal to take a breath test',
        'Refusal to submit to a breath test': 'Refusal to take a breath test',
        'Refusing a breath test': 'Refusal to take a breath test',
        'Unlicensed operation of a motor vehicle': 'Unlicensed operation',
        'Using other license': 'Using the license of another',
        'Refusing a breath screening': 'Refusal to take a breath test',
        'Speed imprudent': 'Speed not reasonable or prudent',
        'Speed not reasonable or imprudent': 'Speed not reasonable or prudent',
        'Ag-gravated unlicensed operationof a motor vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggra-vated unlicensed operation of a motor vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated criminal contemp': 'Aggravated criminal contempt',
        'Aggravated diving while intoxicated with a child in car': 'Aggravated driving while intoxicated with a child in the car',
        'Aggravated unlicensed opera-tion': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated unlicensed operation': 'Aggravated unlicensed operation of a motor vehicle',
        'Using the drivers license of another': 'Using the license of another',
        'Use of license of another person': 'Using the license of another',
        'Welfarefraud': 'Welfare fraud',
        'Unregistered': 'Operating an unregistered motor vehicle',
        'Criminal trespassing': 'Criminal trespass',
        'Trespassing': 'Trespass',
        'Aggravated unlicensed operator': 'Aggravated unlicensed operation of a motor vehicle',
        'No license place': 'No license plate',
        'No head lamps': 'Inadequate headlights',
        'No front plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No distinct license plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No distinct plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No rear license plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No/distinct plate': 'No distinctive/dirty/obstructed or only one license plate',
        'Obstructed plates': 'No distinctive/dirty/obstructed or only one license plate',
        'Offering a false instrumentfor filing': 'Offering a false instrument for filing',
        'Offering a false instrument': 'Offering a false instrument for filing',
        'Offering a false instrument of filing': 'Offering a false instrument for filing',
        'Operating whiel registration suspended or revoked': 'Operating while registration suspended or revoked',
        'Operating while _ registration is suspended or revoked': 'Operating while registration suspended or revoked',
        'Operating while a registration was suspended or revoked': 'Operating while registration suspended or revoked',
        'Operating while registration suspended': 'Operating while registration suspended or revoked',
        'Unsafe turning': 'Unsafe turn',
        'Using another drivers license': 'Using the license of another',
        'Visible distortion': 'Visibility distorted or broken glass',
        'Aggravated driving while intoxicated with a child in the car': 'Aggravated driving while intoxicated with a child in the vehicle',
        'Aggravated driving while intoxicated with a reportable blood-alcohol content of 0.18%': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a reported blood-alcohol content of 0.21 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.21% or greater',
        'Aggravated driving while intoxicated with blood alcohol content 0.18% or greater': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving with a blood-alcohol content of 0.18 percent or more': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving with a blood-alcohol content of 0.18% or more': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving with a blood alcohol content of 0.18 percent of 1 percent or more of alcohol': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated drivingwhile intoxicated with a blood-alcohol content of 0.18 percentor more': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI operating with a blood-alcohol level of 0.18% or greater': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with 0.08 percent blood-alcohol content': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Aggravated DWI with 0.18% blood-alcohol level or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with a blood-alchohol content of 0.18%': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with a blood-alcohol content greater than 0.18%': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with a blood-alcohol content0.18 percent or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with a blood alcohol content of 0.18% or greater': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with blood-alcohol content 0.18 percent or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated a blood-alcohol content greater than 0.18 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content 0.18 percent or more alcohol': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content of 0.18 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content of 0.19 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content result of 0.19 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol level of 0.18% or greater': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated un-licensed operation of a motor vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated unlicensed operation of a vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated unlicensed operation of a motor vehicles': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated unlicensed operation of motor vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Aggravated unlicensed operation ofa motor vehicle': 'Aggravated unlicensed operation of a motor vehicle',
        'Circumvent interlock device': 'Circumventing an interlock device',
        'Consuming alcohol in a motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Criminal obstruction of breathing': 'Criminal obstruction of breathing or blood circulation',
        'Criminal possession of a hypodermic needle': 'Criminal possession of a hypodermic instrument',
        'Criminal possession of controlled substance': 'Criminal possession of a controlled substance',
        'Criminal possession of marijuna': 'Criminal possession of marijuana',
        'Criminal possession of precursors of meth': 'Criminal possession of precursors for making methamphetamine',
        'Criminally possessing a hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'Crossing hazard marking': 'Driving across hazard markings',
        'Driving across hazard marking': 'Driving across hazard markings',
        'Driving over hazard markings': 'Driving across hazard markings',
        'Driving while ability impaired by a drug': 'Driving while ability impaired by drugs or alcohol',
        'Driving while impaired by drugs': 'Driving while ability impaired by drugs or alcohol',
        'Driving while intoxicated with a blood-alcohol content of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood-alcohol content of more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with 0.08% or more blood alcohol': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with 0.08% or more blood alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol level of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08 percent or more': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol contest of 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol level greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol level of 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood alcohol level greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with blood-alcohol content more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'DWI with blood-alcohol content of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Fail to keep right': 'Failure to keep right',
        'Fail to obey a traffic control device': 'Failure to obey a traffic control device',
        'Fail to stop for a stop sign': 'Failure to stop at a stop sign',
        'Failure to comply with police': 'Failure to comply with a police officer',
        'Failure to comply with the lawful order of a police officer': 'Failure to comply with a police officer',
        'Failure to dim lights': 'Failure to dim headlights',
        'Failure to dim headlamps': 'Failure to dim headlights',
        'Following to closely': 'Following too closely',
        'Forged inspection sticker': 'Displaying a forged inspection certificate',
        'unapproved stickers': 'unauthorized stickers',
        'Unlawful fleeing police': 'Unlawful fleeing of a police officer',
        'Unlawful fleeing from a police officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Unlawfully fleeing a police officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Unlawful fleeing a police officer': 'Unlawful fleeing of a police officer',
        'Refusal to take a pre-screen breath test': 'Refusal to take a breath test',
        'Refusal to take breath screening test': 'Refusal to take a breath test',
        'Refuse to submit to a breath test': 'Refusal to take a breath test',
        'Refusing to submit to a breath test': 'Refusal to take a breath test',
        'Refusing to take a breath screening test': 'Refusal to take a breath test',
        'Refusing to take a breath test': 'Refusal to take a breath test',
        'Refusal to take a breath screen test': 'Refusal to take a breath test',
        'Refusal to submit to breath test': 'Refusal to take a breath test',
        'Refusal to submit to breath screening test': 'Refusal to take a breath test',
        'Refusal to submit to a breathalyzer test': 'Refusal to take a breath test',
        'Refusal to submit to a breath-screening test': 'Refusal to take a breath test',
        'Refusal to submit a breath test': 'Refusal to take a breath test',
        'Refusal of breath screening test': 'Refusal to take a breath test',
        'Refusal of breath screening': 'Refusal to take a breath test',
        'Refusal of a portable breath test': 'Refusal to take a breath test',
        'Refusal of a breath screening test': 'Refusal to take a breath test',
        'Refusal of a breath screening device': 'Refusal to take a breath test',
        'Rachel resisting arrest': 'Resisting arrest',
        'Promoting a sexual performance by a child less than 17': 'Promoting a sexual performance by a child',
        'Prohibited use of weapons': 'Prohibited use of a weapon',
        'Predatory sex assault against a child': 'Predatory sexual assault against a child',
        'Predatory sexual assault of a child': 'Predatory sexual assault against a child',
        'Possession of tools': 'Possession of burglars tools',
        'Possession of burglar\'s tools': 'Possession of burglars tools',
        'Possession of burglar tools': 'Possession of burglars tools',
        'Possession of burglary tools': 'Possession of burglars tools',
        'Possession of an obscene sexual performance by a child': 'Possession of a sexual performance by a child',
        'Possession of a instrument': 'Possession of a hypodermic instrument',
        'Possession of a hypodermic needle': 'Possession of a hypodermic instrument',
        'Possession of a controlled substance in a non-original container': 'Possession of a controlled substance not in an original container',
        'Possessing a sexual performance by a child less than 16': 'Possession of a sexual performance by a child',
        'Petit larceny.': 'Petit larceny',
        'Operating with a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'operating an unregistered vehicle': 'Operating an unregistered motor vehicle',
        'Operating a vehicle without an interlock device': 'Operating a vehicle without an ignition interlock device',
        'Operating a motor vehicle without a valid inspection': 'Operating a motor vehicle without a valid inspection certificate',
        'Operating a motor vehicle with more than 0.08 percent blood-alcohol': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle while ability impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Operating a motor vehicle impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Open container of alcohol in a motor vehicle': 'Open container of an alcoholic beverage in a motor vehicle',
        'Of criminal possession of stolen property': 'Criminal possession of stolen property',
        'Of criminally using drug paraphernalia': 'Criminally using drug paraphernalia',
        'Of endangering the welfare of a child': 'Endangering the welfare of a child',
        'Open alcohol container in a vehicle': 'Open container of an alcoholic beverage in a motor vehicle',
        'Open container of an alcoholic beverage in a motor vehicle': 'Open container of an alcoholic beverage in a motor vehicle',
        'Operating a motor vehicle without insurance': 'Operating a motor vehicle without valid insurance',
        'Operating in': 'operating in violation of restrictions',
        'Moved from lane unsafely': 'Moving from a lane unsafely',
        'Martinez: criminal possession of stolen property': 'Criminal possession of stolen property',
        'Lanzo: criminal possession of stolen property': 'Criminal possession of stolen property',
        'Intimidating a witness': 'Intimidating a victim or witness',
        'Insufficient tail lamp': 'No/insufficient tail lamps',
        'Inoperable plate lamp': 'Inoperable plate lamps',
        'Inadequate light': 'Driving with no or inadequate lights',
        'Inadequate lights': 'Driving with no or inadequate lights',
        'Inadequate tail lights': 'No/insufficient tail lamps',
        'Inadequate headlamps': 'Inadequate headlights',
        'Inadequate exhaust system': 'Inadequate exhaust',
        'Inadequate headlamp': 'Inadequate headlights',
        'Improper use of four-way flasher': 'Improper use of four-way flashers',
        'Improper use of flashers': 'Improper use of four-way flashers',
        'Improper signaling': 'No or improper signal',
        'Improper right-hand turn': 'Improper right turn',
        'Improper or no turning signal': 'Improper or no turn signal use',
        'False reporting an incident': 'Falsely reporting an incident',
        'Falsely reporting of an incident': 'Falsely reporting an incident',
        'Falsifying of business records': 'Falsifying business records',
        'Filing a false instrument for filing': 'Filing a false instrument',
        'Fleeing a police officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Fleeing an officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Fugitive of justice': 'Fugitive from justice',
        'Grand larceny.': 'Grand larceny',
        'Growing the plant known as cannabis by an unlicensed person': 'Growing cannabis by an unlicensed person',
        'Improper license plate': 'Switched/improper license plates',
        'Improper or no signal': 'Improper or no turn signal use',
        'Endangering the welfare of a disabled person': 'Endangering the welfare of an incompetent or physically disabled person',
        'Endangering welfare of a child': 'Endangering the welfare of child',
        'Failure to maintain lane': 'Failure to use designated lane',
        'Failure to notify change of address': 'Failure to notify DMV of address change',
        'Failure to notify Department of Motor Vehicles of an address change': 'Failure to notify DMV of address change',
        'Failure to notify DMV of an address change': 'Failure to notify DMV of address change',
        'Failure to notify the Department of Motor Vehicles of an address change': 'Failure to notify DMV of address change',
        'Failure to notify the state Department of Motor Vehicles of a change of address': 'Failure to notify DMV of address change',
        'Failure to notify the state of change of address': 'Failure to notify DMV of address change',
        'Failure to obey a traffic device': 'Failure to obey a traffic control device',
        'Failure to obey traffic device': 'Failure to obey a traffic control device',
        'Failure to provide proper food': 'Failure to provide proper food or drink to an impounded animal',
        'Failure to properly register as a sex offender': 'Failure to register as a sex offender',
        'Failure to signal for a turn': 'Failure to signal a turn',
        'Failure to stop at stop sign': 'Failure to stop at a stop sign',
        'Failure to stop for a stop sign': 'Failure to stop at a stop sign',
        'Failure to use a designated lane': 'Failure to use designated lane',
        'Failure to use signal for a turn': 'Failure to signal a turn',
        'Failure to use turn signal': 'Failure to signal a turn',
        'Failure to yield to right of way on approach of an emergency vehicle': 'Failure to yield right of way to an emergency vehicle',
        'False personation': 'False impersonation',
        'Bowers: obstruction of governmental administration': 'Obstruction of governmental administration',
        'Briana reckless driving': 'Reckless driving',
        'Bur-glary': 'Burglary',
        'Carter: unlawfully dealing with a child': 'Unlawfully dealing with a child',
        'Conspiracies': 'Conspiracy',
        'Conspiring to distribute': 'Conspiracy to distribute',
        'Criminal possession controlled substance': 'Criminal possession of a controlled substance',
        'Criminal possessing a hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'Criminal possession of a controlledsubstance': 'Criminal possession of a controlled substance',
        'Criminal possession of precursors for methamphetamine': 'Criminal possession of precursors for making methamphetamine',
        'Criminal sex act': 'Criminal sexual act',
        'Crossing road hazard marking': 'Driving across hazard markings',
        'Crossing hazard markings': 'Driving across hazard markings',
        'Crossing roadway markings': 'Driving across hazard markings',
        'Driving while impaired by drugs or alcohol': 'Driving while ability impaired by drugs or alcohol',
        'Driving while in-toxicated': 'Driving while intoxicated',
        'Driving with a blood-alcohol content above 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content grater than 0.18%': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood-alcohol content greater an 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Parked on highway': 'Stopped/parked on highway',
        'Parking on a highway': 'Stopped/parked on highway',
        'Possession of alcohol under 21': 'Unlawful possession of alcohol by a person under 21',
        'Unlawful possession of alcohol by someone under 21': 'Unlawful possession of alcohol by a person under 21',
        'Unlawful possession of alcohol under 21': 'Unlawful possession of alcohol by a person under 21',
        'Unlawful possession of alcohol under the age of 21': 'Unlawful possession of alcohol by a person under 21',
        'Unlawful possession of certain ammunition feeding device': 'Unlawful possession of large capacity ammunition feeding device',
        'Unlawful possession of an ammunition feed device': 'Unlawful possession of large capacity ammunition feeding device',
        'Operating with a blood-alcohol content greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating with a blood-alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a vehicle with blood-alcohol content greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a vehicle with a blood-alcohol content of 0.18% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Operating a vehicle with a blood-alcohol content greater than 0.08%' : 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a vehicle with a blood-alcohol content great than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with more than 0.08 percent blood-alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol level of 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol level of 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol content of 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol content level greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol content greater that 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol content of 0.21 percent': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.21 percent or more',
        'Driving with 0.18% or more blood-alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood-alcohol content of 0.18% or more': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood alcohol content of 0.08% or more': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08% or more': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with 0.08 percent or more blood-alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Controlled substance no in original container': 'Possession of a controlled substance not in the original container',
        'Controlled substance not in original container': 'Possession of a controlled substance not in the original container',
        'Possession of a controlled substance not in an original container': 'Possession of a controlled substance not in the original container',
        'Possession of a controlled substance not in original container': 'Possession of a controlled substance not in the original container',
        'Controlled substance outside its container': 'Possession of a controlled substance not in the original container',
        'Promoting a sexual performance of a child': 'Promoting a sexual performance by a child',
        'E criminal possession of a controlled substance': 'Criminal possession of a controlled substance',
        'Criminal possessions of a controlled substance': 'Criminal possession of a controlled substance',
        'Criminal possession of a controlled substances': 'Criminal possession of a controlled substance',
        'Driving while registration is suspended': 'Operating while registration suspended or revoked',
        'Driving with suspended registration': 'Operating while registration suspended or revoked',
        'Criminally using drug paraphernalia.': 'Criminally using drug paraphernalia',
        'Aggravated driving while intoxicated with a blood alcohol content of 0.18% or more': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood-alcohol content of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content about 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with 0.08% blood-alcohol content': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Leaving the scene of a personal injury accident': 'Leaving the scene of a personal injury auto accident',
        'Leaving the scene of an injury accident': 'Leaving the scene of a personal injury auto accident',
        'Leaving the scene of a personal injury motor vehicle accident': 'Leaving the scene of a personal injury auto accident',
        'Possession of a forged instrument': 'Criminal possession of a forged instrument',
        'Possession of a controlled substance outside original container': 'Possession of a controlled substance not in the original container',
        'Possession of a controlled substance not in its proper container': 'Possession of a controlled substance not in the original container',
        'Possessing a controlled substance outside its original container': 'Possession of a controlled substance not in the original container',
        'Driving with a blood-alcohol content of 0.18 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving while intoxicated with a blood-alcohol content of 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.18% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood-alcohol content of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of .018% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving with a blood alcohol content of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08 or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operation of vehicle without interlock device': 'Operating a vehicle without an ignition interlock device',
        'Operation of a motor vehicle without interlock device': 'Operating a vehicle without an ignition interlock device',
        'Operating without insurance': 'Operating a motor vehicle without valid insurance',
        'Operation without insurance': 'Operating a motor vehicle without valid insurance',
        'Operating a vehicle without insurance': 'Operating a motor vehicle without valid insurance',
        'Drinking in motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Drinking in a motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Drinking alcohol in a motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Drinking alcohol in motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Failed to use designated lane': 'Failure to use designated lane',
        'Failure to use the designated lane': 'Failure to use designated lane',
        'Failed to use designated lanes': 'Failure to use designated lane',
        'Failing to use designated lane': 'Failure to use designated lane',
        'F criminal sale of a controlled substance': 'Criminal sale of a controlled substance',
        'Unlawful fleeing an officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Unlawful fleeing a police officer in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'No seatbelt': 'No seat belt',
        'Driving while intoxicated with blood-alcohol content of 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood-alcohol content 0.08 percent or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with blood-alcohol content of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood-alcohol content of 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Manufacturing methamphetamine': 'Unlawful manufacturing of methamphetamine',
        'Unlawful manufacture methamphetamines': 'Unlawful manufacturing of methamphetamine',
        'Criminal possession of a controlled sbustance': 'Criminal possession of a controlled substance',
        'Criminal possession of a controlled substance.': 'Criminal possession of a controlled substance',
        'Criminal possession of a controlled substance and': 'Criminal possession of a controlled substance',
        'Possession of a synthetic drug': 'Possession of synthetic drugs',
        'No/improper signal': 'No or improper signal',
        'No or improper turn signal': 'Improper or no turn signal use',
        'Endangering the welfare of an incompetent or disabled person': 'Endangering the welfare of an incompetent or physically disabled person',
        'Tinted windows': 'Excessive window tint',
        'Drinking alcohol in a motor vehicle while on the highway': 'Drinking alcohol in a motor vehicle on a highway',
        'Speed not reasonable': 'Speed not reasonable for conditions',
        'Operations of a motor vehicle while impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Operation of a motor vehicle while impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Operating a motor vehicle while impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Operation of a motor vehicle impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Aggravated driving while intoxicated with a 0.18% blood alcohol content': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'No headlights': 'Operating a motor vehicle with no headlights',
        'Operating a vehicle without headlights': 'Operating a motor vehicle with no headlights',
        'Driving what ability impaired by drugs': 'Driving while ability impaired by drugs or alcohol',
        'Driving with ability impaired by drugs': 'Driving while ability impaired by drugs or alcohol',
        'Driving a motor vehicle while ability impaired by drugs': 'Driving while ability impaired by drugs or alcohol',
        'Unlawful possession of personal ID': 'Unlawful possession of personal identification',
        'Failure to obey an officer': 'Failure to comply with a police officer',
        'Attempted disseminating indecent material to minors': 'Attempted dissemination of indecent material to minors',
        'Grand larcency': 'Grand larceny',
        'Grand arceny': 'Grand larceny',
        'Consumption of alcoholic beverage in a motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Consumption/possession of alcohol in motor vehicle': 'Consumption of alcohol in a motor vehicle',
        'Uninsured motor vehicle': 'Operating a motor vehicle without valid insurance',
        'Operating an uninsured motor vehicle': 'Operating a motor vehicle without valid insurance',
        'Each of welfare fraud': 'Welfare fraud',
        'Inadequate or loud muffler': 'Inadequate muffler',
        'Inadequate or no muffler': 'Inadequate muffler',
        'No or inadequate muffler': 'Inadequate muffler',
        'Driving to left of pavement markings': 'Driving to the left of pavement markings',
        'Driving left of pavement markings': 'Driving to the left of pavement markings',
        'Driving to the left of pavement marking': 'Driving to the left of pavement markings',
        'Inadequate plate lamp': 'Inadequate plate lamps',
        'Fail to notify change of address': 'Failure to notify DMV of address change',
        'Failure to notify DMV of change of address': 'Failure to notify DMV of address change',
        'Refusal to submit to a chemical test': 'Refusal to submit to a chemical screening test',
        'Unlawful fleeing police in a motor vehicle': 'Unlawful fleeing of a police officer in a motor vehicle',
        'Each of criminal possession of a weapon': 'Criminal possession of a weapon',
        'Unreasonable speed': 'Speed not reasonable or prudent',
        'Failure to yield to an emergency vehicle': 'Failure to yield right of way to an emergency vehicle',
        'Criminal possession of a stolen property': 'Criminal possession of stolen property',
        'Possession of stolen property': 'Criminal possession of stolen property',
        'Operating a vehicle while registration suspended': 'Operating while registration suspended or revoked',
        'Operating a motor vehicle while registration is suspended': 'Operating while registration suspended or revoked',
        'Operating a vehicle with a suspended registration': 'Operating while registration suspended or revoked',
        'Operating a motor vehicle with a suspended registration': 'Operating while registration suspended or revoked',
        'Restrictions': 'operating in violation of restrictions',
        'No plate lamp': 'Inadequate plate lamps',
        'No plate lamps': 'Inadequate plate lamps',
        'Criminal possession of a hypodermicinstrument': 'Criminal possession of a hypodermic instrument',
        'Unlawful possession of a hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'DWI with a blood-alcohol content of 0.18 or higher': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'DWI with a blood alcohol content 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Aggravated DWI with blood-alcohol content of 0.18 percent or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated DWI with a blood-alcohol content 0.18 percent or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Failed to keep right': 'Failure to keep right',
        'Disregarding a traffic devise': 'Disregarding a traffic control device',
        'Failed to stop at a stop sign': 'Failure to stop at a stop sign',
        'Fail to stop at stop sign': 'Failure to stop at a stop sign',
        'Criminal impersonation of another': 'Criminal impersonation',
        'Stopping on a highway': 'Stopped/parked on highway',
        'Standing or parking on a highway': 'Stopped/parked on highway',
        'Stopping/standing/parking on a highway': 'Stopped/parked on highway',
        'Uncovered load': 'Operating with inadequately covered loose cargo',
        'Driving in center lane': 'Driving in the center lane',
        'Disorderly conduction': 'Disorderly conduct',
        'Possession of hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'Possession of a hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'Unlawful possession of hypodermic instrument': 'Criminal possession of a hypodermic instrument',
        'Using a phone while driving': 'Driving while using a mobile phone',
        'Driving while using a cell phone': 'Driving while using a mobile phone',
        'Endangering the welfare of child': 'Endangering the welfare of a child',
        'Each of endangering the welfare of a child': 'Endangering the welfare of a child',
        'Operating a vehicle without a valid registration': 'Operating a motor vehicle without a valid registration',
        'Driving while intoxicted': 'Driving while intoxicated',
        'Driving While Intoxicated': 'Driving while intoxicated',
        'Riving while intoxicated': 'Driving while intoxicated',
        'Driving while intoxicated a': 'Driving while intoxicated',
        'Driving without headlights': 'Operating a motor vehicle with no headlights',
        'Driving with no headlights': 'Operating a motor vehicle with no headlights',
        'Possession of an open container': 'Open container of alcohol',
        'Possession of open container': 'Open container of alcohol',
        'Unlawful dealing with a child': 'Unlawfully dealing with a child',
        'Driving while ability impaired': 'Driving while ability impaired by drugs or alcohol',
        'Driving while intoxicated with prior conviction': 'Driving while intoxicated with a prior conviction',
        'Driving while intoxicated with a previous conviction': 'Driving while intoxicated with a prior conviction',
        'Criminal obstruction of breathing or circulation': 'Criminal obstruction of breathing or blood circulation',
        'Criminal obstruction of breath': 'Criminal obstruction of breathing or blood circulation',
        'Obstruction of breathing': 'Criminal obstruction of breathing or blood circulation',
        'Driving while intoxicated with previous conviction in 10 years': 'Driving while intoxicated with a conviction in the previous 10 years',
        'Drivers view obstructed': 'Driver\'s view obstructed or obstructed windshield',
        'Drivers view distorted': 'Driver\'s view obstructed or obstructed windshield',
        'Visibility distorted or broken glass': 'Driver\'s view obstructed or obstructed windshield',
        'Failure to comply with a lawful order and': 'Failure to comply with a lawful order',
        'Moving from the lane unsafely': 'Moving from a lane unsafely',
        'Unsafe lane change': 'Moving from a lane unsafely',
        'Wrong way on a one way street': 'Driving the wrong way on a one-way street',
        'Imprudent speed': 'Speed not reasonable or prudent',
        'No headlamp': 'Inadequate headlights',
        'Failure to use a turn signal': 'Failure to signal a turn',
        'Wrong way on a one-way street': 'Driving the wrong way on a one-way street',
        'Theft of service': 'Theft of services',
        'Driving an uninspected vehicle': 'Operating an uninspected vehicle',
        'Possession of drug paraphernalia': 'Criminal possession of drug paraphernalia',
        'Backing unsafely': 'Unsafe backing',
        'Failing to keep right on a two land road': 'Failing to keep right',
        'Driving while impaired bydrugs': 'Driving while impaired by drugs',
        'Driving across hazardous markings': 'Driving across hazard markings',
        'Disregarding a traffic device': 'Disregarding a traffic control device',
        'Disobeying a traffic control device': 'Disregarding a traffic control device',
        'Unlawful fleeing from police': 'Unlawful fleeing of a police officer',
        'Unlawful fleeing from a police officer': 'Unlawful fleeing of a police officer',
        'Operating without a license': 'Operating without a valid license',
        'Driving while intoxicated with a blood-alcohol level of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol level above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with blood-alcohol above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Criminal possession of stolen property.': 'Criminal possession of stolen property',
        'Aggravated driving while intoxicated with a blood-alcohol level higher than 0.18': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Speeding': 'Speeding in zone',
        'Operating a motor vehicle without ignition interlock device': 'Operating a vehicle without an ignition interlock device',
        'Suspended registration': 'Operating while registration suspended or revoked',
        'Operating a motor vehicle with a blood-alcohol content of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol level of 0.18% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Operating a motor vehicle with a blood-alcohol content greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Obstructed plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No plate or distinct plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No distinctive license plate': 'No distinctive/dirty/obstructed or only one license plate',
        'Failure to stay in a designated lane': 'Failure to use designated lane',
        'Obstructed view': 'Driver\'s view obstructed or obstructed windshield',
        'Driving with obstructed view': 'Driver\'s view obstructed or obstructed windshield',
        'Driving with a blood alcohol contest greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol contest greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'No tail light': 'No/insufficient tail lamps',
        'Failure to comply': 'Failure to comply with a lawful order',
        'Possession of a controlled substance': 'Criminal possession of a controlled substance',
        'Insufficient tail lamps': 'No/insufficient tail lamps',
        'Driving across hazards': 'Driving across hazard markings',
        'Cross hazard markings': 'Driving across hazard markings',
        'Crossing hazardous marking': 'Driving across hazard markings',
        'Crossing road hazard markings': 'Driving across hazard markings',
        'No license plate lamp': 'No license plate lamps',
        'Operating a motor vehicle without an interlock device': 'Operating a vehicle without an ignition interlock device',
        'Improper use of signal': 'No or improper signal',
        'Aggravated driving while intoxicated with a blood-alcohol content of 0.18 or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'DWI with a previous conviction': 'Driving while intoxicated with a prior conviction',
        'DWI with a previous conviction within 10 years': 'Driving while intoxicated with a conviction in the previous 10 years',
        'DWI with a previous conviction within the last 10 years': 'Driving while intoxicated with a conviction in the previous 10 years',
        'Driving while intoxicated with a blood-alcohol level of 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Sex abuse': 'Sexual abuse',
        'Operation of motor vehicle with a blood-alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'F robbery': 'Robbery',
        'F rape': 'Rape',
        'Failure to walk facing traffic': 'Pedestrian failure to walk facing traffic',
        'No or inadequate plate lamps': 'Inadequate plate lamps',
        'No/inadequate license plate lamps': 'Inadequate plate lamps',
        'Improper left hand turn': 'Improper left turn',
        'Burglar': 'Burglary',
        'No turn signal': 'Improper or no turn signal use',
        'Obstruction of governmental administration': 'Obstruction of governmental administration',
        'Obstructing government administration': 'Obstruction of governmental administration',
        'Tammy obstruction of governmental administration': 'Obstruction of governmental administration',
        'Improper license plates': 'Switched/improper license plates',
        'No signal': 'No or improper signal',
        'No signal usage': 'No or improper signal',
        'DWI with a blood-alcohol content of more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Unauthorized use of a vehicle': 'Unauthorized use of a motor vehicle',
        "Driver’s view obstructed": "Driver's view obstructed or obstructed windshield",
        'Tampering with physical evidence': 'Tampering with evidence',
        'Switched plates': 'Switched/improper license plates',
        'Failure to obey a police officer': 'Failure to comply with a police officer',
        'Failure to yield the right of way': 'Failure to yield right of way',
        'DWI with a blood-alcohol content of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'First-offense driving while intoxicated': 'Driving while intoxicated',
        'Driving while intoxicated as a first offense': 'Driving while intoxicated',
        'License plate': 'No distinctive/dirty/obstructed or only one license plate',
        'Driving with a blood-alcohol level of 0.08% or more': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol level greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Operating a motor vehicle with a blood-alcohol level greater than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Improver signal': 'No or improper signal',
        'Appropriate shelter for dogs left outdoors': 'Failure to provide appropriate shelter for dogs left outdoors',
        'Possession of a dangerous substance or synthetic drug': 'Possession or use of a dangerous or synthetic drug',
        'Sexual Assault': 'Sexual assault',
        'Appearing in public under the influence of narcotics or a drug other than alcohol': 'Appearing in public under the influence of a drug other than alcohol',
        'Possession of marijuana': 'Unlawful possession of marijuana',
        'Drink to an impounded animal': 'Failure to provide proper food or drink to an impounded animal',
        'Distorted or broken glass': 'Visibility distorted or broken glass',
        'Drinking alcohol in public': 'Consumption of alcohol in public',
        'Driving with a blood-alcohol content of 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content level of 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving with a blood-alcohol content of 0.08% or higher': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'E burglary': 'Burglary',
        'Forged inspection certificate': 'Displaying a forged inspection certificate',
        'Drove across hazard markings': 'Driving across hazard markings',
        'Driving while intoxicated in a commercial motor vehicle': 'Driving while intoxicated in a commercial vehicle',
        'Possessing a sexual performance by a child': 'Possession of a sexual performance by a child',
        'Driving without a license': 'Operating without a valid license',
        'Driving with no license': 'Operating without a valid license',
        'Operation of a motor vehicle with a blood alcohol content above 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with previous conviction within 10 years': 'Driving while intoxicated with a conviction in the previous 10 years',
        'Improper plate': 'Switched/improper license plates',
        'Possess with intent to distribute 50 grams or more of methamphetamine': 'Possession with intent to distribute 50 grams or more of methamphetamine',
        'Operation without headlights': 'Operating a motor vehicle with no headlights',
        'Speed not prudent': 'Speed not reasonable or prudent',
        'Possession of hypodermic needle': 'Criminal possession of a hypodermic instrument',
        'Criminal possession of precursors for making methamphetamine': 'Criminal possession of methamphetamine manufacturing material',
        'Five vehicle and': 'Traffic violations',
        'Four Vehicle': 'Traffic violations',
        'Criminal contempt of an arrest warrant': 'Criminal contempt for an outstanding warrant',
        'License plate light out': 'Inadequate plate lamps',
        'Inadequate plate lights': 'Inadequate plate lamps',
        'No license plate': 'No distinctive/dirty/obstructed or only one license plate',
        'No license plate lamps': 'Inadequate plate lamps',
        'Two': 'Traffic violations',
        'Having an open container in a motor vehicle': 'Open container of an alcoholic beverage in a motor vehicle',
        'Operating out of ignition interlock restriction': 'Operating a vehicle without an ignition interlock device',
        'Operating without ignition interlock': 'Operating a vehicle without an ignition interlock device',
        'Operation of a motor vehicle without an interlock device': 'Operating a vehicle without an ignition interlock device',
        'Overload on tries': 'Overload on tires',
        'Violating of conditional license': 'Operating while violating conditional license',
        'A traffic': 'Traffic violations',
        'Traffic': 'Traffic violations',
        'Other': 'Traffic violations',
        'Several other': 'Traffic violations',
        'Unlawful fleeing': 'Unlawful fleeing of a police officer',
        'Nine': 'Traffic violations',
        'First-offense operating a motor vehicle while impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Operating a vehicle while impaired by drugs': 'Operating a motor vehicle while impaired by drugs',
        'Driving with a damaged wind-shield': "Driver's view obstructed or obstructed windshield",
        'Broken or cracked windshield': "Driver's view obstructed or obstructed windshield",
        'Windshield non-transparent': "Driver's view obstructed or obstructed windshield",
        'Passing a red signal': 'Passing a red light',
        'Going through a red light': 'Passing a red light',
        'Running a red light': 'Passing a red light',
        'Unsafe speed': 'Speed not reasonable or prudent',
        'Failing to stop at a stop sign': 'Failure to stop at a stop sign',
        'Operating without tail lamps': 'Operating without tail lights',
        'Driving while ability impaired by alcohol & drugs combined': 'Driving while ability impaired by drugs or alcohol',
        'Driving while ability impaired by drugs-special': 'Driving while ability impaired by drugs or alcohol',
        'Driving while ability impaired by drugs or alcohol': 'Driving while ability impaired by drugs or alcohol',
        'Failure to obey a traffic control device': 'Disregarding a traffic control device',
        'Driving while intoxicated by drugs': 'Driving while intoxicated by drugs or alcohol',
        'Unlawful sale/possession/use of dangerous substances': 'Unlawful sale/possession/use of dangerous substances/synthetics',
        'Driving while intoxicated with a conviction in the previous 10 years': 'Driving while intoxicated with a prior conviction',
        'A traffic violation': 'Traffic violations',
        'Traffic Law': 'Traffic violations',
        'Crossing pavement markings': 'Driving across pavement markings',
        'Numerous': 'Traffic violations',
        'Ignition interlock restrictions': 'Operating a vehicle without an ignition interlock device',
        'No tail lamp': 'No/insufficient tail lamps',
        'No tail lamps': 'No/insufficient tail lamps',
        'No tail lights': 'No/insufficient tail lamps',
        'Unlawfully fleeing a police officer': 'Unlawful fleeing of a police officer',
        'No or improper signal': 'Improper or no turn signal use',
        'Four': 'Traffic violations',
        'Driving while ability impaired by alcohol or drugs': 'Driving while ability impaired by drugs or alcohol',
        'Several traffic': 'Traffic violations',
        'Various': 'Traffic violations',
        'Several vehicle and': 'Traffic violations',
        'A traffic device': 'Disregarding a traffic control device',
        'Speed over posted 55 mph zone': 'Speeding in excess of 55 mph',
        'Speed over 55 mph': 'Speeding in excess of 55 mph',
        'Noise prohibited': 'General prohibition of noise',
        'Noise ordinance': 'General prohibition of noise',
        'Three vehicle and': 'Traffic violations',
        'Obstruction of government administration': 'Obstruction of governmental administration',
        'DWI with blood-alcohol content more than 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Five vehicle violations': 'Traffic violations',
        'Unsafe passing on the left': 'Improper passing',
        'No inspection': 'Operating without inspection',
        'No taillights': 'No/insufficient tail lamps',
        'Three': 'Traffic violations',
        'Parked on a highway': 'Stopped/parked on highway',
        'Bank Robbery': 'Bank robbery',
        'Unlawful possession of alcohol': 'Unlawful possession of alcohol by a person under 21',
        'Improper plates': 'Switched/improper license plates',
        'Assorted': 'Traffic violations',
        'Displaying a forged inspection sticker': 'Displaying a forged inspection certificate',
        'Operating a vehicle without a valid inspection certification': 'Operating a motor vehicle without a valid inspection certificate',
        'Operation of a motor vehicle without an inspection certification': 'Operating a motor vehicle without a valid inspection certificate',
        'DWI with a blood-alcohol level of 0.08 percent or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Lane-use': 'Failure to use designated lane',
        'State police also issued Dayton 58 traffic tickets for': 'Traffic violations',
        'Aggravated driving while intoxicated with a blood-alcohol content greater than 0.18%': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Aggravated driving while intoxicated with a blood-alcohol level of 0.18% or higher': 'Aggravated driving while intoxicated with a blood-alcohol content of 0.18% or greater',
        'Driving while intoxicated with a blood-alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Harrassment': 'Harassment',
        'Driving while intoxicated with a blood alcohol content greater than 0.08%': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood-alcohol content over 0.08 percent': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated with a blood alcohol level of 0.08% or greater': 'Driving while intoxicated with a blood-alcohol content of 0.08% or greater',
        'Driving while intoxicated-Leandras law': 'Driving while intoxicated',
        'Driving on the sidewalk': 'Driving a motor vehicle on or across a sidewalk',
        'Driving while ability impaired with a child 15 or under as a passenger': 'Driving while impaired by drugs with a child in the vehicle',
        'Inadequate brake lamps': 'Inadequate brake lights',
        'Driving below the minimum speed limit': 'Driving too slowly',
        'Driving while impaired': 'Driving while ability impaired by drugs or alcohol',
    }

    if cleaned_charge_description.strip() in charges_to_rename:
        return charges_to_rename[cleaned_charge_description.strip()]
    else:
        print(f'charge description not found: {cleaned_charge_description}')
        return cleaned_charge_description


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
            print('charge cleaned description: ', charge['cleaned_charge_description'])
            charge['cleaned_charge_description'] = rename_charge_description(charge['cleaned_charge_description'])
            separated_charges_by_comma = charge['cleaned_charge_description'].split(',')
            for c in separated_charges_by_comma:
                charges_split_by_and = split_charges_by_and(c, charge_type)
                for split_charge in charges_split_by_and:
                    split_charge = split_charge.strip()
                    print('split_charge: ', split_charge)
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
    print('charge_str: ', charge_str)
    name_used = re.search('(\w+) (?:was|were) charged with ', charge_str, re.IGNORECASE)
    if charge_str.startswith('All '):
        name_used = 'all'
    else:
        try:
            name_used = name_used.group(1)
        except AttributeError:
            name_used = None
    print('Name used is: ', name_used)
    if name_used:
        if name_used.lower() == 'each':
            # 'each' means that everyone mentioned was charged with the crime, so we'll add it for all.
            pass
        elif name_used.lower() == 'all':
            # 'all' means that everyone mentioned was charged with the crime, so we'll add it for all.
            pass
        elif name_used.lower() == 'both':
            # 'the' means that the person mentioned was charged with the crime, so we'll add it for that person.
            pass
        # if the name used in the charge description is different from the accused name,
        # don't add the charge to the charges table
        elif name_used.lower() != accused_name.split()[-1].lower():
            print(
                'Name used in charge description is different from accused name. '
                'Charge will not be added to charges table.')
            return
        elif name_used.lower() == accused_name.split()[-1].lower():
            # names are the same
            pass
        else:
            print(f'Name used: {name_used.lower()}, accused name: {accused_name.split()[-1].lower()}')
            raise Exception('Name used in charge description is different from accused name.')
    charge_str_without_name = re.sub(r'(\w+) (?:was|were) charged with ', '', charge_str, re.IGNORECASE)
    #charge_description, counts, charge_degree = process_charge(charge_str_without_name)
    cleaned_description, cleaned_counts, cleaned_degree = process_charge(charge_str_without_name)
    cleaned_description = cleaned_description.replace('  ', ' ')
    if ' charged with ' in cleaned_description:
        cleaned_description = ' '.join(cleaned_description.split(' charged with ')[1:])
    if 'degree' in cleaned_description:
        cleaned_description = ' '.join(cleaned_description.split('degree')[1:])
    if cleaned_description.startswith('_ '):
        cleaned_description = cleaned_description[2:]
    cleaned_description = cleaned_description.strip()

    cleaned_description = cleaned_description[0].upper() + cleaned_description[1:]
    cleaned_description = rename_charge_description(cleaned_description)
    if cleaned_description == 'N/A':
        return
    charge = session.query(Charges).filter(
        Charges.charge_description == charge_str,
        Charges.crime == cleaned_description,
        Charges.charge_class == charge_type,
        Charges.degree == cleaned_degree,
        Charges.charged_name == accused_name,
        Charges.counts == cleaned_counts,
        Charges.incident_id == incident_id
    ).first()
    if charge:
        print('Charge already found.')
        print(charge.id)
        return charge.id
    else:
        charge = Charges(
            charged_name=accused_name,
            charge_description=charge_str,
            crime=cleaned_description,
            charge_class=charge_type,
            degree=cleaned_degree,
            counts=cleaned_counts,
            incident_id=incident_id,
        )
        session.add(charge)
        session.commit()
        print('Charge added.')
        return charge.id


def main():
    # use the below for a full load:
    #incidents = DBsession.query(Incident).all()

    # use the below for a partial load:
    # get all incident_ids referenced in the charges table
    incident_ids_in_charges_table = DBsession.query(Charges.incident_id).distinct().all()
    incident_ids_in_charges_table = [i[0] for i in incident_ids_in_charges_table]
    # get all incidents that are not in the charges table
    incidents = DBsession.query(Incident).filter(~Incident.id.in_(incident_ids_in_charges_table)).all()

    # use the below for a single incident:
    #incidents = DBsession.query(Incident).filter(Incident.id == 2984)

    print(len(incidents), 'incidents to process')
    for incident in tqdm(incidents):
        print('Incident ID: ', incident.id)
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
            print('Accused name contains only one name. Incident will not be split.')
            uncategorized_charges = incident.spellchecked_charges
            accused_name = incident.accused_name
            categorized_charges = categorize_charges(
                incident_id=incident.id,
                charges=uncategorized_charges,
                accused_name=accused_name
            )
            add_charges_to_charges_table(incident, categorized_charges)


if __name__ == '__main__':
    main()
