from unittest.mock import Mock
from datetime import date
from html import escape
import json
import sys
from types import SimpleNamespace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from police_fire.cortland_standard.browser_export import discover_urls, extract_metadata, visible_article_text, navigate
from police_fire.cortland_standard import browser_export


def test_discovery_deduplicates_and_limits_source():
    html = '<a href="/news/example/article_abc.html">Fixture</a><a href="/news/example/article_abc.html">Again</a><a href="https://other.example/news/article_xyz.html">Other</a><a href="/opinion/article_abc.html">Opinion</a>'
    assert discover_urls(html) == ['https://www.cortlandstandard.com/news/example/article_abc.html']


def test_metadata_publication_not_updated_date():
    html = '<h1>Fixture headline</h1><meta property="article:published_time" content="2026-11-25T13:51:00-05:00"><time datetime="2026-11-27T13:00:00-05:00"></time>'
    assert extract_metadata(html)['date_published'] == '2026-11-25'


def test_metadata_time_fallback():
    assert extract_metadata('<h1>Fixture</h1><time datetime="2026-11-25T13:51:00-05:00"></time>')['date_published'] == '2026-11-25'


def test_metadata_missing_date_rejected():
    with pytest.raises(ValueError):
        extract_metadata('<h1>Fixture</h1>')


def test_hidden_article_body_rejected():
    page = Mock()
    page.locator.return_value.first.count.return_value = 1
    page.locator.return_value.first.is_visible.return_value = False
    with pytest.raises(ValueError, match='not normally accessible'):
        visible_article_text(page)
    page.locator.return_value.first.inner_text.assert_not_called()


def test_only_visible_paragraphs_exported():
    page = Mock()
    body = page.locator.return_value.first
    body.count.return_value = 1
    body.is_visible.return_value = True
    visible, hidden = Mock(), Mock()
    visible.is_visible.return_value = True
    visible.inner_text.return_value = 'Synthetic visible reporting. ' * 6
    hidden.is_visible.return_value = False
    body.locator.return_value.all.return_value = [visible, hidden]
    assert 'Synthetic visible reporting' in visible_article_text(page)
    hidden.inner_text.assert_not_called()


def test_subscription_prompt_rejected():
    page = Mock()
    body = page.locator.return_value.first
    body.count.return_value = 1
    body.is_visible.return_value = True
    node = Mock()
    node.is_visible.return_value = True
    node.inner_text.return_value = 'Subscribe to continue. ' * 10
    body.locator.return_value.all.return_value = [node]
    with pytest.raises(ValueError, match='Subscription prompt'):
        visible_article_text(page)


def test_rate_limit_stops_without_retry():
    page = Mock()
    page.goto.return_value.status = 429
    with pytest.raises(RuntimeError, match='HTTP 429'):
        navigate(page, 'https://www.cortlandstandard.com/')
    page.goto.assert_called_once()
    page.wait_for_timeout.assert_not_called()


def test_waits_for_delayed_article_text(monkeypatch):
    page = Mock()
    page.locator.return_value.all.return_value = []
    content = 'Synthetic readable reporting. ' * 10
    extract = Mock(side_effect=[ValueError('loading'), content, content, content, content])
    monkeypatch.setattr(browser_export, 'visible_article_text', extract)
    assert browser_export.wait_for_article_text(page, timeout_ms=6000) == content
    page.goto.assert_not_called()


def test_waits_until_subscriber_elements_visible(monkeypatch):
    page = Mock()
    node = Mock()
    node.is_visible.side_effect = [False, True, True, True, True]
    page.locator.return_value.all.return_value = [node]
    extract = Mock(return_value='Synthetic readable reporting. ' * 10)
    monkeypatch.setattr(browser_export, 'visible_article_text', extract)
    assert browser_export.wait_for_article_text(page, timeout_ms=6000) == extract.return_value
    assert extract.call_count == 4
    page.goto.assert_not_called()


