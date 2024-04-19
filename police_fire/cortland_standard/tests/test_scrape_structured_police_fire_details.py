from models.article import Article
from models.incident import Incident
from models.incidents_with_errors import IncidentsWithErrors
from police_fire.cortland_standard.scrape_structured_police_fire_details import scrape_structured_incident_details, \
    identify_articles_with_incident_formatting
from police_fire.cortland_standard.scrape_articles_by_section import login, scrape_article

from police_fire.test_database import setup_database


def test_structure_data_with_matching_counts_gets_added_to_incidents_table(setup_database):
    DBsession = setup_database

    drop_existing_incidents(DBsession)

    logged_in_session = login()
    scrape_article('https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?', logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == 'https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?').first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incident).all()

    assert len(incidents) == 1

    scraped_incident = incidents[0]

    assert scraped_incident.source == 'https://www.cortlandstandard.com/stories/homer-woman-charged-with-dwi,70763?'
    assert scraped_incident.accused_name == 'Julie M. Conners'
    assert scraped_incident.accused_age == '34'
    assert scraped_incident.accused_location == 'Cold Brook Road, Homer'
    assert scraped_incident.charges == 'Driving while intoxicated, a misdemeanor; parked on a highway, a violation'
    assert scraped_incident.details == ('Cortland County sheriff’s officers found Conners’ vehicle parked abut 1:38 '
                                        'a.m. Sunday on Riley Road in Cortlandville. Police said they found Conners '
                                        'intoxicated.')
    assert scraped_incident.legal_actions == 'Conners was ticketed to appear Nov. 27 in Cortlandville Town Court.'

    DBsession.close()
    return


def test_structure_data_with_multiple_incidents_gets_added_correctly(setup_database):
    DBsession = setup_database

    article_url = 'https://www.cortlandstandard.com/stories/groton-driver-charged-after-crash-causes-injury,13070?'

    drop_existing_incidents(DBsession)

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incident).all()

    assert len(incidents) == 9


def drop_existing_incidents(DBsession):
    incidents = DBsession.query(Incident).all()
    for incident in incidents:
        DBsession.delete(incident)
    DBsession.commit()
    return


def test_structure_data_with_multiple_incidents_with_span_tag_gets_added_correctly(setup_database):
    DBsession = setup_database
    article_url = 'https://www.cortlandstandard.com/stories/two-charged-with-drunken-driving,12273?'

    drop_existing_incidents(DBsession)

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incident).all()

    assert len(incidents) == 2
    for incident in incidents:
        assert incident.details != ''


def test_structure_data_with_br_tags_gets_added_correctly(setup_database):
    DBsession = setup_database

    article_url = 'https://www.cortlandstandard.com/stories/10-year-old-hurt-when-vehicle-tips,19473?'
    drop_existing_incidents(DBsession)

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)
    test_article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(test_article, DBsession)
    incidents = DBsession.query(Incident).all()

    assert len(incidents) == 2
    first_incident = incidents[0]
    second_incident = incidents[1]

    assert first_incident.accused_name == 'Wendy Caswell'
    assert first_incident.accused_age == '40'
    assert first_incident.accused_location == 'Cortland'
    assert first_incident.charges == ('Third-degree criminal possession of a controlled substance, third-degree '
                                      'criminal possession of a weapon, criminal possession of a firearm, '
                                      'felonies; three counts of seventh-degree criminal possession of a controlled '
                                      'substance, two counts of ssecond degree criminally using drug paraphernalia '
                                      'and fourth-degree criminal possession of a weapon, misdemeanors')
    assert first_incident.details == ('The Cortland County Drug Task Force executed a search warrant Wednesday of a '
                                      'home on Main Street in Cortland. Officers seized 3 grams of fentanyl, '
                                      'a half-gram of methamphetamine, packaging materials, scales, Tramadol and '
                                      'Alprazolam. The drugs had a street value of more than $400, police said.')
    assert first_incident.legal_actions == ("Caswell was awaiting arraignment Wednesday evening at the Cortland County "
                                            "Sheriff's Office.")

    assert second_incident.accused_name == 'Cypress Jana V. Hill'
    assert second_incident.accused_age == '25'
    assert second_incident.accused_location == 'Groton'
    assert second_incident.charges == ('First-degree burglary, first-degree criminal contempt, felonies; second-degree '
                                       'menacing, a misdemeanor')
    assert second_incident.details == ('Hill kicked open the door to a residence then threatened the resident with a '
                                       'knife on Oct. 9 on Ward Boulevard in Newfield, state police said, '
                                       'violating an order of protection in the process.A day later, Hill menaced the '
                                       'same person with a knife near Miller Hill and Elmira Road in Newfield, '
                                       'police said.')
    assert second_incident.legal_actions == ('Hill was arrested Oct. 14 and taken to Tompkins County central '
                                             'arraignment and awaits an appearance in Newfield Town Court.')


def test_identify_articles_with_incident_formatting_correctly_returns_one_incident(setup_database):
    DBsession = setup_database
    DBsession.query(IncidentsWithErrors).delete()
    DBsession.query(Article).delete()

    article_url = 'https://www.cortlandstandard.com/stories/preble-driver-charged-with-dwi,70053?'

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)

    articles = identify_articles_with_incident_formatting(
        DBsession
    )

    for article in articles:
        print(vars(article))

    assert len(articles) == 1


def test_identify_articles_with_incident_formatting_correctly_returns_0_incidents(setup_database):
    DBsession = setup_database
    DBsession.query(IncidentsWithErrors).delete()
    DBsession.query(Article).delete()

    article_url = 'https://www.cortlandstandard.com/stories/one-charged-with-assault-4-others-arrested-in-palm-gardens-brawl,70665?'

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)

    articles = identify_articles_with_incident_formatting(
        DBsession
    )

    assert len(articles) == 0


def test_duplicate_incident_does_not_get_added_twice(setup_database):
    # test setup - add the article to the database
    DBsession = setup_database
    drop_existing_incidents(DBsession)

    article_url = 'https://www.cortlandstandard.com/stories/preble-driver-charged-with-dwi,70053??'

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)

    article = DBsession.query(Article).where(
        Article.url == article_url).first()

    # scrape the article for the first time
    scrape_structured_incident_details(article, DBsession)
    # check that there are three incidents in the database
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 3

    # scrape the article for the second time
    scrape_structured_incident_details(article, DBsession)
    # assert no new incidents were added
    incidents = DBsession.query(Incident).all()
    assert len(incidents) == 3


def test_scraped_article_gets_added_to_scraped_articles_table(setup_database):
    DBsession = setup_database

    article_url = 'https://www.cortlandstandard.com/stories/preble-driver-charged-with-dwi,70053??'

    logged_in_session = login()
    scrape_article(article_url, logged_in_session,
                   section='Police/Fire', DBsession=DBsession)

    article = DBsession.query(Article).where(
        Article.url == article_url).first()

    scrape_structured_incident_details(article, DBsession)

    scraped_article = DBsession.query(Incident).where(
        Incident.source == article_url).first()

    assert scraped_article.source == article_url
