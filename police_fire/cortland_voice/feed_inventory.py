"""Inventory a locally saved publisher RSS feed; no HTTP, API or database calls."""
import argparse
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from lxml import etree


CONTENT = '{http://purl.org/rss/1.0/modules/content/}encoded'
CREATOR = '{http://purl.org/dc/elements/1.1/}creator'
MAX_BYTES = 20 * 1024 * 1024
TRUNCATION = re.compile(r'\[(?:…|\.{3})\]|\bread more\b', re.IGNORECASE)


def validate_article_url(value):
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.hostname != 'cortlandvoice.com'
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.query or parts.fragment
            or not re.fullmatch(r'/\d{4}/\d{2}/\d{2}/[^/]+/', parts.path)):
        raise ValueError('Expected a canonical HTTPS Cortland Voice article URL')
    return value


def plain_text(html):
    soup = BeautifulSoup(html or '', 'html.parser')
    for node in soup.select('script, style'):
        node.decompose()
    return soup.get_text(' ', strip=True)


def read_inventory(path, categories=('Crime & Courts',)):
    """Return discovery metadata, not Article records eligible for automatic parsing."""
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Feed exceeds the 20 MiB limit')
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('Feed exceeds the 20 MiB limit')
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as error:
        raise ValueError('Invalid RSS XML') from error
    if root.getroottree().docinfo.doctype:
        raise ValueError('Feed DTD declarations are not allowed')
    channel = root.find('channel')
    if root.tag != 'rss' or channel is None:
        raise ValueError('Expected an RSS channel')
    if (channel.findtext('link') or '').strip() != 'https://cortlandvoice.com/':
        raise ValueError('Expected the Cortland Voice publisher channel')
    selected = {category.casefold() for category in categories}
    if not selected:
        raise ValueError('Select at least one feed category')
    entries, seen = [], set()
    items = channel.findall('item')
    for item in items:
        url = validate_article_url((item.findtext('link') or '').strip())
        if url in seen:
            raise ValueError('Duplicate article URLs in feed')
        seen.add(url)
        headline = (item.findtext('title') or '').strip()
        if not headline:
            raise ValueError('Feed article headline missing')
        try:
            published = parsedate_to_datetime((item.findtext('pubDate') or '').strip())
            if published.tzinfo is None:
                raise ValueError('Publication timestamp requires a timezone')
        except (TypeError, ValueError) as error:
            raise ValueError('Invalid feed publication timestamp') from error
        labels = [(node.text or '').strip() for node in item.findall('category')]
        if not selected.intersection(label.casefold() for label in labels):
            continue
        summary = plain_text(item.findtext('description'))
        encoded = plain_text(item.findtext(CONTENT))
        has_full_content = bool(encoded) and not TRUNCATION.search(encoded)
        entries.append({
            'url': url, 'headline': headline,
            'published_at': published.astimezone(timezone.utc).isoformat(),
            'author': (item.findtext(CREATOR) or '').strip(), 'categories': labels,
            'summary': summary, 'summary_truncated': bool(TRUNCATION.search(summary)),
            'has_full_content': bool(has_full_content), 'content': encoded if has_full_content else None,
        })
    return {
        'publisher': 'Cortland Voice', 'source_feed': 'https://cortlandvoice.com/feed/',
        'total_items': len(items), 'selected_items': len(entries), 'entries': entries,
        'full_content_items': sum(entry['has_full_content'] for entry in entries),
        'warning': 'Discovery inventory only. Excerpts are not imported or parsed as complete articles.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Locally saved RSS XML')
    parser.add_argument('--output', type=Path, default=Path('downloads/voice-feed-inventory.json'))
    parser.add_argument('--category', action='append', help='Repeat to select categories; default Crime & Courts')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Output exists; use a new filename to preserve the previous inventory')
    inventory = read_inventory(args.input, args.category or ['Crime & Courts'])
    from police_fire.cortland_standard.browser_export import write_json_checkpoint
    write_json_checkpoint(args.output, inventory)
    print({key: inventory[key] for key in ('total_items', 'selected_items', 'full_content_items', 'warning')})
    print('Saved offline inventory:', args.output)


if __name__ == '__main__':
    main()

