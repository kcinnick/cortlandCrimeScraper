from sqlalchemy import func

from database import get_database_session, Incident


def delete_duplicates_by_details_and_name():
    """
    Searchs for & deletes duplicate records from the database by comparing the details and accused_name fields.
    :return:
    """
    DBsession, engine = get_database_session(test=False)

    normalized_details = func.regexp_replace(Incident.details, '\\s+', ' ', 'g')

    # Query to find potential duplicates based on normalized 'details'
    potential_duplicates = (DBsession.query(normalized_details, func.count())
                            .group_by(normalized_details)
                            .having(func.count() > 1)
                            .all())

    for duplicate in potential_duplicates:
        normalized_detail, count = duplicate
        if count > 1:
            print(f"Normalized Details: {normalized_detail}, Count: {count}")
            # Query to find all incidents with these details
            matching_incidents = DBsession.query(Incident).filter(
                func.regexp_replace(Incident.details, '\\s+', ' ', 'g') == normalized_detail).all()
            for incident in matching_incidents:
                print(f"  Incident ID: {incident.id}, Accused Name: {incident.accused_name}")
            # if the name is N/A, just move on
            if matching_incidents[0].accused_name == 'N/A':
                continue
            # if the names in the matching incidents are the same except for commas, delete the one with commas
            if len(matching_incidents) == 2:
                if matching_incidents[0].accused_name.replace(',', '') == matching_incidents[1].accused_name.replace(',', ''):
                    if ',' in matching_incidents[0].accused_name:
                        print(f"  Deleting Incident ID: {matching_incidents[0].id}, Accused Name: {matching_incidents[0].accused_name}")
                        DBsession.delete(matching_incidents[0])
                        DBsession.commit()
                        continue
                    elif ',' in matching_incidents[1].accused_name:
                        print(f"  Deleting Incident ID: {matching_incidents[1].id}, Accused Name: {matching_incidents[1].accused_name}")
                        DBsession.delete(matching_incidents[1])
                        DBsession.commit()
                        continue

    return


def main():
    delete_duplicates_by_details_and_name()

    return


if __name__ == '__main__':
    main()
