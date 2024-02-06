import os

import unicodedata
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from tqdm import tqdm

Base = declarative_base()


def get_database_session(environment='development'):
    print('environment==', environment)
    database_username = os.getenv('DATABASE_USERNAME')
    database_password = os.getenv('DATABASE_PASSWORD')
    print("database_username: ", database_username)
    print("database_password: ", database_password)

    # SQLAlchemy connection string for PostgreSQL
    if environment == 'test':
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_test'
    elif environment == 'development':
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_dev'
    elif environment == 'dev':
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_dev'
    else:
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard'

    engine = create_engine(DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    return db_session, engine


def remove_non_standard_characters(string):
    # Normalize unicode characters
    if string is None:
        return None
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    # Replace unwanted characters, e.g., line breaks, extra spaces
    string = string.replace("\n", "").replace("\r", "").strip()
    return string


def clean_strings_in_table(environment):
    from models.incident import Incident
    DBsession, engine = get_database_session(environment)
    # get the Incidents table
    incidents = DBsession.query(Incident).all()
    for incident in tqdm(incidents):
        incident.accused_location = remove_non_standard_characters(incident.accused_location)
        incident.charges = remove_non_standard_characters(incident.charges)
        incident.details = remove_non_standard_characters(incident.details)
        incident.legal_actions = remove_non_standard_characters(incident.legal_actions)
        incident.incident_location = remove_non_standard_characters(incident.incident_location)
        DBsession.commit()

    return


if __name__ == "__main__":
    clean_strings_in_table('dev')
