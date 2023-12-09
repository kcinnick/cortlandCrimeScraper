import regex as re
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from database import get_database_session, Article, Incidents, Persons, AlreadyScrapedUrls
from police_fire.utilities import add_incident_with_error_if_not_already_exists, \
    clean_up_charges_details_and_legal_actions_records, check_if_details_references_a_relative_date, \
    update_incident_date_if_necessary, check_if_details_references_an_actual_date, get_incident_location_from_details, \
    add_or_get_person
from police_fire.maps import get_lat_lng_of_addresses


def identify_articles_with_incident_formatting(db_session):
    """
    Identify articles that contain incidents in the headline or keywords.
    """
    articles = db_session.query(Article).where(Article.section == 'Police/Fire').all()
    articles_with_incidents = []
    for article in articles:
        if 'Accused' in article.html_content and 'Charges' in article.html_content and 'Details' in article.html_content:
            articles_with_incidents.append(article)

    return articles_with_incidents


def scrape_separate_incident_details(separate_incident_tags, article, DBsession):
    separate_incident_tags = [i for i in separate_incident_tags if i.strip() != '']
    if 'Accused' not in separate_incident_tags[0]:
        # remove the first element if it's not an accused record
        separate_incident_tags = separate_incident_tags[1:]
    if len(separate_incident_tags) in [0, 1]:
        print('No separate incident tags found.')
        # add the article to IncidentsWithErrors if it's not already there
        add_incident_with_error_if_not_already_exists(article, DBsession)
        return
    accused_tag_index = 0
    if 'Accused' in separate_incident_tags[accused_tag_index]:
        pass
    else:
        accused_tag_index += 1
        if 'Accused' in separate_incident_tags[accused_tag_index]:
            pass
        else:
            print(f'No Accused found: {separate_incident_tags[accused_tag_index]}')
            return

    charges_tag_index = accused_tag_index + 1
    if 'Charges' in separate_incident_tags[charges_tag_index]:
        charges_str = separate_incident_tags[charges_tag_index]
        pass
    else:
        print(f'No Charges found: {separate_incident_tags[charges_tag_index]}')
        return

    details_tag_index = charges_tag_index + 1
    if 'Details' in separate_incident_tags[details_tag_index]:
        details_str = separate_incident_tags[details_tag_index]
        if 'Legal Actions' not in separate_incident_tags[details_tag_index + 1]:
            details_str += separate_incident_tags[details_tag_index + 1]
            legal_actions_tag_index = details_tag_index + 2
        else:
            legal_actions_tag_index = details_tag_index + 1
        pass
    else:
        print(f'No Details found: {separate_incident_tags[details_tag_index]}')
        return

    try:
        if 'Legal Action' in separate_incident_tags[legal_actions_tag_index]:
            legal_actions_str = separate_incident_tags[legal_actions_tag_index]
        elif 'Legal actions' in separate_incident_tags[legal_actions_tag_index]:
            legal_actions_str = separate_incident_tags[legal_actions_tag_index]
        else:
            print(f'No Legal Action found: {separate_incident_tags[legal_actions_tag_index]}')
            return
    except IndexError:
        legal_actions_tag_index -= 1
        if 'Legal Action' in separate_incident_tags[legal_actions_tag_index]:
            legal_actions_str = separate_incident_tags[legal_actions_tag_index]
        elif 'Legal actions' in separate_incident_tags[legal_actions_tag_index]:
            legal_actions_str = separate_incident_tags[legal_actions_tag_index]
        else:
            print(f'No Legal Action found: {separate_incident_tags[legal_actions_tag_index]}')
            return

    accused_str = separate_incident_tags[accused_tag_index].replace('Accused: ', '')
    accused_name, accused_age, accused_location = clean_up_accused_record(article, accused_str, DBsession)
    accused_person_id = add_or_get_person(DBsession, accused_name)

    # clean up charges, details, and legal actions records
    charges_str, details_str, legal_actions_str = clean_up_charges_details_and_legal_actions_records(
        charges_str, details_str, legal_actions_str)

    incident_date = check_if_details_references_a_relative_date(details_str, article.date_published)
    incident_location = get_incident_location_from_details(details_str)
    incident_lat, incident_lng = get_lat_lng_of_addresses.get_lat_lng_of_address(incident_location)
    incident = Incidents(
        article_id=article.id,
        url=article.url,
        incident_reported_date=article.date_published,
        accused_age=accused_age,
        accused_location=accused_location,
        charges=charges_str,
        details=details_str,
        legal_actions=legal_actions_str,
        structured_source=True,
        incident_date=incident_date,
        incident_location=incident_location,
        incident_location_lat=incident_lat,
        incident_location_lng=incident_lng,
        accused_person_id=accused_person_id,
        accused_name=accused_name
    )

    # add incident to database if it doesn't already exist
    if DBsession.query(Incidents).filter_by(details=details_str, accused_person_id=accused_person_id).count() == 0:
        DBsession.add(incident)
        DBsession.commit()
    else:
        print('Incident already exists. Updating if necessary.')
        incident_date_response = check_if_details_references_a_relative_date(details_str, article.date_published)
        print(incident_date_response)
        if incident_date_response:
            update_incident_date_if_necessary(DBsession, incident_date_response, details_str)

    return


