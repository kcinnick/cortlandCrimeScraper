import os

import unicodedata
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from models.incident import Incident
from models.charges import Charges
from models.article import Article
from base import Base


def get_database_session(environment='development', create_tables=True):
    database_username = os.getenv('DATABASE_USERNAME')
    database_password = os.getenv('DATABASE_PASSWORD')
    databases = {
        'test': 'cortlandstandard_test',
        'development': 'cortlandstandard_dev', 'dev': 'cortlandstandard_dev',
        'production': 'cortlandstandard', 'prod': 'cortlandstandard',
    }
    if environment not in databases:
        raise ValueError(f'Unknown database environment: {environment!r}')
    DATABASE_URI = URL.create(
        'postgresql+psycopg2', username=database_username,
        password=database_password, host=os.getenv('DATABASE_HOST', 'localhost'),
        port=int(os.getenv('DATABASE_PORT', '5432')), database=databases[environment],
    )

    engine = create_engine(DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    # create tables if they don't exist
    if create_tables:
        Base.metadata.create_all(engine, Base.metadata.tables.values(), checkfirst=True)

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
    db_session, engine = get_database_session(environment='development')

