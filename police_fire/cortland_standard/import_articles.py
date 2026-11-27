"""Validate a local publisher-authorized Standard export; never contact the website."""
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

from models.article import Article


STANDARD_HOSTS = {'cortlandstandard.com', 'www.cortlandstandard.com'}


def validate_standard_url(url):
    if not isinstance(url, str):
        raise ValueError('Article URL must be a string')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname not in STANDARD_HOSTS
            or parts.username or parts.password or parts.port not in (None, 443)
            or not parts.path or parts.path == '/' or parts.query or parts.fragment):
        raise ValueError('Expected a canonical HTTPS Cortland Standard article URL')
    return url


def load_export(path):
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('Export exceeds the 20 MiB limit; split it into smaller files')
    payload = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(payload, dict) or not isinstance(payload.get('articles'), list):
        raise ValueError('Expected a JSON object containing an articles list')
    articles = []
    seen = set()
    for row in payload['articles']:
        if not isinstance(row, dict):
            raise ValueError('Each exported article must be an object')
        url = validate_standard_url(row.get('url'))
        if url in seen:
            raise ValueError('Duplicate article URLs in export')
        seen.add(url)
        for key in ('headline', 'content', 'date_published'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f'Article requires a non-empty string: {key}')
        published = date.fromisoformat(row['date_published'])
        author = row.get('author', '')
        html = row.get('html_content')
        if not isinstance(author, str) or (html is not None and not isinstance(html, str)):
            raise ValueError('Author and optional HTML content must be strings')
        articles.append(Article(
            url=url, headline=row['headline'].strip(), content=row['content'].strip(),
            date_published=published, author=author, html_content=html,
            section='Police/Fire', incidents_scraped=False, incidents_verified=False,
        ))
    return articles

