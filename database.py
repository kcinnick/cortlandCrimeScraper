import os

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from sqlalchemy import Column, Integer, String, Date, Boolean

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

    id = Column(Integer, primary_key=True)
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

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)


class Incidents(Base):
    __tablename__ = 'incidents'
    __table_args__ = {'schema': 'public'}

    article_id = Column(Integer, ForeignKey('public.article.id'))  # Assuming 'public' schema and 'article' table
    article = relationship("Article")  # This creates a link to the Article model

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    accused_name = Column(String)
    accused_age = Column(String)
    accused_location = Column(String)
    charges = Column(String)
    details = Column(String)
    legal_actions = Column(String)
    structured_source = Column(Boolean)

    def __str__(self):
        return f'{self.article_id} - {self.url} - {self.accused_name} - {self.accused_age} - {self.accused_location} - {self.charges} - {self.details} - {self.legal_actions} - {self.structured_source}'


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


if __name__ == "__main__":
    create_tables(test=False)
