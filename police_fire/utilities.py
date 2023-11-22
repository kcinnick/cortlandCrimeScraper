# contains helper functions that are useful for both structured and unstructured data.
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
