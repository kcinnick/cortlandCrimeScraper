# contains helper functions that are useful for both structured and unstructured data.
import re

from database import IncidentsWithErrors, Incidents, Article


def delete_table_contents(DBsession):
    DBsession.query(IncidentsWithErrors).delete()
    DBsession.query(Incidents).delete()
    DBsession.query(Article).delete()
    DBsession.commit()

    return


def add_incident_with_error_if_not_already_exists(article, DBsession):
    if DBsession.query(IncidentsWithErrors).filter_by(article_id=article.id).count() == 0:
        incidentWithError = IncidentsWithErrors(
            article_id=article.id,
            url=article.url
        )
        DBsession.add(incidentWithError)
        DBsession.commit()

    return


def clean_up_charges_details_and_legal_actions_records(charges_str, details_str, legal_actions_str):
    if charges_str.startswith(': '):
        charges_str = charges_str[2:]
    else:
        charges_str = charges_str.replace('Charges: ', '')
    if details_str.startswith(': '):
        details_str = details_str[2:]
    else:
        details_str = details_str.replace('Details: ', '')
    if legal_actions_str.startswith(': '):
        legal_actions_str = legal_actions_str[2:]
    else:
        legal_actions_str = re.sub(r'Legal [Aa]ctions: ', '', legal_actions_str)

    return charges_str, details_str, legal_actions_str
