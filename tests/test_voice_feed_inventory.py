from pathlib import Path

import pytest

from police_fire.cortland_voice.feed_inventory import main, read_inventory, validate_article_url


URL = 'https://cortlandvoice.com/2026/11/25/synthetic-report/'


def feed(item='', publisher='https://cortlandvoice.com/'):
    return f'''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><link>{publisher}</link>{item}</channel></rss>'''


def item(url=URL, category='Crime &amp; Courts', published='Thu, 26 Nov 2026 02:53:01 +0000', body=''):
    return f'''<item><title>Synthetic report</title><link>{url}</link><pubDate>{published}</pubDate><category>{category}</category><dc:creator>Synthetic author</dc:creator><description><![CDATA[<p>Synthetic excerpt [&#8230;]</p>]]></description>{body}</item>'''


def save(tmp_path, data):
    path = tmp_path / 'feed.xml'
    path.write_text(data, encoding='utf-8')
    return path


def test_excerpt_is_not_complete_content(tmp_path):
    result = read_inventory(save(tmp_path, feed(item())))
    assert result['total_items'] == result['selected_items'] == 1
    assert result['full_content_items'] == 0
    entry = result['entries'][0]
    assert entry['content'] is None and entry['summary_truncated'] is True
    assert entry['published_at'] == '2026-11-26T02:53:01+00:00'
    assert 'date_published' not in entry  # Retain timestamp; conversion to local date belongs to full import.


def test_encoded_content_and_publication_timestamp(tmp_path):
    body = '<content:encoded><![CDATA[<p>Synthetic complete report.</p><script>ignore()</script>]]></content:encoded>'
    result = read_inventory(save(tmp_path, feed(item(published='Wed, 25 Nov 2026 21:53:01 -0500', body=body))))
    assert result['entries'][0]['content'] == 'Synthetic complete report.'
    assert result['entries'][0]['published_at'] == '2026-11-26T02:53:01+00:00'
    assert result['full_content_items'] == 1


def test_truncated_encoded_body_not_accepted(tmp_path):
    body = '<content:encoded><![CDATA[<p>Incomplete [&#8230;]</p>]]></content:encoded>'
    result = read_inventory(save(tmp_path, feed(item(body=body))))
    assert result['entries'][0]['content'] is None


def test_category_selection(tmp_path):
    path = save(tmp_path, feed(item(category='Public Safety')))
    assert read_inventory(path)['selected_items'] == 0
    assert read_inventory(path, categories=['public safety'])['selected_items'] == 1
    with pytest.raises(ValueError, match='category'):
        read_inventory(path, categories=[])


@pytest.mark.parametrize('url', [
    'https://other.example/2026/11/25/synthetic/',
    'http://cortlandvoice.com/2026/11/25/synthetic/',
    'https://user:secret@cortlandvoice.com/2026/11/25/synthetic/',
    'https://cortlandvoice.com:444/2026/11/25/synthetic/',
    URL + '?token=secret', URL + '#fragment', 'https://cortlandvoice.com/feed/',
])
def test_source_url_validation(url):
    with pytest.raises(ValueError):
        validate_article_url(url)


def test_duplicate_feed_urls_rejected(tmp_path):
    with pytest.raises(ValueError, match='Duplicate'):
        read_inventory(save(tmp_path, feed(item() + item())))


@pytest.mark.parametrize('published', ['not a date', 'Wed, 25 Nov 2026 18:30:00'])
def test_invalid_or_timezone_missing_timestamp_rejected(tmp_path, published):
    with pytest.raises(ValueError, match='timestamp'):
        read_inventory(save(tmp_path, feed(item(published=published))))


def test_wrong_channel_rejected(tmp_path):
    with pytest.raises(ValueError, match='publisher'):
        read_inventory(save(tmp_path, feed(item(), publisher='https://other.example/')))


def test_dtd_and_entities_rejected(tmp_path):
    payload = '<!DOCTYPE rss [<!ENTITY unsafe SYSTEM "file:///C:/private.txt">]>' + feed(item())
    with pytest.raises(ValueError, match='DTD'):
        read_inventory(save(tmp_path, payload))


def test_oversized_feed_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr('police_fire.cortland_voice.feed_inventory.MAX_BYTES', 4)
    with pytest.raises(ValueError, match='20 MiB'):
        read_inventory(save(tmp_path, feed()))


def test_malformed_xml_rejected(tmp_path):
    with pytest.raises(ValueError, match='Invalid RSS'):
        read_inventory(save(tmp_path, '<rss>'))


def test_cli_writes_inventory_without_importing_articles(tmp_path):
    source = save(tmp_path, feed(item()))
    output = tmp_path / 'inventory.json'
    main(['--input', str(source), '--output', str(output)])
    assert output.is_file()
    assert '"content": null' in output.read_text(encoding='utf-8')
    with pytest.raises(SystemExit):
        main(['--input', str(source), '--output', str(output)])

