from datetime import date
from unittest.mock import Mock

import pytest

from flask_app.app import app, get_request_session, get_incidents_by_year
from models.article import Article
from models.incident import Incident
from models.charges import Charges
from police_fire.test_database import setup_database


@pytest.fixture
def client(setup_database):
    original = dict(app.config)
    app.config.update(TESTING=True, READ_ONLY=True, WTF_CSRF_ENABLED=True,
                      SECRET_KEY='test-only', ADMIN_TOKEN=None,
                      DATABASE_SESSION_FACTORY=lambda: (setup_database, None))
    try:
        yield app.test_client()
    finally:
        app.config.clear()
        app.config.update(original)


def test_empty_home_and_year_api(client):
    assert client.get('/').status_code == 200
    assert client.get('/api/incidents_by_year').json == {}


def test_null_dates_supported():
    assert get_incidents_by_year([Incident(), Incident(incident_reported_date=date(2024, 1, 1))]) == {2024: 1}


@pytest.mark.parametrize('path', ['/delete-incident/1', '/update-verification/1',
                                 '/add-incident', '/rescrape/cortland-voice/1'])
def test_read_only_blocks_all_mutations(client, path):
    assert client.post(path).status_code == 403


def test_get_cannot_trigger_rescraping(client):
    assert client.get('/rescrape/cortland-voice/1').status_code == 405


def test_admin_token_and_csrf_required(client):
    app.config.update(READ_ONLY=False, ADMIN_TOKEN='test-admin')
    assert client.post('/delete-incident/1').status_code == 403
    assert client.post('/delete-incident/1', headers={'X-Admin-Token': 'test-admin'}).status_code == 400


def test_missing_records_404(client):
    assert client.get('/incidents/999').status_code == 404
    assert client.get('/verify-article/999').status_code == 404


def test_new_incident_visible(client, setup_database):
    record = Incident(accused_name='Fixture Person', charges='Fixture charge',
                      details='Fixture details', incident_location='Cortland',
                      incident_reported_date=date(2024, 5, 30))
    setup_database.add(record)
    setup_database.commit()
    response = client.get(f'/incidents/{record.id}')
    assert response.status_code == 200
    assert b'Fixture charge' in response.data
    assert b'Read-only preview' in response.data
    assert b'Incident Location' in response.data
    assert client.get('/incidents').status_code == 200


def test_null_charge_names_are_excluded(client, setup_database):
    setup_database.add_all([Charges(crime=None), Charges(crime='Fixture charge')])
    setup_database.commit()
    assert client.get('/data').json == ['Fixture charge']


def test_delete_resolves_article_before_removal(client, setup_database):
    source = Article(url='https://cortlandvoice.com/example/')
    record = Incident(cortlandVoiceSource=source.url)
    setup_database.add_all([source, record])
    setup_database.commit()
    incident_id, article_id = record.id, source.id
    setup_database.add(Charges(incident_id=incident_id))
    setup_database.commit()
    app.config.update(READ_ONLY=False, ADMIN_TOKEN='test-admin', WTF_CSRF_ENABLED=False)
    response = client.post(f'/delete-incident/{incident_id}', headers={'X-Admin-Token': 'test-admin'})
    assert response.status_code == 302
    assert response.location.endswith(f'/verify-article/{article_id}')
    assert setup_database.query(Incident).count() == 0
    assert setup_database.query(Charges).count() == 0


def test_session_lifetime(monkeypatch):
    session, engine = Mock(), Mock()
    factory = Mock(return_value=(session, engine))
    monkeypatch.setitem(app.config, 'DATABASE_SESSION_FACTORY', factory)
    with app.app_context():
        assert get_request_session() is session
        assert get_request_session() is session
    factory.assert_called_once()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    engine.dispose.assert_called_once()


def test_missing_pdf_is_404(client):
    assert client.get('/verify-article/pdfs/2024/not-a-month/12').status_code == 404
    assert client.get('/verify-article/pdfs/2024/02/31').status_code == 404