def clean_up_accused_record(article, accused_str, DBsession):
    # clean up accused record
    accused_str = accused_str.replace(': ', '')
    if ', Jr' in accused_str:
        accused_str = accused_str.replace(', Jr.', ' Jr.')
    if ', Sr' in accused_str:
        accused_str = accused_str.replace(', Sr.', ' Sr.')

    if ' and ' in accused_str:
        accused_str = accused_str.replace(' and ', ';')

    if ';' in accused_str:
        print('; in accused_str')
        # only add the article to IncidentsWithErrors if it's not already there
        add_incident_with_error_if_not_already_exists(article, DBsession)

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


def scrape_structured_incident_details(article, DBsession):
    """
    Scrape incident details from article.
    """
    incidents = []
    # get already scraped urls
    alreadyScrapedUrls = DBsession.query(AlreadyScrapedUrls).all()
    alreadyScrapedUrls = [alreadyScrapedUrl.url for alreadyScrapedUrl in alreadyScrapedUrls]
    if article.url in alreadyScrapedUrls:
        print('Article already scraped. Skipping.')
        return
    else:
        print('Article not already scraped. Scraping now.')
        print(article.url)
    soup = BeautifulSoup(article.html_content, 'html.parser')

    # check for <strong> tags first
    accused = soup.find_all('strong', string=re.compile('Accused'))
    # for accused in accused:
    #     print(accused.next_sibling)
    charges = soup.find_all('strong', string=re.compile('Charge[sd]'))
    # for charge in charges:
    #     print(charge.next_sibling)
    details = soup.find_all('strong', string=re.compile('Details'))
    # for detail in details:
    #     print(detail.next_sibling)
    legal_actions = soup.find_all('strong', string=re.compile('Legal [Aa]ction[s:]'))
    # for legal_action in legal_actions:
    #     print(legal_action.next_sibling)

    print(len(accused))
    print(len(charges))
    print(len(details))
    print(len(legal_actions))

    # if len of all of the above is 0, this article may have <br> tag formatting
    if len(accused) == 0 and len(charges) == 0 and len(details) == 0 and len(legal_actions) == 0:
        # check for <br> tag formatting
        main_body = soup.find('div', class_='body main-body clearfix')
        separate_incidents = main_body.find_all('p')
        for separate_incident in separate_incidents:
            br_tags = str(separate_incident).replace('<br>', '<br/>').split('<br/>')
            soupy_br_tags = [BeautifulSoup(br_tag, 'html.parser').text.strip() for br_tag in br_tags if
                             br_tag.strip() != '']
            scrape_separate_incident_details(soupy_br_tags, article, DBsession)
        return

    if len(accused) != len(charges) or len(accused) != len(details) or len(accused) != len(legal_actions):
        add_incident_with_error_if_not_already_exists(article, DBsession)
        return

    for index, accused in enumerate(accused):
        try:
            accused_element = accused.next_sibling
            accused_str = accused_element.text.strip()
            if accused_str == '':
                accused_element = accused.next_sibling.next_sibling
                accused_str = accused_element.text.strip()
            charges_element = charges[index].next_sibling
            charges_str = charges_element.text.strip()
            if charges_str == '':
                charges_element = charges[index].find_next('span')
                charges_str = charges_element.text.strip()
            details_element = details[index].next_sibling
            details_str = details_element.text.strip()
            if details_str == '':
                details_element = details[index].find_next('span')
                details_str = details_element.text.strip()
            legal_actions_element = legal_actions[index].next_sibling
            legal_actions_str = legal_actions_element.text.strip()
            if legal_actions_str == '':
                legal_actions_element = legal_actions[index].find_next('span')
                legal_actions_str = legal_actions_element.text.strip()
        except IndexError:
            print('IndexError')
            add_incident_with_error_if_not_already_exists(article, DBsession)
            continue

        # clean up accused record
        accused_name, accused_age, accused_location = clean_up_accused_record(article, accused_str, DBsession)
        accused_person_id = add_or_get_person(DBsession, accused_name)

        # clean up charges, details, and legal actions records
        charges_str, details_str, legal_actions_str = clean_up_charges_details_and_legal_actions_records(
            charges_str, details_str, legal_actions_str)

        # check if details references a relative date
        incident_date_response = check_if_details_references_a_relative_date(details_str, article.date_published)
        if not incident_date_response:
            # check if details references an actual date
            incident_date_response = check_if_details_references_an_actual_date(details_str, article.date_published)

        incident_location = get_incident_location_from_details(details_str)
        response = get_lat_lng_of_addresses.get_lat_lng_of_address(incident_location)
        if response:
            incident_lat, incident_lng = response
        else:
            incident_lat, incident_lng = None, None

        incident = Incidents(
            article_id=article.id,
            url=article.url,
            incident_reported_date=article.date_published,
            accused_age=accused_age,
            accused_location=accused_location,
            charges=charges_str,
            details=details_str,
            legal_actions=legal_actions_str,
            structured_source=True,
            incident_date=incident_date_response,
            incident_location=incident_location,
            incident_location_lat=incident_lat,
            incident_location_lng=incident_lng,
            accused_person_id=accused_person_id
        )

        # add incident to database if it doesn't already exist
        if DBsession.query(Incidents).filter_by(accused_person_id=accused_person_id, details=details_str).count() == 0:
            try:
                DBsession.add(incident)
                DBsession.commit()
            except IntegrityError as e:
                print('Integrity error: ', e)
                DBsession.rollback()
        else:
            print('Incident already exists. Updating if necessary.')
            if incident_date_response:
                update_incident_date_if_necessary(DBsession, incident_date_response, details_str)
            incident_location = get_incident_location_from_details(details_str)
            if incident_location:
                lat, lng = get_lat_lng_of_addresses.get_lat_lng_of_address(incident_location)
                existing_incident = DBsession.query(Incidents).filter_by(details=details_str).first()
                existing_incident.incident_location = incident_location
                existing_incident.incident_location_lat = lat
                existing_incident.incident_location_lng = lng
                DBsession.add(existing_incident)
                DBsession.commit()
                print('Incident location updated for ' + existing_incident.url)

    return


def main():
    database_session, engine = get_database_session(environment='prod')
    articles_with_incidents = identify_articles_with_incident_formatting(database_session)
    # reverse the list so that the most recent articles are scraped first
    articles_with_incidents = articles_with_incidents[::-1]
    print(f'{len(articles_with_incidents)} articles with incident formatting.')
    try:
        for index, article in enumerate(articles_with_incidents):
            print('\n---Scraping article ' + str(index + 1) + ' of ' + str(len(articles_with_incidents)) + '---\n')
            scrape_structured_incident_details(article, database_session)
    finally:
        database_session.close()


if __name__ == '__main__':
    main()
