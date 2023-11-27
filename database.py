import os

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from sqlalchemy import Column, Integer, String, Date, Boolean, text

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

    def __str__(self):
        return f'{self.incident_reported_date} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.incident_date}'


class CombinedIncidents(Base):
    __tablename__ = 'combined_incidents'  # Name of the view
    id = Column(Integer, primary_key=True)
    incident_reported_date = Column(Date)
    accused_name = Column(String)
    accused_age = Column(Integer)
    accused_location = Column(String)
    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)
    incident_location = Column(String, nullable=True)


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
    SELECT incident_reported_date, accused_name, accused_age, accused_location, charges, details, legal_actions, incident_location
    FROM incidents
    UNION ALL
    SELECT incident_reported_date, accused_name, accused_age, accused_location, charges, details, legal_actions, incident_location
    FROM incidents_from_pdf;
    """)
    DBsession, engine = get_database_session(test=test)
    with engine.connect() as connection:
        connection.execute(create_view_sql)
    DBsession.close()


if __name__ == "__main__":
    create_tables(test=False)
    create_view(test=False)
