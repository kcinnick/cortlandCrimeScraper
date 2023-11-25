import glob
import re

from tika import parser

from police_fire.utilities import add_incident_with_error_if_not_already_exists
from database import IncidentsFromPdf, get_database_session


def get_accused_names(pdf_content_as_string):
    accused_names = []
    results = re.findall('(?s)Accused:(.*?)Charges:', pdf_content_as_string)
    accused_names.extend([accused_name.strip().replace('\n', '') for accused_name in results])
    return accused_names


def get_accused_charges(pdf_content_as_string):
    accused_charges = []
    results = re.findall('(?s)Charges:(.*?)Details?:', pdf_content_as_string)
    for result in results:
        result = result.replace('\n', '')
        accused_charges.append(result)

    return accused_charges


def get_charge_details(pdf_content_as_string):
    charge_details = []
    results = re.findall('(?s)Details?:(.*?)Legal', pdf_content_as_string)
    charge_details.extend(results)
    return charge_details


def get_legal_actions(pdf_content_as_string):
    legal_actions = []
    results = re.findall('(?s)Legal Action[s]:(.*?)\n', pdf_content_as_string)
    legal_actions.extend(results)
    return legal_actions


def clean_up_accused_record(accused_str):
    # clean up accused record
    accused_str = accused_str.replace(': ', '')
    if ', Jr' in accused_str:
        accused_str = accused_str.replace(', Jr.', ' Jr.')
    if ', Sr' in accused_str:
        accused_str = accused_str.replace(', Sr.', ' Sr.')

    if ' and ' in accused_str:
        accused_str = accused_str.replace(' and ', ';')

    accused_name = accused_str.split(',')[0].strip().split(' of ')[0].strip()
    try:
        accused_age = accused_str.split(',')[1].strip()
    except IndexError:
        accused_age = None
    # if accused_age isn't a digit, it's probably a location
    if accused_age and not accused_age.isdigit():
        accused_age = None

    if ' of ' in accused_name:
        accused_location = accused_name.split(' of ')[1]
    elif accused_age:
        accused_location_index = 2
        accused_location = None
    else:
        accused_location_index = 1
        accused_location = None

    if not accused_location:
        try:
            accused_location = ', '.join([i.strip() for i in accused_str.split(',')[accused_location_index:]])
            if accused_location[-1] == '.':
                accused_location = accused_location[:-1]
            if accused_location.startswith('of '):
                accused_location = accused_location[3:]
        except IndexError:
            if accused_location.strip() == '':
                accused_location = None
            else:
                print(accused_location)
                raise IndexError('accused_location was incorrectly formatted.')

    return accused_name, accused_age, accused_location


def get_data_from_pdf(year, month, day_number, DBsession):
    pdf_glob_path = rf'C:\Users\Nick\PycharmProjects\cortlandStandardScraper\pdfs\{year}\{month}\{day_number}\*'
    try:
        pdf_path = glob.glob(pdf_glob_path)[0]
    except IndexError:
        print(f'No PDF found for {year}-{month}-{day_number}.')
        return
    print(pdf_path)
    raw = parser.from_file(pdf_path)
    pdf_content_as_string = raw['content']

    names = get_accused_names(pdf_content_as_string)
    accused_charges = get_accused_charges(pdf_content_as_string)
    charge_details = get_charge_details(pdf_content_as_string)
    legal_actions = get_legal_actions(pdf_content_as_string)

    for index, name in enumerate(names):
        print('---')
        accused_name, accused_age, accused_location = clean_up_accused_record(name)
        incidentFromPdf = IncidentsFromPdf(
            incident_reported_date=f'{year}-{month}-{day_number}',
            accused_name=accused_name,
            accused_age=accused_age,
            accused_location=accused_location,
            charges=accused_charges[index],
            details=charge_details[index],
            legal_actions=legal_actions[index]
        )
        DBsession.add(incidentFromPdf)
        DBsession.commit()

    return


def main():
    DBsession, engine = get_database_session(test=True)
    years = ['2019']
    months = ['aug']
    day_numbers = [str(day_number) for day_number in range(1, 32)]
    for year in years:
        for month in months:
            for day_number in day_numbers:
                get_data_from_pdf(year, month, day_number, DBsession)


if __name__ == '__main__':
    main()
