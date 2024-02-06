from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base
from database import Base


class AlreadyScrapedUrls(Base):
    __tablename__ = 'already_scraped_urls'
    __table_args__ = {'schema': 'public'}

    url = Column(String, primary_key=True)