from datetime import date
from unittest.mock import Mock

import pytest

from models.article import Article
from police_fire.test_database import setup_database
from police_fire.cortland_voice.import_saved_article import main, read_saved_article

URL = 'https://cortlandvoice.com/2026/11/25/synthetic-report/'
CONTENT = 'Synthetic source reporting. ' * 10


def html(body=None):
    return f'''<html><head><title>Synthetic report</title><link rel="canonical" href="{URL}"><meta name="author" content="Synthetic reporter"><meta property="article:published_time" content="2026-11-26T02:00:00+00:00"></head><body><h1>Synthetic report</h1><div class="post-date">November 25, 2026</div><div itemprop="articleBody">{body if body is not None else '<p>' + CONTENT + '</p>'}</div></body></html>'''


def save(tmp_path, value):
    path = tmp_path / 'report.html'
    path.write_text(value, encoding='utf-8')
    return path


def test_complete_saved_report_and_displayed_date(tmp_path):
    article = read_saved_article(save(tmp_path, html()), expected_url=URL)
    assert article.url == URL
    assert article.date_published == date(2026, 11, 25)  # Not UTC date from the metadata.
    assert article.author == 'Synthetic reporter'
    assert article.content == CONTENT.strip()
    assert article.html_content is None
    assert not article.incidents_scraped and not article.incidents_verified


def test_hidden_and_executable_content_excluded(tmp_path):
    body = f'<p>{CONTENT}<span hidden>Hidden details</span></p><p style="display:none">Secret</p><script>unsafe()</script>'
    article = read_saved_article(save(tmp_path, html(body)))
    assert 'Hidden' not in article.content and 'Secret' not in article.content and 'unsafe' not in article.content


@pytest.mark.parametrize('change', [
    lambda value: value.replace('Synthetic report</title>', 'Just a moment...</title>'),
    lambda value: value.replace('rel="canonical"', 'rel="other"'),
    lambda value: value.replace(URL, 'https://other.example/2026/11/25/synthetic/'),
    lambda value: value.replace('itemprop="articleBody"', 'itemprop="other"'),
    lambda value: value.replace('itemprop="articleBody"', 'itemprop="articleBody" hidden'),
    lambda value: value.replace('November 25, 2026', 'not a date'),
])
def test_invalid_saved_reports_rejected(tmp_path, change):
    with pytest.raises(ValueError):
        read_saved_article(save(tmp_path, change(html())))


def test_feed_url_mismatch_rejected(tmp_path):
    with pytest.raises(ValueError, match='expected feed'):
        read_saved_article(save(tmp_path, html()), URL.replace('synthetic', 'other'))


@pytest.mark.parametrize('body', ['<p>Short</p>', '<p>' + CONTENT + '[…]</p>', '<p>' + CONTENT + 'Sign in to continue</p>'])
def test_excerpt_and_access_prompt_rejected(tmp_path, body):
    with pytest.raises(ValueError):
        read_saved_article(save(tmp_path, html(body)))


def test_preview_does_not_open_database(tmp_path, monkeypatch):
    database = Mock()
    monkeypatch.setattr('database.get_database_session', database)
    path = save(tmp_path, html())
    main(['--input', str(path), '--confirmed-full-text'])
    database.assert_not_called()


def test_confirmation_and_apply_required(tmp_path):
    path = save(tmp_path, html())
    with pytest.raises(SystemExit):
        main(['--input', str(path)])
    with pytest.raises(SystemExit):
        main(['--input', str(path), '--confirmed-full-text', '--parse'])


@pytest.fixture

def local_cli(setup_database, monkeypatch):
    session = setup_database
    monkeypatch.setattr('database.get_database_session', lambda *args, **kwargs: (session, session.bind))
    monkeypatch.setattr(session, 'close', Mock())
    monkeypatch.setattr(session.bind, 'dispose', Mock())
    return session


def test_apply_and_rerun_do_not_overwrite(tmp_path, local_cli):
    path = save(tmp_path, html())
    args = ['--input', str(path), '--confirmed-full-text', '--apply', '--environment', 'test']
    main(args)
    article = local_cli.query(Article).one()
    article.content = 'Previously reviewed source text'
    article.incidents_verified = True
    local_cli.commit()
    main(args)
    assert local_cli.query(Article).count() == 1
    assert article.content == 'Previously reviewed source text' and article.incidents_verified


def test_production_backup_failure_prevents_insert(tmp_path, local_cli, monkeypatch):
    path = save(tmp_path, html())
    monkeypatch.setattr('police_fire.refresh_data.backup_database', Mock(side_effect=RuntimeError('Backup failed')))
    with pytest.raises(RuntimeError, match='Backup failed'):
        main(['--input', str(path), '--confirmed-full-text', '--apply', '--environment', 'production'])
    assert local_cli.query(Article).count() == 0


def test_parsed_rerun_skips_paid_api(tmp_path, local_cli, monkeypatch):
    article = Article(url=URL, incidents_scraped=True)
    local_cli.add(article)
    local_cli.commit()
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-fixture')
    parse = Mock()
    monkeypatch.setattr('police_fire.refresh_data.parse_article', parse)
    main(['--input', str(save(tmp_path, html())), '--confirmed-full-text', '--apply', '--parse', '--environment', 'test'])
    parse.assert_not_called()

