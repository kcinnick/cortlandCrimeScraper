import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Column, Integer, String, Date

database_username = os.getenv('DATABASE_USERNAME')
database_password = os.getenv('DATABASE_PASSWORD')

# SQLAlchemy connection string for PostgreSQL
DATABASE_URI = f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard'

Base = declarative_base()

engine = create_engine(DATABASE_URI, echo=True)
Session = sessionmaker(bind=engine)


class Article(Base):
    __tablename__ = 'article'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True)
    title = Column(String)
    section = Column(String)
    author = Column(String)
    publish_date = Column(Date)
    url = Column(String)
    content = Column(String)
    html_content = Column(String)


def create_tables():
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    create_tables()
