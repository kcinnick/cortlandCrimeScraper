from sqlalchemy import Column, Integer, String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, declarative_base

from database import Base


class IncidentsWithErrors(Base):
    __tablename__ = 'incidents_with_errors'
    __table_args__ = {'schema': 'public'}

    article_id = Column(Integer, ForeignKey('public.article.id'))
    article = relationship("Article")  # This creates a link to the Article model

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True)
