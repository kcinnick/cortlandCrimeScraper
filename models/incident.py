from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import declarative_base

from database import Base


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