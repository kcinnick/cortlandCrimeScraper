from sqlalchemy.exc import IntegrityError
from database import get_database_session, Incident


# get all addresses in Incidents table
# for each address, check if it's in Addresses table
# if not, add it to Addresses table
# if so, do nothing

def main():
    db_session, engine = get_database_session(environment='prod')
    incidents = db_session.query(Incident).all()
    for incident in incidents:
        people = incident.accused_name.split(',')
        people = [person.strip() for person in people]
        for person in people:
            person = Persons(
                name=person,
            )
            try:
                db_session.add(person)
                db_session.commit()
            except IntegrityError:
                print('Person already exists in database.')
                db_session.rollback()


if __name__ == '__main__':
    main()
