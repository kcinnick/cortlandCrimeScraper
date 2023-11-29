from sqlalchemy import Column, Integer, String, Date

from database import Base


class Persons(Base):
    __tablename__ = 'persons'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

    def __str__(self):
        return f'{self.name}'
