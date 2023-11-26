import ast
import glob
import os
from time import sleep

from openai import OpenAI
from pdf2image import convert_from_path
from simpleaichat import AIChat
from tqdm import tqdm

from database import IncidentsFromPdf, get_database_session

from PyPDF2 import PdfFileWriter, PdfReader, PdfWriter
import pytesseract

from police_fire.utilities import check_if_details_references_a_relative_date, \
    check_if_details_references_an_actual_date

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
DBsession, engine = get_database_session(test=False)

ai = AIChat(
    console=False,
    save_messages=False,  # with schema I/O, messages are never saved
    model="gpt-4",
    params={"temperature": 0.0},
    api_key=os.getenv('OPENAI_API_KEY'),
)

month_str_to_int = {
    'jan': '01',
    'feb': '02',
    'mar': '03',
    'apr': '04',
    'may': '05',
    'jun': '06',
    'jul': '07',
    'aug': '08',
    'sep': '09',
    'oct': '10',
    'nov': '11',
    'dec': '12'
}


def get_pdf_path(year, month, day):
    pdf_glob_path = rf'C:\Users\Nick\PycharmProjects\cortlandStandardScraper\pdfs\{year}\{month}\{day}\*'
    try:
        pdf_path = glob.glob(pdf_glob_path)[-1]
        return pdf_path
    except IndexError:
        print(f'No PDF found for {year}-{month}-{day}.')
        return


def scrape_police_fire_data_from_pdf(pdf_path, year_month_day_str):
    print(pdf_path)
    pages_path = '\\'.join(pdf_path.split('\\')[:-1]) + '\\pages'
    if not os.path.exists(pages_path):
        os.mkdir(pages_path)

    try:
        input_pdf = PdfReader(pdf_path)
    except PermissionError:
        print('PermissionError')
        return
    output = PdfWriter()
    page_object = input_pdf.pages[2]
    output.add_page(page_object)

    policeFirePagePath = pages_path + '\\' + "police_fire_page.pdf"
    with open(policeFirePagePath, "wb") as output_stream:
        output.write(output_stream)

    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    doc = convert_from_path(policeFirePagePath,
                            poppler_path=r'C:\Users\Nick\Downloads\Release-23.11.0-0\poppler-23.11.0\Library\bin')
    path, fileName = os.path.split(policeFirePagePath)

    query = "List all of the incident details provided in the following string, in the original language of the article.  Use a Python-style dictionaries with the keys \'accused_name\', \'accused_age\', \'accused_location\', \'charges\', \'details\', \'legal_actions\'. All values need to be strings. If the article is not about a crime, the output should be N/A."

    for page_number, page_data in enumerate(doc):
        txt = pytesseract.pytesseract.image_to_string(page_data).encode("utf-8")
        try:
            police_fire_txt = str(txt).split('Police/')[1]
        except IndexError:
            print('No police/fire details found.  Not adding to database.')
            return
        raw_incidents = ['Accused:' + i for i in police_fire_txt.split('Accused:')][1:]
        for raw_incident in raw_incidents:
            query_with_incident = query + raw_incident
            response = ai(query_with_incident)
            response_as_dict = ast.literal_eval(response)
            incident_date_response = check_if_details_references_a_relative_date(response_as_dict['details'],
                                                                                 year_month_day_str)
            if not incident_date_response:
                # check if details references an actual date
                incident_date_response = check_if_details_references_an_actual_date(response_as_dict['details'],
                                                                                    year_month_day_str)
            existing_incident = DBsession.query(IncidentsFromPdf).filter(
                IncidentsFromPdf.incident_reported_date == year_month_day_str,
                IncidentsFromPdf.accused_name == response_as_dict['accused_name'],
                IncidentsFromPdf.charges == response_as_dict['charges'],
                IncidentsFromPdf.details == response_as_dict['details']
            ).all()
            existing_incident = existing_incident[0] if len(existing_incident) > 0 else None
            if existing_incident:
                print('Existing incident found.  Not adding to database.')
                continue
            else:
                incidentFromPdf = IncidentsFromPdf(
                    incident_reported_date=year_month_day_str,
                    accused_name=response_as_dict['accused_name'],
                    accused_age=response_as_dict['accused_age'],
                    accused_location=response_as_dict['accused_location'],
                    charges=response_as_dict['charges'],
                    details=response_as_dict['details'],
                    legal_actions=response_as_dict['legal_actions'],
                    incident_date=incident_date_response
                )
                DBsession.add(incidentFromPdf)
                DBsession.commit()
                sleep(1)

    return


def main():
    years = [
        '2016',
        '2017',
        '2018',
        '2019',
        '2020',
        '2021',
        '2022'
    ]
    months = [
        'jan',
        'feb',
        'mar',
        'apr',
        'may',
        'jun',
        'jul'
        'aug',
        'sep',
        'oct',
        'nov',
        'dec',
    ]
    day_numbers = [str(day_number) for day_number in range(1, 32)]
    for year in tqdm(years, desc='year'):
        for month in tqdm(months, desc='month'):
            for day_number in tqdm(day_numbers, desc='day'):
                year_month_day_str = f'{year}-{month}-{day_number}'
                pdf_path = get_pdf_path(year, month, day_number)
                if not pdf_path:
                    continue
                else:
                    scrape_police_fire_data_from_pdf(pdf_path, year_month_day_str)


if __name__ == '__main__':
    main()
