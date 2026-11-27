import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from base import Base
from models.article import Article
from models.incident import Incident
from models.charges import Charges
from models.incidents_with_errors import IncidentsWithErrors


@pytest.fixture(scope="function")
def setup_database():
    engine = create_engine('sqlite:///:memory:').execution_options(
        schema_translate_map={'public': None}
    )
    Base.metadata.create_all(engine)
    db_session = scoped_session(sessionmaker(bind=engine))
    try:
        yield db_session
    finally:
        db_session.remove()
        engine.dispose()
