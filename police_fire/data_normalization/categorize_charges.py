import os

from openai import OpenAI
from tqdm import tqdm

from database import get_database_session
from models.charges import Charges
from police_fire.utilities import get_response_for_query

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

DBsession, engine = get_database_session(environment='prod')

charge_types = {
    'DUI/DWI': [],
    'Traffic Violations': [],
    'Weapons Charges': [],
    'Theft Charges': [],
    'Failure to Comply': [],
    'Drug Charges': [],
    'License Violations': [],
    'Registration Violations': [],
    'False Information': [],
    'Evading Arrest': [],
    'Identification Charges': [],
    'Equipment Violations': [],
    'Animal Charges': [],
    'Public Intoxication': [],
    'Reckless Driving': [],
    'Disorderly Conduct': [],
    'Document Tampering': [],
    'Obstruction of Justice': [],
    'Sexual Offenses': [],
    'Endangering Welfare': []
}


def categorize_charge(charge):
    response_dict = {
        '1': 'DUI/DWI',
        '2': 'Traffic Violations',
        '3': 'Weapons Charges',
        '4': 'Theft Charges',
        '5': 'Failure to Comply',
        '6': 'Drug Charges',
        '7': 'License Violations',
        '8': 'Registration Violations',
        '9': 'False Information',
        '10': 'Evading Arrest',
        '11': 'Identification Charges',
        '12': 'Equipment Violations',
        '13': 'Animal Charges',
        '14': 'Public Intoxication',
        '15': 'Reckless Driving',
        '16': 'Disorderly Conduct',
        '17': 'Document Tampering',
        '18': 'Obstruction of Justice',
        '19': 'Sexual Offenses',
        '20': 'Endangering Welfare',
        '21': 'Assault',
        '22': 'Fraud',
        '23': 'Harassment',
        '24': 'Family offense',
        '25': 'Conspiracy',
        '26': 'Criminal Mischief',
        '27': 'Murder or attempted murder',
        '28': 'Menacing',
        '29': 'Violation of probation',
        '30': 'Unlawful imprisonment',
        '31': 'Trespass',
        '32': 'Unlawful possession of alcohol',
        '33': 'Vandalism',
        '34': 'Manslaughter',
        '35': 'Kidnapping or attempted kidnapping',
        '36': 'Witness or victim intimidation',
        '37': 'Manslaughter',
        '38': 'Making a terroristic threat',
        '39': 'Arson or attempted arson',
        '40': 'Criminal contempt',
        '41': 'Escape or attempted escape',
        '42': 'Unlawful sale of alcohol',
        '43': 'Stalking',
        '44': 'Sex offender registry violation',
        '45': 'Leaving the scene of an accident',
        '46': 'Promoting prison contraband',
        '47': 'Other',

    }
    print('\nIncident ID: ', charge.incident_id)
    print(charge.crime)
    print('What category does this charge belong to?\n')
    response = input('1: DUI/DWI, 2: Traffic Violations, 3: Weapons Charges, 4: Theft Charges, 5: Failure to '
                     'Comply\n6: Drug Charges, 7: License Violations, 8: Registration Violations, '
                     '9: False Information\n10: Evading Arrest, 11: Identification Charges, 12: Equipment Violations, '
                     '13: Animal Charges, 14: Public Intoxication\n15: Reckless Driving, 16: Disorderly Conduct, '
                     '17: Document Tampering, 18: Obstruction of Justice\n19: Sexual Offenses, 20: Endangering '
                     'Welfare, 21: Assault, 22: Fraud, 23: Harassment, 24. Family offense, 25. Conspiracy\n'
                     '26. Criminal Mischief, 27. Murder or attempted murder, 28. Menacing, 29. Violation of '
                     'probation/parole\n'
                     '30. Unlawful imprisonment, 31. Trespass, 32. Unlawful possession of alcohol, 33. Vandalism, '
                     '\n34. Manslaughter, 35. Kidnapping or attempted kidnapping, 36. Witness or victim intimidation,'
                     '37. Manslaughter\n38. Making a terroristic threat, 39. Arson or attempted arson, 40. Criminal '
                     'contempt,'
                     '41. Escape or attempted escape\n42. Unlawful sale of alcohol, 43. Stalking, 44. Sex offender '
                     'registry violation'
                     '\n45. Leaving the scene of an accident, 46. Promoting prison contraband, 47. Other\n\n> ')
    if response.strip() == '':
        return
    if response == 'exit':
        return

    # now get all charges with that crime
    charges = DBsession.query(Charges).filter_by(crime=charge.crime).all()
    for charge in charges:
        charge.category = response_dict[response]
    DBsession.commit()

    return


def main():
    # get charges one after another where category is null
    # charges = DBsession.query(Charges).filter_by(category=None).all()

    # get charges where category is 'Other'
    charges = DBsession.query(Charges).filter_by(category='Other').all()
    for charge in tqdm(charges):
        categorize_charge(charge)

    pass


if __name__ == '__main__':
    main()
