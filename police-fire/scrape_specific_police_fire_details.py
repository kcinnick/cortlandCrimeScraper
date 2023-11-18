import regex as re
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from database import engine, Article, Incidents, IncidentsWithErrors, Session as DBSession


def identify_articles_with_incident_formatting():
    """
    Identify articles that contain incidents in the headline or keywords.
    """
    DBsession = DBSession()
    articles = DBsession.query(Article).where(Article.section == 'Police/Fire').all()
    articles_with_incidents = []
    for article in articles:
        if 'Accused:' in article.html_content and 'Charges:' in article.html_content and 'Details:' in article.html_content:
            articles_with_incidents.append(article)

    return articles_with_incidents


def scrape_incident_details(article):
    """
    Scrape incident details from article.
    """
    DBsession = DBSession()
    print(article.url)
    soup = BeautifulSoup(article.html_content, 'html.parser')
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

    if len(accused) != len(charges) or len(accused) != len(details) or len(accused) != len(legal_actions):
        incidentWithError = IncidentsWithErrors(
            article_id=article.id,
            url=article.url
        )
        try:
            DBsession.add(incidentWithError)
            DBsession.commit()
        except IntegrityError:
            DBsession.rollback()
        finally:
            DBsession.close()
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
            details_element = details[index].next_sibling
            details_str = details_element.text.strip()
            legal_actions_element = legal_actions[index].next_sibling
            legal_actions_str = legal_actions_element.text.strip()
        except IndexError:
            incidentWithError = IncidentsWithErrors(
                article_id=article.id,
                url=article.url
            )
            try:
                DBsession.add(incidentWithError)
                DBsession.commit()
            except IntegrityError:
                DBsession.rollback()
            finally:
                DBsession.close()
            continue

        # clean up accused record
        accused_str = accused_str.replace(': ', '')
        if ', Jr' in accused_str:
            accused_str = accused_str.replace(', Jr.', ' Jr.')
        if ', Sr' in accused_str:
            accused_str = accused_str.replace(', Sr.', ' Sr.')

        if ' and ' in accused_str:
            accused_str = accused_str.replace(' and ', ';')

        if ';' in accused_str:
            incidentWithError = IncidentsWithErrors(
                article_id=article.id,
                url=article.url
            )
            try:
                DBsession.add(incidentWithError)
                DBsession.commit()
            except IntegrityError:
                DBsession.rollback()
            finally:
                DBsession.close()
            continue

        accused_name = accused_str.split(',')[0].strip()
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

        # clean up charges, details, and legal actions records
        if charges_str.startswith(': '):
            charges_str = charges_str[2:]
        if details_str.startswith(': '):
            details_str = details_str[2:]
        if legal_actions_str.startswith(': '):
            legal_actions_str = legal_actions_str[2:]

        incident = Incidents(
            article_id=article.id,
            url=article.url,
            accused_name=accused_name,
            accused_age=accused_age,
            accused_location=accused_location,
            charges=charges_str,
            details=details_str,
            legal_actions=legal_actions_str
        )

        # add incident to database if it doesn't already exist
        try:
            DBsession.add(incident)
            DBsession.commit()
        except IntegrityError:
            DBsession.rollback()
        finally:
            DBsession.close()

    return


def main():
    articles_with_incidents = identify_articles_with_incident_formatting()
    print(f'{len(articles_with_incidents)} articles with incident formatting.')
    for index, article in enumerate(articles_with_incidents):
        print('\n---Scraping article ' + str(index + 1) + ' of ' + str(len(articles_with_incidents)) + '---\n')
        scrape_incident_details(article)


if __name__ == '__main__':
    main()
