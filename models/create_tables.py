# test_model.py

from base import Base
from database import get_database_session
from models.article import Article
from models.charges import Charges
from models.incident import Incident
from models.incidents_with_errors import IncidentsWithErrors

if __name__ == "__main__":
    DBsession, engine = get_database_session(environment='test')
    Base.metadata.create_all(engine)
