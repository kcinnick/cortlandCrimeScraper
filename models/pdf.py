from sqlalchemy import Column, Integer, String, Date, Boolean

from base import Base


class Pdf(Base):
    __tablename__ = 'pdf'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, unique=True)
    date_published = Column(Date)

    incidents_scraped = Column(Boolean, default=True)
    incidents_verified = Column(Boolean, default=False)