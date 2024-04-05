from sqlalchemy import func

from database import get_database_session, Incident


def delete_one_incident_if_names_are_same_except_for_commas(matching_incidents):
    deleted = False
    if matching_incidents[0].accused_name.replace(',', '') == matching_incidents[1].accused_name.replace(',', ''):
        if ',' in matching_incidents[0].accused_name:
            print(
                f"  Deleting Incident ID: {matching_incidents[0].id}, Accused Name: {matching_incidents[0].accused_name}")
            # DBsession.delete(matching_incidents[0])
            # DBsession.commit()
            deleted = True
            return deleted
        elif ',' in matching_incidents[1].accused_name:
            print(
                f"  Deleting Incident ID: {matching_incidents[1].id}, Accused Name: {matching_incidents[1].accused_name}")
            # DBsession.delete(matching_incidents[1])
            # DBsession.commit()
            deleted = True
            return deleted

    return deleted


def delete_one_incident_if_two_exist_for_split_names(DBsession, matching_incidents):
    print('delete_one_incident_if_two_exist_for_split_names')
    # reorder the matching incidents so that the one with the most names is first
    if len(matching_incidents[0].accused_name.split(',')) < len(matching_incidents[1].accused_name.split(',')):
        matching_incidents = [matching_incidents[1], matching_incidents[0]]
    else:
        pass

    print(vars(matching_incidents[0]))
    split_names = [i.strip() for i in matching_incidents[0].accused_name.split(',')]
    split_ages = [i.strip() for i in matching_incidents[0].accused_age.split(',')]
    split_locations = [i.strip() for i in matching_incidents[0].accused_location.split(',')]
    split_charges = [i.strip() for i in matching_incidents[0].charges.split(',')]
    split_legal_actions = [i.strip() for i in matching_incidents[0].legal_actions.split(',')]

    if len(split_charges) == 1:
        split_charges = [split_charges[0] for i in range(len(split_names))]
    if len(split_legal_actions) == 1:
        split_legal_actions = [split_legal_actions[0] for i in range(len(split_names))]

    for index, name in enumerate(split_names):
        location = split_locations[index] if index < len(split_locations) else split_locations[-1]
        new_incident = Incident(
            incident_reported_date=matching_incidents[0].incident_reported_date,
            accused_name=name,
            accused_age=split_ages[index],
            accused_location=location,
            charges=split_charges[index],
            details=matching_incidents[0].details,
            legal_actions=split_legal_actions[index],
            incident_date=matching_incidents[0].incident_date,
            incident_location=matching_incidents[0].incident_location,
            incident_location_lat=matching_incidents[0].incident_location_lat,
            incident_location_lng=matching_incidents[0].incident_location_lng,
            source=matching_incidents[0].source,
        )
        DBsession.add(new_incident)
        DBsession.commit()
        print(f'Incident added for {name}.')

    # delete incident with multiple names
    print(f'  Deleting Incident ID: {matching_incidents[0].id}, Accused Name: {matching_incidents[0].accused_name}')
    DBsession.delete(matching_incidents[0])
    DBsession.commit()


def delete_one_incident_if_name_is_shorter(DBsession, matching_incidents):
    if len(matching_incidents[0].accused_name) < len(matching_incidents[1].accused_name):
        print(
            f"  Deleting Incident ID: {matching_incidents[0].id}, Accused Name: {matching_incidents[0].accused_name}")
        deleted = True
        DBsession.delete(matching_incidents[0])
        DBsession.commit()
    elif len(matching_incidents[1].accused_name) < len(matching_incidents[0].accused_name):
        print(
            f"  Deleting Incident ID: {matching_incidents[1].id}, Accused Name: {matching_incidents[1].accused_name}")
        deleted = True
        DBsession.delete(matching_incidents[1])
        DBsession.commit()
    else:
        print('  No deletion criteria met.')
        deleted = False

    return deleted


def delete_duplicates_by_details_and_name():
    """
    Searchs for & deletes duplicate records from the database by comparing the details and accused_name fields.
    :return:
    """
    DBsession, engine = get_database_session(environment='prod')

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
            if len(matching_incidents) == 2:
                # if the names in the matching incidents are the same except for commas, delete the one with commas
                deleted = delete_one_incident_if_names_are_same_except_for_commas(matching_incidents)
                if deleted:
                    continue
                # if there are 2 names in one incident and 1 name in the other, delete the one with 2 names
                if ',' in matching_incidents[0].accused_name and ',' not in matching_incidents[1].accused_name:
                    deleted = delete_one_incident_if_two_exist_for_split_names(DBsession, matching_incidents)
                elif ',' in matching_incidents[1].accused_name and ',' not in matching_incidents[0].accused_name:
                    deleted = delete_one_incident_if_two_exist_for_split_names(DBsession, matching_incidents)
                if deleted:
                    continue
                # if the details are the same but there's only one name, delete the one with the shorter name
                if len(matching_incidents[0].accused_name) < len(matching_incidents[1].accused_name):
                    # split the names and compare. If they're different, move on.
                    if matching_incidents[0].accused_name.split()[0] == matching_incidents[1].accused_name.split()[0]:
                        if matching_incidents[0].accused_name.split()[-1] == matching_incidents[1].accused_name.split()[-1]:
                            print('Names are the same. Deleting incident with higher ID.')
                            deleted = delete_one_incident_if_name_is_shorter(DBsession, matching_incidents)
                        else:
                            print('Names are different. Not deleting.')
                    else:
                        print('Names are different. Not deleting.')
                if deleted:
                    continue
                # if the details & name are the same, delete the one with the higher ID
                if matching_incidents[0].accused_name == matching_incidents[1].accused_name:
                    if matching_incidents[0].id > matching_incidents[1].id:
                        print(
                            f"  Deleting Incident ID: {matching_incidents[0].id}, Accused Name: {matching_incidents[0].accused_name}")
                        DBsession.delete(matching_incidents[0])
                        DBsession.commit()
                    else:
                        print(
                            f"  Deleting Incident ID: {matching_incidents[1].id}, Accused Name: {matching_incidents[1].accused_name}")
                        DBsession.delete(matching_incidents[1])
                        DBsession.commit()
                else:
                    print('  No deletion criteria met.')

    return


def main():
    delete_duplicates_by_details_and_name()

    return


if __name__ == '__main__':
    main()
