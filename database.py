import os

import unicodedata
from sqlalchemy import Column, Integer, String, Date, text, UniqueConstraint, Boolean
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
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

    article_id = Column(Integer, ForeignKey('public.article.id'))
    article = relationship("Article")  # This creates a link to the Article model

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True)


from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Incident(Base):
    __tablename__ = 'incident'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_reported_date = Column(Date)
    accused_name = Column(String)
    accused_age = Column(String, nullable=True)
    accused_location = Column(String)
    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)
    incident_date = Column(Date, nullable=True)
    incident_location = Column(String, nullable=True)
    incident_location_lat = Column(String, nullable=True)
    incident_location_lng = Column(String, nullable=True)

    # Foreign Key to Source table
    source = Column(String)

    # charges_relationship = relationship('Charges', back_populates='incident')

    def __str__(self):
        return f'{self.incident_reported_date} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.incident_date}'


class Incidents(Base):
    __tablename__ = 'incidents'

    article_id = Column(Integer, ForeignKey('public.article.id'))  # Assuming 'public' schema and 'article' table
    # incident_persons = relationship('IncidentPerson', back_populates='incidents')

    id = Column(Integer, autoincrement=True, primary_key=True)
    url = Column(String)

    incident_reported_date = Column(Date)

    accused_name = Column(String)
    accused_age = Column(String, nullable=True)
    accused_location = Column(String)

    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)

    structured_source = Column(Boolean)

    incident_date = Column(Date, nullable=True)

    incident_location = Column(String, nullable=True)
    incident_location_lat = Column(String, nullable=True)
    incident_location_lng = Column(String, nullable=True)

    # article = relationship("Article")  # This creates a link to the Article model
    # charges_relationship = relationship('Charges', back_populates='incidents')

    __table_args__ = (
        UniqueConstraint(
            'url', 'incident_reported_date', 'charges', 'accused_name',
            name='uix_url_incident_reported_date_charges_accused_name'),
        {'schema': 'public'},
    )

    def __str__(self):
        return f'{self.incident_reported_date} - {self.url} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.structured_source} - {self.incident_date}'


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


class Charges(Base):
    __tablename__ = 'charges'
    __table_args__ = (
        UniqueConstraint('charge_description', 'charge_class', 'degree', name='unique_charge_combination'),
        {'schema': 'public'},
    )

    # Define the relationships
    # persons = relationship('Persons', back_populates='charges')
    # incident = relationship('Incident', back_populates='charges_relationship')

    id = Column(Integer, primary_key=True, autoincrement=True)
    charge_description = Column(String)
    charge_class = Column(String)  # felony, misdemeanor, violation, traffic_infraction
    degree = Column(String, nullable=True)

    # person_id = Column(Integer, ForeignKey('public.persons.id'))
    incident_id = Column(Integer, ForeignKey('public.incident.id'))

    def __str__(self):
        return f'{self.charge_description}, {self.charge_class}, {self.degree}'


class AlreadyScrapedUrls(Base):
    __tablename__ = 'already_scraped_urls'
    __table_args__ = {'schema': 'public'}

    url = Column(String, primary_key=True)


class AlreadyScrapedPdfs(Base):
    __tablename__ = 'already_scraped_pdfs'
    __table_args__ = {'schema': 'public'}

    pdf_date = Column(String, primary_key=True)


def create_tables(environment='development'):
    print('environment==', environment)
    DBsession, engine = get_database_session(environment)
    if environment == 'test':
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


def create_view_for_already_scraped_urls(environment='test'):
    print('environment==', environment)
    create_view_sql = text(
        """CREATE OR REPLACE VIEW public.already_scraped_urls AS
            SELECT
                DISTINCT url
            FROM
            incidents""")
    DBsession, engine = get_database_session(environment=environment)
    with engine.connect() as connection:
        connection.execute(create_view_sql)
    DBsession.close()


def create_view_for_already_scraped_pdfs(environment='test'):
    print('environment==', environment)
    create_view_sql = text(
        """CREATE OR REPLACE VIEW public.already_scraped_pdfs AS
            SELECT
                incident_reported_date
            FROM
            incidents_from_pdf""")
    DBsession, engine = get_database_session(environment=environment)
    with engine.connect() as connection:
        connection.execute(create_view_sql)
    DBsession.close()


def remove_non_standard_characters(string):
    # Normalize unicode characters
    if string is None:
        return None
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    # Replace unwanted characters, e.g., line breaks, extra spaces
    string = string.replace("\n", " ").replace("\r", " ").strip()
    return string


def clean_strings_in_table(environment):
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
    # create_tables(environment='development')
    # create_view(environment='development')
    # create_view_for_already_scraped_urls(environment='prod')
    clean_strings_in_table(
        environment='prod'
    )

# helpful query for finding duplicates:
# SELECT
#     accused_person_id,
#     incident_reported_date,
#     incident_location,
#     COUNT(*) as duplicate_count
# FROM
#     incidents
# GROUP BY
#     accused_person_id,
#     incident_reported_date,
#     incident_location
# HAVING
#     COUNT(*) > 1
# ORDER BY
#     duplicate_count DESC;
