from datetime import date
import json
from unittest.mock import Mock

import pytest

from models.article import Article
from models.incident import Incident
from police_fire.test_database import setup_database
from police_fire.cortland_standard.import_articles import load_export, validate_standard_url
from police_fire import refresh_data


def row():
    return {'url': 'https://www.cortlandstandard.com/news/example-article.html',
            'headline': 'Synthetic test article', 'date_published': '2026-11-27',
            'content': 'Synthetic fixture content, not real reporting.'}


def write_export(tmp_path, rows):
    path = tmp_path / 'standard-export.json'
    path.write_text(json.dumps({'articles': rows}), encoding='utf-8')
    return path


def payload():
    return {'incidents': [{'accused_name': 'Fixture Person', 'charges': 'Fixture charge',
                          'details': 'Synthetic details', 'legal_actions': 'N/A',
                          'accused_age': 'N/A', 'accused_location': 'N/A',
                          'incident_location': 'N/A', 'incident_date': None}]}


def test_export_validation(tmp_path):
    articles = load_export(write_export(tmp_path, [row()]))
    assert articles[0].date_published == date(2026, 11, 27)
    assert articles[0].section == 'Police/Fire'
    assert not articles[0].incidents_scraped
    assert not articles[0].incidents_verified


@pytest.mark.parametrize('url', ['https://cortlandstandard.com.evil.test/a',
                                'http://www.cortlandstandard.com/a',
                                'https://user:password@www.cortlandstandard.com/a',
                                'https://www.cortlandstandard.com/a?tracking=1',
                                'https://www.cortlandstandard.com/'])
def test_bad_source_urls_rejected(url):
    with pytest.raises(ValueError):
        validate_standard_url(url)


@pytest.mark.parametrize('field,value', [('content', ''), ('headline', None),
                                       ('date_published', 'not-a-date')])
def test_invalid_metadata_rejected(tmp_path, field, value):
    record = row()
    record[field] = value
    with pytest.raises(ValueError):
        load_export(write_export(tmp_path, [record]))


def test_duplicate_export_urls_rejected(tmp_path):
    with pytest.raises(ValueError, match='Duplicate'):
        load_export(write_export(tmp_path, [row(), row()]))


def test_standard_attribution_and_rerun(tmp_path, setup_database):
    source = load_export(write_export(tmp_path, [row()]))[0]
    setup_database.add(source)
    setup_database.commit()
    query = Mock(return_value=json.dumps(payload()))
    assert refresh_data.parse_article(setup_database, source, query) == 1
    assert refresh_data.parse_article(setup_database, source, query) == 0
    result = setup_database.query(Incident).one()
    assert result.cortlandStandardSource == source.url
    assert result.cortlandVoiceSource is None
    assert result.incident_date is None
    assert not source.incidents_verified
    query.assert_called_once()


def test_standard_partial_extraction_stops(tmp_path, setup_database):
    source = load_export(write_export(tmp_path, [row()]))[0]
    setup_database.add_all([source, Incident(cortlandStandardSource=source.url)])
    setup_database.commit()
    with pytest.raises(ValueError, match='manual review'):
        refresh_data.parse_article(setup_database, source, Mock())


def test_standard_validation_atomic(tmp_path, setup_database):
    source = load_export(write_export(tmp_path, [row()]))[0]
    setup_database.add(source)
    setup_database.commit()
    response = payload()
    response['incidents'].append({'accused_name': 'Incomplete'})
    with pytest.raises(ValueError):
        refresh_data.parse_article(setup_database, source, lambda query: json.dumps(response))
    assert setup_database.query(Incident).count() == 0
    assert not source.incidents_scraped


def configure_cli_session(monkeypatch, session):
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (session, session.bind))
    monkeypatch.setattr(session.bind, 'dispose', Mock())
    discovery = Mock(side_effect=AssertionError('Standard import must not discover website URLs'))
    monkeypatch.setattr(refresh_data, 'get_article_urls', discovery)
    return discovery


def test_import_preview_no_writes(tmp_path, setup_database, monkeypatch):
    path = write_export(tmp_path, [row()])
    discovery = configure_cli_session(monkeypatch, setup_database)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    refresh_data.main(['--source', 'standard', '--import-file', str(path)])
    assert setup_database.query(Article).count() == 0
    discovery.assert_not_called()


def test_import_apply_bounded_and_idempotent(tmp_path, setup_database, monkeypatch):
    second = row()
    second['url'] = 'https://www.cortlandstandard.com/news/second.html'
    path = write_export(tmp_path, [row(), second])
    configure_cli_session(monkeypatch, setup_database)
    args = ['--source', 'standard', '--import-file', str(path), '--apply', '--max-articles', '1']
    refresh_data.main(args)
    assert setup_database.query(Article).count() == 1
    refresh_data.main(args)
    assert setup_database.query(Article).count() == 2
    refresh_data.main(args)
    assert setup_database.query(Article).count() == 2


def test_standard_cli_parse_selects_only_standard(tmp_path, setup_database, monkeypatch):
    standard = load_export(write_export(tmp_path, [row()]))[0]
    voice = Article(url='https://cortlandvoice.com/example/', incidents_scraped=False,
                    date_published=date(2026, 11, 27), content='Synthetic text')
    setup_database.add_all([standard, voice])
    setup_database.commit()
    configure_cli_session(monkeypatch, setup_database)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    parse = Mock(return_value=0)
    monkeypatch.setattr(refresh_data, 'parse_article', parse)
    refresh_data.main(['--source', 'standard', '--parse-only', '--apply'])
    assert parse.call_count == 1
    assert parse.call_args.args[1].url == standard.url


def test_standard_discovery_fails_before_database(monkeypatch):
    db = Mock()
    monkeypatch.setattr(refresh_data, 'get_database_session', db)
    with pytest.raises(SystemExit):
        refresh_data.main(['--source', 'standard'])
    db.assert_not_called()


def test_invalid_export_fails_before_backup(tmp_path, monkeypatch):
    db = Mock()
    monkeypatch.setattr(refresh_data, 'get_database_session', db)
    record = row()
    record['content'] = ''
    with pytest.raises(ValueError):
        refresh_data.main(['--source', 'standard', '--import-file', str(write_export(tmp_path, [record])),
                           '--environment', 'production', '--apply'])
    db.assert_not_called()

