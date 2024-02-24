# test_model.py
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from base import Base
from database import get_database_session
from models.already_scraped_pdfs import AlreadyScrapedPdfs
from models.already_scraped_urls import AlreadyScrapedUrls
from models.article import Article
from models.charges import Charges
from models.incident import Incident
from models.incidents_with_errors import IncidentsWithErrors

if __name__ == "__main__":
    DBsession, engine = get_database_session(environment='test')
    Base.metadata.create_all(engine)
