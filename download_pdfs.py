import os
from time import sleep

from bs4 import BeautifulSoup
from tqdm import tqdm

from utilities import login


def get_eeditions_urls(logged_in_session, page_number=1):
    r = logged_in_session.get(
        f'https://www.cortlandstandard.com/eeditions/?page_size=18&sub_type=eeditions&page={page_number}')
    sleep(5)
    soup = BeautifulSoup(r.content, 'html.parser')
    eeditions_container = soup.find('div', {'class': 'content-list row'})
    urls = []
    eeditions_title_containers = eeditions_container.find_all('h3')
    for eeditions_title_container in eeditions_title_containers:
        urls.append('https://www.cortlandstandard.com' + eeditions_title_container.find('a')['href'])

    return urls


def get_pdf_url(logged_in_session, eedition_url):
    print(eedition_url)
    r = logged_in_session.get(eedition_url)
    soup = BeautifulSoup(r.content, 'html.parser')
    links = soup.find_all('a')
    for link in links:
        #print(link)
        url = link.get('href')
        if url:
            if 'cortland/files' in url:
                break

    return url


def main():
    logged_in_session = login()
    page_number = 0
    while True:
        page_number += 1
        print(f'page_number: {page_number}')
        urls = get_eeditions_urls(logged_in_session, page_number=page_number)
        if len(urls) == 0:
            break
        for url in tqdm(urls):
            pdf_title = url.split('/')[-1].split(',')[0]
            if pdf_title.startswith('saturday-'):
                pdf_title = pdf_title.replace('saturday-', '')
            if pdf_title.startswith('december6'):
                pdf_title = pdf_title.replace('december6', 'december-6')
            if pdf_title.startswith('november23'):
                pdf_title = pdf_title.replace('november23', 'november-23')
            try:
                month, day, year = pdf_title.split('-')
            except ValueError as e:
                print(pdf_title)
                raise e
            if not os.path.exists(f'pdfs/{year}'):
                os.mkdir(f'pdfs/{year}')
            if not os.path.exists(f'pdfs/{year}/{month}'):
                os.mkdir(f'pdfs/{year}/{month}')
            if not os.path.exists(f'pdfs/{year}/{month}/{day}'):
                os.mkdir(f'pdfs/{year}/{month}/{day}')
            # if pdf_title not already in pdfs/ folder, download the pdf
            pdf_path = f'pdfs/{year}/{month}/{day}/{pdf_title}.pdf'
            if os.path.exists(pdf_path):
                continue
            sleep(5)
            try:
                pdf_url = get_pdf_url(logged_in_session, url)
            except AttributeError:
                raise AttributeError(f'pdf_url not found for {url}')
                continue
            r = logged_in_session.get(pdf_url)
            with open(f'{pdf_path}', 'wb') as f:
                f.write(r.content)


if __name__ == '__main__':
    main()
