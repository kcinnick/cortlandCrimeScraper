import os

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from sqlalchemy import Column, Integer, String, Date

database_username = os.getenv('DATABASE_USERNAME')
database_password = os.getenv('DATABASE_PASSWORD')

# SQLAlchemy connection string for PostgreSQL
DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard'

Base = declarative_base()

engine = create_engine(DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)


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


def create_tables():
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    create_tables()