def test_loading_timeout_is_bounded(monkeypatch):
    page = Mock()
    page.locator.return_value.all.return_value = []
    monkeypatch.setattr(browser_export, 'visible_article_text', Mock(side_effect=ValueError('loading')))
    with pytest.raises(ValueError, match='loading timeout'):
        browser_export.wait_for_article_text(page, timeout_ms=2000)
    assert page.wait_for_timeout.call_count == 2
    page.goto.assert_not_called()


def archive_html(next_url=None):
    result = '<div class="search-page-container"><div class="col-md-9"><a href="/news/blotter/article_abc.html">Blotter</a></div></div>'
    result += '<a href="/news/sidebar/article_other.html">Unrelated sidebar</a>'
    if next_url:
        result += '<ul class="pagination"><li class="next"><a href="' + escape(next_url) + '">Next</a></li></ul>'
    return result


def test_archive_scope_and_next_filters():
    url = browser_export.archive_url(date(2024, 5, 30), date(2026, 11, 27))
    next_url = url + '&o=100'
    urls, following = browser_export.archive_links(archive_html(next_url), url)
    assert urls == ['https://www.cortlandstandard.com/news/blotter/article_abc.html']
    assert following == next_url


def test_archive_includes_migrated_paths():
    html = archive_html().replace('/news/blotter/article_abc.html', '/police-blotter/article_abc.html')
    urls, following = browser_export.archive_links(html, 'https://www.cortlandstandard.com/search/')
    assert urls == ['https://www.cortlandstandard.com/police-blotter/article_abc.html']
    assert following is None


@pytest.mark.parametrize('next_url', [
    'https://other.example/search/',
    'http://www.cortlandstandard.com/search/',
    'https://www.cortlandstandard.com/users/login/',
    'https://www.cortlandstandard.com/search/?c[]=news',
])
def test_invalid_archive_pagination_rejected(next_url):
    with pytest.raises(ValueError):
        browser_export.archive_links(archive_html(next_url), browser_export.archive_url(date(2024, 5, 30), date(2026, 11, 27)))


def test_archive_dates_invalid():
    with pytest.raises(ValueError):
        browser_export.archive_url(date(2026, 11, 27), date(2024, 5, 30))


def test_archive_result_container_required():
    with pytest.raises(ValueError, match='container missing'):
        browser_export.archive_links('<html>Login</html>', 'https://www.cortlandstandard.com/search/')


def test_archive_bounded_and_exhausted(monkeypatch):
    since, until = date(2024, 5, 30), date(2026, 11, 27)
    url = browser_export.archive_url(since, until)
    page = Mock()
    navigation = Mock()
    monkeypatch.setattr(browser_export, 'navigate', navigation)
    page.content.return_value = archive_html(url + '&o=100')
    urls, exhausted = browser_export.collect_archive_urls(page, since, until, 1)
    assert len(urls) == 1 and exhausted is False
    assert navigation.call_count == 1
    page.content.side_effect = [archive_html(url + '&o=100'), archive_html()]
    urls, exhausted = browser_export.collect_archive_urls(page, since, until, 5)
    assert len(urls) == 1 and exhausted is True


def test_archive_pagination_loop_rejected(monkeypatch):
    since, until = date(2024, 5, 30), date(2026, 11, 27)
    url = browser_export.archive_url(since, until)
    page = Mock()
    page.content.return_value = archive_html(url)
    monkeypatch.setattr(browser_export, 'navigate', Mock())
    with pytest.raises(ValueError, match='loop'):
        browser_export.collect_archive_urls(page, since, until, 5)


@pytest.fixture
def exporter_browser(monkeypatch):
    page, context, playwright = Mock(), Mock(), Mock()
    context.pages = [page]
    playwright.chromium.launch_persistent_context.return_value = context
    manager = Mock()
    manager.__enter__ = Mock(return_value=playwright)
    manager.__exit__ = Mock(return_value=False)
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', SimpleNamespace(sync_playwright=lambda: manager))
    monkeypatch.setattr(browser_export, 'navigate', Mock())
    monkeypatch.setattr(browser_export, 'extract_metadata', Mock(return_value={
        'headline': 'Synthetic article', 'date_published': '2026-11-25', 'author': '',
    }))
    monkeypatch.setattr(browser_export, 'wait_for_article_text', Mock(return_value='Synthetic reporting. ' * 20))
    return page, context


