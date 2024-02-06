from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base

from database import Base


class Charges(Base):
    __tablename__ = 'charges'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    charge_description = Column(String)
    charge_class = Column(String)  # felony, misdemeanor, violation, traffic_infraction
    degree = Column(String, nullable=True)
    charged_name = Column(String, nullable=True)

    incident_id = Column(Integer, ForeignKey('public.incident.id'))

    def __str__(self):
        return f'{self.charged_name}, {self.charge_description}, {self.charge_class}, {self.degree}, {self.incident_id}'
