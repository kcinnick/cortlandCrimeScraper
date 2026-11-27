from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import database
from police_fire.utilities import utilities


def test_injected_openai_client():
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=' {"date": "2026-11-25"} '))]
    )
    assert utilities.get_response_for_query('Extract date', client=client) == '{"date": "2026-11-25"}'
    assert client.chat.completions.create.call_args.kwargs['response_format'] == {'type': 'json_object'}


def test_location_parsing(monkeypatch):
    monkeypatch.setattr(utilities, 'get_response_for_query', lambda query: '{"location": "110 Main Street, Cortland, New York"}')
    assert utilities.get_incident_location_from_details('Example text') == '110 Main Street, Cortland, New York'


def test_unknown_environment_rejected():
    with pytest.raises(ValueError, match='Unknown database environment'):
        database.get_database_session('typo')


@pytest.mark.parametrize('environment,name', [
    ('test', 'cortlandstandard_test'), ('dev', 'cortlandstandard_dev'),
    ('development', 'cortlandstandard_dev'), ('prod', 'cortlandstandard'),
    ('production', 'cortlandstandard'),
])
def test_database_routing_no_secret_output(monkeypatch, capsys, environment, name):
    monkeypatch.setenv('DATABASE_PASSWORD', 'test-secret@:/')
    create = Mock(return_value=Mock())
    monkeypatch.setattr(database, 'create_engine', create)
    monkeypatch.setattr(database.Base.metadata, 'create_all', Mock())
    session, engine = database.get_database_session(environment)
    assert create.call_args.args[0].database == name
    assert create.call_args.args[0].password == 'test-secret@:/'
    assert 'test-secret' not in capsys.readouterr().out
    session.close()
