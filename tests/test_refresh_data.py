from datetime import date
import json
from unittest.mock import Mock

import pytest

from models.article import Article
from models.incident import Incident
from police_fire.test_database import setup_database
from police_fire.cortland_voice import scrape_articles
from police_fire.refresh_data import backfill_incident_dates, parse_article, validate_incidents, main


def article():
    return Article(url='https://cortlandvoice.com/2026/11/25/example/',
                   date_published=date(2026, 11, 25), content='Fixture text')


def payload():
    return {'incidents': [{
        'accused_name': 'Example Person', 'charges': 'Example allegation',
        'details': 'Reported incident', 'legal_actions': 'N/A', 'accused_age': 'N/A',
        'accused_location': 'N/A', 'incident_location': 'N/A', 'incident_date': None,
    }]}


def test_parse_idempotent(setup_database):
    session = setup_database
    source = article()
    session.add(source)
    session.commit()
    query = Mock(return_value=json.dumps(payload()))
    assert parse_article(session, source, query) == 1
    assert parse_article(session, source, query) == 0
    assert query.call_count == 1
    record = session.query(Incident).one()
    assert record.cortlandVoiceSource == source.url
    assert record.incident_date is None
    assert source.incidents_verified is False


def test_parse_invalid_atomic(setup_database):
    source = article()
    setup_database.add(source)
    setup_database.commit()
    response = payload()
    response['incidents'].append({'accused_name': 'Incomplete'})
    with pytest.raises(ValueError):
        parse_article(setup_database, source, lambda query: json.dumps(response))
    assert setup_database.query(Incident).count() == 0
    assert not source.incidents_scraped


def test_existing_partial_article_requires_review(setup_database):
    source = article()
    setup_database.add_all([source, Incident(cortlandVoiceSource=source.url)])
    setup_database.commit()
    with pytest.raises(ValueError, match='manual review'):
        parse_article(setup_database, source, Mock())


def test_future_date_rejected():
    response = payload()
    response['incidents'][0]['incident_date'] = '2026-11-26'
    with pytest.raises(ValueError):
        validate_incidents(response, article())


def test_validate_infers_each_incident_separately():
    response = payload()
    response['incidents'][0]['legal_actions'] = 'Charged Tuesday.'
    second = dict(response['incidents'][0], accused_name='Second Person', legal_actions='Charged Monday.')
    response['incidents'].append(second)
    records = validate_incidents(response, article())
    assert [record.incident_date for record in records] == [date(2026, 11, 24), date(2026, 11, 23)]


def test_validate_preserves_explicit_occurrence_date():
    response = payload()
    response['incidents'][0].update(incident_date='2026-11-12', legal_actions='Charged Tuesday.')
    assert validate_incidents(response, article())[0].incident_date == date(2026, 11, 12)


def test_backfill_preview_apply_and_rerun(setup_database):
    source = article()
    missing = Incident(cortlandVoiceSource=source.url, details='Charged Tuesday.')
    existing = Incident(cortlandVoiceSource=source.url, details='Charged Monday.', incident_date=date(2026, 11, 10))
    unknown = Incident(cortlandVoiceSource=source.url, details='No event date.', legal_actions='Court Tuesday.')
    unrelated = Incident(cortlandVoiceSource=source.url + 'other', details='Charged Tuesday.')
    setup_database.add_all([source, missing, existing, unknown, unrelated])
    setup_database.commit()
    preview = backfill_incident_dates(setup_database, source)
    assert preview == [{'incident_id': missing.id, 'incident_date': '2026-11-24'}]
    assert missing.incident_date is None
    assert backfill_incident_dates(setup_database, source, apply=True) == preview
    setup_database.expire_all()
    assert missing.incident_date == date(2026, 11, 24)
    assert existing.incident_date == date(2026, 11, 10)
    assert unknown.incident_date is unrelated.incident_date is None
    assert backfill_incident_dates(setup_database, source, apply=True) == []


def test_backfill_cli_no_discovery_or_paid_api(setup_database, monkeypatch):
    from police_fire import refresh_data
    source = article()
    record = Incident(cortlandVoiceSource=source.url, details='Charged Tuesday.')
    setup_database.add_all([source, record])
    setup_database.commit()
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    discovery, parse = Mock(), Mock()
    monkeypatch.setattr(refresh_data, 'get_article_urls', discovery)
    monkeypatch.setattr(refresh_data, 'parse_article', parse)
    main(['--backfill-dates', '--max-articles', '1'])
    assert record.incident_date is None
    discovery.assert_not_called()
    parse.assert_not_called()


