"""Import one normally readable, manually saved Voice report without website requests."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path

from bs4 import BeautifulSoup

from models.article import Article
from police_fire.cortland_voice.feed_inventory import MAX_BYTES, TRUNCATION, validate_article_url


def hidden(node):
    for element in (node, *node.parents):
        if not getattr(element, 'attrs', None):
            continue
        style = ''.join(element.get('style', '').lower().split())
        if ('hidden' in element.attrs or element.get('aria-hidden', '').lower() == 'true'
                or 'display:none' in style or 'visibility:hidden' in style):
            return True
    return False


def read_saved_article(path, expected_url=None):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Saved HTML exceeds the 20 MiB limit')
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('Saved HTML exceeds the 20 MiB limit')
    soup = BeautifulSoup(raw, 'html.parser')
    title = soup.title.get_text(' ', strip=True).lower() if soup.title else ''
    if 'just a moment' in title or 'attention required' in title:
        raise ValueError('Saved page is a security challenge, not a report')
    canonical = soup.find('link', rel='canonical', href=True)
    if canonical is None:
        raise ValueError('Saved report canonical URL missing')
    url = validate_article_url(canonical['href'])
    if expected_url is not None and url != validate_article_url(expected_url):
        raise ValueError('Saved report does not match the expected feed article URL')
    headline, displayed_date = soup.find('h1'), soup.select_one('.post-date')
    body = soup.select_one('[itemprop="articleBody"]')
    if (headline is None or displayed_date is None or body is None
            or hidden(headline) or hidden(displayed_date) or hidden(body)):
        raise ValueError('Normally readable headline, publication date and body required')
    published = datetime.strptime(displayed_date.get_text(' ', strip=True), '%B %d, %Y').date()
    if not headline.get_text(' ', strip=True):
        raise ValueError('Saved report headline missing')
    for node in body.select('script, style, iframe, noscript'):
        node.decompose()
    for node in list(body.find_all(True)):
        if node.parent is not None and hidden(node):
            node.decompose()
    paragraphs = [node.get_text(' ', strip=True) for node in body.select('p') if not hidden(node)]
    content = '\n\n'.join(text for text in paragraphs if text)
    if len(content) < 100 or TRUNCATION.search(content):
        raise ValueError('Saved report is too short or truncated; full reporting required')
    if any(prompt in content.lower() for prompt in ('sign in to continue', 'subscribe to continue', 'subscription required')):
        raise ValueError('Saved report contains an access prompt')
    author = soup.find('meta', attrs={'name': 'author'})
    return Article(url=url, headline=headline.get_text(' ', strip=True),
                   date_published=published, content=content, section='Police/Fire',
                   author=author.get('content', '') if author else '',
                   html_content=None, incidents_scraped=False, incidents_verified=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--expected-url', help='Canonical URL from the saved feed inventory')
    parser.add_argument('--confirmed-full-text', action='store_true', help='Confirm the entire report was normally readable when saved')
    parser.add_argument('--environment', choices=['development', 'test', 'production'], default='development')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--parse', action='store_true', help='Parse after importing; requires --apply and local API key')
    args = parser.parse_args(argv)
    if not args.confirmed_full_text:
        parser.error('Confirm the entire article was normally readable; summaries are not eligible')
    if args.parse and not args.apply:
        parser.error('--parse requires --apply; preview never calls paid APIs')
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('Environment file does not exist')
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=True)
    if args.parse and not os.getenv('OPENAI_API_KEY'):
        parser.error('Set OPENAI_API_KEY locally before parsing')
    article = read_saved_article(args.input, args.expected_url)
    print(json.dumps({'url': article.url, 'date_published': article.date_published.isoformat(),
                      'content_chars': len(article.content), 'action': 'apply' if args.apply else 'preview'}))
    if not args.apply:
        return
    from database import get_database_session
    from police_fire.refresh_data import backup_database, parse_article
    session, engine = get_database_session(args.environment, create_tables=False)
    try:
        existing = session.query(Article).filter_by(url=article.url).first()
        if existing and (existing.incidents_scraped or not args.parse):
            print(json.dumps({'article_id': existing.id, 'action': 'skip-existing'}))
            return
        if args.environment == 'production':
            print('Backup:', backup_database(engine))
        if existing is None:
            session.add(article)
            session.commit()
        else:
            article = existing  # Never overwrite existing content or verified data.
        count = parse_article(session, article) if args.parse else 0
        print(json.dumps({'article_id': article.id, 'new_incidents': count,
                          'parsed': bool(article.incidents_scraped)}))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == '__main__':
    main()

