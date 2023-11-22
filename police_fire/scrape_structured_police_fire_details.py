import regex as re
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from database import get_database_session, Article, Incidents
from police_fire.utilities import add_incident_with_error_if_not_already_exists, \
    clean_up_charges_details_and_legal_actions_records


def identify_articles_with_incident_formatting(db_session):
    """
    Identify articles that contain incidents in the headline or keywords.
    """
    articles = db_session.query(Article).where(Article.section == 'Police/Fire').all()
    articles_with_incidents = []
    for article in articles:
        if 'Accused:' in article.html_content and 'Charges:' in article.html_content and 'Details:' in article.html_content:
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

    # clean up charges, details, and legal actions records
    charges_str, details_str, legal_actions_str = clean_up_charges_details_and_legal_actions_records(
        charges_str, details_str, legal_actions_str)

    incident = Incidents(
        article_id=article.id,
        url=article.url,
        incident_reported_date=article.date_published,
        accused_name=accused_name,
        accused_age=accused_age,
        accused_location=accused_location,
        charges=charges_str,
        details=details_str,
        legal_actions=legal_actions_str,
        structured_source=True
    )

    # add incident to database if it doesn't already exist
    if DBsession.query(Incidents).filter_by(details=details_str).count() == 0:
        DBsession.add(incident)
        DBsession.commit()

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

        # clean up charges, details, and legal actions records
        charges_str, details_str, legal_actions_str = clean_up_charges_details_and_legal_actions_records(
            charges_str, details_str, legal_actions_str)

        incident = Incidents(
            article_id=article.id,
            url=article.url,
            incident_reported_date=article.date_published,
            accused_name=accused_name,
            accused_age=accused_age,
            accused_location=accused_location,
            charges=charges_str,
            details=details_str,
            legal_actions=legal_actions_str,
            structured_source=True
        )

        # add incident to database if it doesn't already exist
        if DBsession.query(Incidents).filter_by(details=details_str).count() == 0:
            try:
                DBsession.add(incident)
                DBsession.commit()
            except IntegrityError as e:
                print('Integrity error: ', e)
                DBsession.rollback()

    return


def main():
    database_session, engine = get_database_session(test=False)
    articles_with_incidents = identify_articles_with_incident_formatting(database_session)
    print(f'{len(articles_with_incidents)} articles with incident formatting.')
    try:
        for index, article in enumerate(articles_with_incidents):
            print('\n---Scraping article ' + str(index + 1) + ' of ' + str(len(articles_with_incidents)) + '---\n')
            scrape_structured_incident_details(article, database_session)
    finally:
        database_session.close()


if __name__ == '__main__':
    main()