def test_export_skips_stored_urls_and_checkpoints(tmp_path, monkeypatch, exporter_browser):
    page, context = exporter_browser
    profile = tmp_path / 'profile'
    profile.mkdir()
    output, skip = tmp_path / 'export.json', tmp_path / 'skip.json'
    known = 'https://www.cortlandstandard.com/news/example/article_known.html'
    pending = 'https://www.cortlandstandard.com/news/example/article_new.html'
    skip.write_text(json.dumps([known]), encoding='utf-8')
    page.url = pending
    monkeypatch.setattr(browser_export, 'collect_archive_urls', Mock(return_value=([known, pending], True)))
    browser_export.main(['--authorized', '--since', '2024-05-30', '--until', '2026-11-27',
                         '--profile', str(profile), '--output', str(output), '--skip-file', str(skip)])
    assert [row['url'] for row in json.loads(output.read_text())['articles']] == [pending]
    assert json.loads(output.with_suffix('.manifest.json').read_text())['archive_exhausted'] is True
    browser_export.navigate.assert_called_once_with(page, pending)
    context.close.assert_called_once()


def test_resume_does_not_refetch_checkpointed_articles(tmp_path, monkeypatch, exporter_browser):
    page, context = exporter_browser
    profile = tmp_path / 'profile'
    profile.mkdir()
    output = tmp_path / 'export.json'
    known = 'https://www.cortlandstandard.com/news/example/article_known.html'
    output.write_text(json.dumps({'articles': [{'url': known, 'headline': 'Synthetic',
        'content': 'Synthetic reporting', 'date_published': '2026-11-25'}]}), encoding='utf-8')
    monkeypatch.setattr(browser_export, 'collect_archive_urls', Mock(return_value=([known], True)))
    browser_export.main(['--authorized', '--resume', '--since', '2024-05-30', '--until', '2026-11-27',
                         '--profile', str(profile), '--output', str(output)])
    browser_export.navigate.assert_not_called()
    assert len(json.loads(output.read_text())['articles']) == 1
    context.close.assert_called_once()


def test_export_failure_closes_browser_and_keeps_checkpoint(tmp_path, monkeypatch, exporter_browser):
    page, context = exporter_browser
    profile = tmp_path / 'profile'
    profile.mkdir()
    output = tmp_path / 'export.json'
    first = 'https://www.cortlandstandard.com/news/example/article_first.html'
    second = 'https://www.cortlandstandard.com/news/example/article_second.html'
    monkeypatch.setattr(browser_export, 'collect_archive_urls', Mock(return_value=([first, second], True)))
    def navigation(page, url):
        if url == second:
            raise RuntimeError('HTTP 429')
        page.url = url
    monkeypatch.setattr(browser_export, 'navigate', navigation)
    with pytest.raises(RuntimeError, match='429'):
        browser_export.main(['--authorized', '--since', '2024-05-30', '--until', '2026-11-27',
                             '--profile', str(profile), '--output', str(output)])
    assert [row['url'] for row in json.loads(output.read_text())['articles']] == [first]
    context.close.assert_called_once()


def test_checkpoint_retries_temporary_windows_lock(tmp_path, monkeypatch):
    output = tmp_path / 'checkpoint.json'
    replace = Path.replace
    attempts = []
    def temporarily_locked(path, target):
        attempts.append(target)
        if len(attempts) < 3:
            raise PermissionError('Temporary reader lock')
        return replace(path, target)
    monkeypatch.setattr(Path, 'replace', temporarily_locked)
    sleep = Mock()
    monkeypatch.setattr(browser_export.time, 'sleep', sleep)
    browser_export.write_json_checkpoint(output, {'articles': []})
    assert json.loads(output.read_text()) == {'articles': []}
    assert len(attempts) == 3 and sleep.call_count == 2


