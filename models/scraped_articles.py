from sqlalchemy import Column, String, Boolean

from base import Base


class ScrapedArticles(Base):
    __tablename__ = 'scraped_articles'
    __table_args__ = {'schema': 'public'}

    path = Column(String, primary_key=True)
    incidents_scraped = Column(Boolean, default=False)
    incidents_verified = Column(Boolean, default=False)
