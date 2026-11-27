from unittest.mock import Mock

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