def test_backfill_production_backup_failure_prevents_updates(setup_database, monkeypatch):
    from police_fire import refresh_data
    source = article()
    record = Incident(cortlandVoiceSource=source.url, details='Charged Tuesday.')
    setup_database.add_all([source, record])
    setup_database.commit()
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    monkeypatch.setattr(refresh_data, 'backup_database', Mock(side_effect=RuntimeError('backup failed')))
    backfill = Mock()
    monkeypatch.setattr(refresh_data, 'backfill_incident_dates', backfill)
    with pytest.raises(RuntimeError, match='backup failed'):
        main(['--backfill-dates', '--apply', '--environment', 'production'])
    backfill.assert_not_called()


def test_scrape_article_duplicate_does_not_fetch(setup_database, monkeypatch):
    source = article()
    setup_database.add(source)
    setup_database.commit()
    fetch = Mock()
    monkeypatch.setattr(scrape_articles, 'fetch_article', fetch)
    assert scrape_articles.scrape_article(source.url, setup_database).id == source.id
    fetch.assert_not_called()


def test_fetch_parses_html(monkeypatch):
    response = Mock(content=b'<h1 itemprop="headline">Example</h1><div class="post-author">by Betty</div><div class="post-date">November 25, 2026</div><div itemprop="articleBody">Fixture body</div>')
    get = Mock(return_value=response)
    monkeypatch.setattr(scrape_articles.requests, 'get', get)
    fetched = scrape_articles.fetch_article(article().url)
    assert fetched.author == 'Betty'
    assert fetched.date_published == date(2026, 11, 25)
    assert get.call_args.kwargs['timeout'] == 30
    response.raise_for_status.assert_called_once()


def test_parser_requires_apply():
    with pytest.raises(SystemExit):
        main(['--parse'])


def test_audit_only_no_fetch(setup_database, monkeypatch):
    from police_fire import refresh_data
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    fetch = Mock()
    monkeypatch.setattr(refresh_data, 'get_article_urls', fetch)
    main(['--audit-only'])
    fetch.assert_not_called()


def test_parse_only_no_discovery(setup_database, monkeypatch):
    from police_fire import refresh_data
    source = article()
    setup_database.add(source)
    setup_database.commit()
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    discovery = Mock()
    parse = Mock(return_value=1)
    monkeypatch.setattr(refresh_data, 'get_article_urls', discovery)
    monkeypatch.setattr(refresh_data, 'parse_article', parse)
    main(['--apply', '--parse-only', '--max-articles', '1'])
    discovery.assert_not_called()
    parse.assert_called_once()


def test_preview_bounded_no_writes(setup_database, monkeypatch):
    from police_fire import refresh_data
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    monkeypatch.setattr(refresh_data, 'get_article_urls', lambda page: [article().url, article().url + 'second'])
    fetch = Mock(side_effect=lambda url: article())
    monkeypatch.setattr(refresh_data, 'fetch_article', fetch)
    monkeypatch.setattr(refresh_data.time, 'sleep', lambda seconds: None)
    add = Mock(wraps=setup_database.add)
    commit = Mock(wraps=setup_database.commit)
    monkeypatch.setattr(setup_database, 'add', add)
    monkeypatch.setattr(setup_database, 'commit', commit)
    main(['--max-articles', '1'])
    assert fetch.call_count == 1
    add.assert_not_called()
    commit.assert_not_called()


def test_production_backup_failure_stops_ingestion(setup_database, monkeypatch):
    from police_fire import refresh_data
    monkeypatch.setattr(refresh_data, 'get_database_session', lambda *args, **kwargs: (setup_database, setup_database.bind))
    monkeypatch.setattr(refresh_data, 'backup_database', Mock(side_effect=RuntimeError('backup failed')))
    discovery = Mock()
    monkeypatch.setattr(refresh_data, 'get_article_urls', discovery)
    with pytest.raises(RuntimeError, match='backup failed'):
        main(['--environment', 'production', '--apply'])
    discovery.assert_not_called()