def test_checkpoint_permanent_lock_preserves_previous(tmp_path, monkeypatch):
    output = tmp_path / 'checkpoint.json'
    output.write_text('{"previous": true}', encoding='utf-8')
    replace = Mock(side_effect=PermissionError('Locked'))
    monkeypatch.setattr(Path, 'replace', replace)
    monkeypatch.setattr(browser_export.time, 'sleep', Mock())
    with pytest.raises(PermissionError):
        browser_export.write_json_checkpoint(output, {'new': True})
    assert json.loads(output.read_text()) == {'previous': True}
    assert replace.call_count == 25


def test_archive_no_lower_date_bound():
    query = parse_qs(urlsplit(browser_export.archive_url(None, date(2025, 12, 31))).query)
    assert 'd1' not in query
    assert query['d2'] == ['2025-12-31']
    assert query['c[]'] == ['news/police-fire']


def test_archive_search_fallback_preserved():
    url = browser_export.archive_url(None, date(2025, 12, 31), '"police blotter"')
    query = parse_qs(urlsplit(url).query)
    assert 'c[]' not in query and 'd1' not in query
    assert query['q'] == ['"police blotter"']
    assert browser_export.archive_links(archive_html(url + '&o=100'), url)[1] == url + '&o=100'
    with pytest.raises(ValueError, match='filters'):
        browser_export.archive_links(archive_html(url.replace('blotter', 'other') + '&o=100'), url)


def test_archive_empty_results_checkpointed(tmp_path, monkeypatch, exporter_browser):
    page, context = exporter_browser
    profile = tmp_path / 'profile'
    profile.mkdir()
    output = tmp_path / 'export.json'
    collect = Mock(return_value=([], True))
    monkeypatch.setattr(browser_export, 'collect_archive_urls', collect)
    browser_export.main(['--authorized', '--archive', '--until', '2025-12-31',
                         '--profile', str(profile), '--output', str(output)])
    collect.assert_called_once_with(page, None, date(2025, 12, 31), 10)
    assert json.loads(output.read_text()) == {'articles': []}
    manifest = json.loads(output.with_suffix('.manifest.json').read_text())
    assert manifest['since'] is None and manifest['archive_exhausted'] is True
    browser_export.navigate.assert_not_called()


def test_archive_upper_bound_enforced_without_since(tmp_path, monkeypatch, exporter_browser):
    page, context = exporter_browser
    profile = tmp_path / 'profile'
    profile.mkdir()
    pending = 'https://www.cortlandstandard.com/news/example/article_new.html'
    page.url = pending
    monkeypatch.setattr(browser_export, 'collect_archive_urls', Mock(return_value=([pending], True)))
    with pytest.raises(ValueError, match='outside requested'):
        browser_export.main(['--authorized', '--archive', '--until', '2025-12-31',
                             '--profile', str(profile), '--output', str(tmp_path / 'export.json')])
    browser_export.wait_for_article_text.assert_not_called()
    context.close.assert_called_once()


def test_search_term_requires_archive():
    with pytest.raises(SystemExit):
        browser_export.main(['--authorized', '--search-term', 'blotter'])


def test_broader_local_news_archive_filters():
    url = browser_export.archive_url(None, date(2025, 12, 31), section='news')
    assert parse_qs(urlsplit(url).query)['c[]'] == ['news']
    assert browser_export.archive_links(archive_html(url + '&o=100'), url)[1] == url + '&o=100'
    with pytest.raises(ValueError, match='filters'):
        browser_export.archive_links(archive_html(url.replace('=news', '=news%2Fpolice-fire')), url)
    with pytest.raises(ValueError, match='Unsupported'):
        browser_export.archive_url(None, date(2025, 12, 31), section='unrelated')


