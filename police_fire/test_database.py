import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from base import Base

database_username = os.getenv('DATABASE_USERNAME')
database_password = os.getenv('DATABASE_PASSWORD')


@pytest.fixture(scope="function")
def setup_database():
    # Connect to your test database
    environment = 'dev'

    print(environment)
    engine = create_engine(
        f'postgresql+psycopg2://{database_username}:{database_password}@localhost:5432/cortlandstandard_' + environment, )
    Base.metadata.create_all(engine)  # Create tables

    # Create a new session for testing
    db_session = scoped_session(sessionmaker(bind=engine))

    yield db_session  # Provide the session for testing

    db_session.close()
    tables = ['public.scraped_articles', 'public.charges', 'public.incidents_with_errors', 'public.incidents',
              'public.articles']
    for table_name in tables:
        table = Base.metadata.tables.get(table_name)
        if table is not None:
            table.drop(engine, checkfirst=True)

    return
