import os

import unicodedata
from sqlalchemy import create_engine, ForeignKey, MetaData
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

from sqlalchemy import Column, Integer, String, Date, Boolean, text
from tqdm import tqdm

Base = declarative_base()


def get_database_session(test=False):
    database_username = os.getenv('DATABASE_USERNAME')
    database_password = os.getenv('DATABASE_PASSWORD')

    # SQLAlchemy connection string for PostgreSQL
    if test:
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_test'
    else:
        DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard'

    engine = create_engine(DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    return db_session, engine


class Article(Base):
    __tablename__ = 'article'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    headline = Column(String)
    section = Column(String)
    keywords = Column(String)
    author = Column(String)
    date_published = Column(Date)
    url = Column(String, unique=True)
    content = Column(String)
    html_content = Column(String)


class IncidentsWithErrors(Base):
    __tablename__ = 'incidents_with_errors'
    __table_args__ = {'schema': 'public'}

    article_id = Column(Integer, ForeignKey('public.article.id'))  # Assuming 'public' schema and 'article' table
    article = relationship("Article")  # This creates a link to the Article model

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True)


class Incidents(Base):
    __tablename__ = 'incidents'
    __table_args__ = {'schema': 'public'}

    article_id = Column(Integer, ForeignKey('public.article.id'))  # Assuming 'public' schema and 'article' table
    article = relationship("Article")  # This creates a link to the Article model

    id = Column(Integer, autoincrement=True, primary_key=True)
    url = Column(String, primary_key=True)
    incident_reported_date = Column(Date, primary_key=True)
    accused_name = Column(String, primary_key=True)
    accused_age = Column(String, nullable=True)
    accused_location = Column(String)
    charges = Column(String, primary_key=True)
    details = Column(String, primary_key=True)
    legal_actions = Column(String)
    structured_source = Column(Boolean)
    incident_date = Column(Date, nullable=True)
    incident_location = Column(String, nullable=True)
    incident_location_lat = Column(String, nullable=True)
    incident_location_lng = Column(String, nullable=True)

    def __str__(self):
        return f'{self.incident_reported_date} - {self.url} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.structured_source} - {self.incident_date}'


class IncidentsFromPdf(Base):
    __tablename__ = 'incidents_from_pdf'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, autoincrement=True, primary_key=True)
    incident_reported_date = Column(Date, primary_key=True)
    accused_name = Column(String, primary_key=True)
    accused_age = Column(String, nullable=True)
    accused_location = Column(String)
    charges = Column(String, primary_key=True)
    details = Column(String, primary_key=True)
    legal_actions = Column(String)
    incident_date = Column(Date, nullable=True)
    incident_location = Column(String, nullable=True)
    incident_location_lat = Column(String, nullable=True)
    incident_location_lng = Column(String, nullable=True)

    def __str__(self):
        return f'{self.incident_reported_date} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.incident_date}'


class CombinedIncidents(Base):
    __tablename__ = 'combined_incidents'  # Name of the view
    id = Column(Integer, primary_key=True)
    incident_reported_date = Column(Date)
    incident_date = Column(Date)
    accused_name = Column(String)
    accused_age = Column(Integer)
    accused_location = Column(String)
    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)
    incident_location = Column(String, nullable=True)


class Persons(Base):
    __tablename__ = 'persons'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    age = Column(Integer)
    location = Column(String)
    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)
    incident_date = Column(Date, nullable=True)
    incident_location = Column(String, nullable=True)
    incident_location_lat = Column(String, nullable=True)
    incident_location_lng = Column(String, nullable=True)

    def __str__(self):
        return f'{self.name}'


class Addresses(Base):
    __tablename__ = 'addresses'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, unique=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String)

    lat = Column(String)
    lng = Column(String)

    def __str__(self):
        return f'{self.address}'


class PersonAddress(Base):
    __tablename__ = 'PersonAddress'
    __table_args__ = {'schema': 'public'}

    PersonID = Column(Integer, ForeignKey('public.persons.id'), primary_key=True)
    AddressID = Column(Integer, ForeignKey('public.addresses.id'), primary_key=True)
    AsOfDate = Column(Date)


def create_tables(test):
    print('test==', test)
    DBsession, engine = get_database_session(test=test)
    if test:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        article = Article(
            url='https://www.cortlandstandard.com/stories/policefire-march-9-2022,9090?',
        )
        DBsession.add(article)
        DBsession.commit()
        DBsession.close()
    else:
        Base.metadata.create_all(engine)


def create_view(test):
    print('test==', test)
    create_view_sql = text("""
    CREATE OR REPLACE VIEW public.combined_incidents AS
SELECT 
    incident_reported_date::date, 
    accused_name, 
    accused_age, 
    accused_location, 
    charges, 
    details, 
    legal_actions, 
    incident_date::date,
    incident_location,
    incident_location_lat,
    incident_location_lng
FROM incidents
UNION ALL
SELECT 
    incident_reported_date::date, 
    accused_name, 
    accused_age, 
    accused_location, 
    charges, 
    details, 
    legal_actions, 
    incident_date::date,
    incident_location,
    incident_location_lat,
    incident_location_lng
FROM incidents_from_pdf;
    """)
    DBsession, engine = get_database_session(test=test)
    with engine.connect() as connection:
        connection.execute(create_view_sql)
    DBsession.close()


def remove_non_standard_characters(string):
    # Normalize unicode characters
    if string is None:
        return None
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    # Replace unwanted characters, e.g., line breaks, extra spaces
    string = string.replace("\n", "").replace("\r", "").strip()
    return string


def clean_strings_in_table(test=False):
    DBsession, engine = get_database_session(test=test)
    # get the Incidents table
    incidents = DBsession.query(Incidents).all()
    for incident in tqdm(incidents):
        incident.accused_name = remove_non_standard_characters(incident.accused_name)
        incident.accused_location = remove_non_standard_characters(incident.accused_location)
        incident.charges = remove_non_standard_characters(incident.charges)
        incident.details = remove_non_standard_characters(incident.details)
        incident.legal_actions = remove_non_standard_characters(incident.legal_actions)
        incident.incident_location = remove_non_standard_characters(incident.incident_location)
        DBsession.commit()

    incidents_from_pdf = DBsession.query(IncidentsFromPdf).all()
    for incident in tqdm(incidents_from_pdf):
        incident.accused_name = remove_non_standard_characters(incident.accused_name)
        incident.accused_location = remove_non_standard_characters(incident.accused_location)
        incident.charges = remove_non_standard_characters(incident.charges)
        incident.details = remove_non_standard_characters(incident.details)
        incident.legal_actions = remove_non_standard_characters(incident.legal_actions)
        incident.incident_location = remove_non_standard_characters(incident.incident_location)
        DBsession.commit()

    return


if __name__ == "__main__":
    create_tables(test=False)
    create_view(test=False)
    # clean_strings_in_table(
    #    test=False
    # )
