"""Export normally visible Standard articles using a publisher-authorized browser."""
import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup

from police_fire.cortland_standard.import_articles import load_export, validate_standard_url
from police_fire.refresh_data import positive_int


SECTION_URL = 'https://www.cortlandstandard.com/news/police-fire/'


def write_json_checkpoint(path, payload):
    """Flush before replacing; retry only transient local Windows file locks."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(25):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 24:
                raise
            time.sleep(0.2)


def discover_urls(html, news_only=True):
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    for link in soup.select('a[href]'):
        url = urljoin(SECTION_URL, link['href'])
        if '/article_' not in url or (news_only and '/news/' not in url):
            continue
        try:
            validate_standard_url(url)
        except ValueError:
            continue
        if url not in urls:
            urls.append(url)
    return urls


def extract_metadata(html):
    soup = BeautifulSoup(html, 'html.parser')
    headline = soup.find('h1')
    published = soup.find('meta', attrs={'property': 'article:published_time'})
    if published is None:
        published = soup.find('meta', attrs={'itemprop': 'datePublished'})
    if published is None:
        published = soup.find('time', attrs={'itemprop': 'datePublished'})
    if published is None:
        published = soup.find('time', attrs={'datetime': True})
    if headline is None or published is None:
        raise ValueError('Article headline or publication date missing')
    raw_date = published.get('content') or published.get('datetime')
    if not raw_date:
        raise ValueError('Publication date missing')
    published_date = datetime.fromisoformat(raw_date.replace('Z', '+00:00')).date()
    author = soup.find('meta', attrs={'name': 'author'})
    return {'headline': headline.get_text(' ', strip=True),
            'date_published': published_date.isoformat(),
            'author': author.get('content', '') if author else ''}


def archive_url(since, until, search_term=None, section='news/police-fire'):
    if since is not None and since > until:
        raise ValueError('Archive start date must not exceed end date')
    query = {'t': 'article', 's': 'start_time', 'sd': 'desc', 'l': '100', 'd2': until.isoformat()}
    if search_term:
        query['q'] = search_term
    else:
        if section not in ('news/police-fire', 'news'):
            raise ValueError('Unsupported archive section')
        query['c[]'] = section
    if since is not None:
        query['d1'] = since.isoformat()
    return 'https://www.cortlandstandard.com/search/?' + urlencode(query)


def archive_links(html, current_url):
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('.search-page-container .col-md-9')
    if container is None:
        raise ValueError('Archive result container missing')
    urls = discover_urls(str(container), news_only=False)
    next_link = soup.select_one('.pagination li.next:not(.disabled) a[href]')
    next_url = urljoin(current_url, next_link['href']) if next_link else None
    if next_url:
        parts = urlsplit(next_url)
        if (parts.scheme != 'https' or parts.hostname != 'www.cortlandstandard.com'
                or parts.path != '/search/' or parts.username or parts.password
                or parts.port not in (None, 443) or parts.fragment):
            raise ValueError('Invalid archive pagination URL')
        expected, actual = parse_qs(urlsplit(current_url).query), parse_qs(parts.query)
        sections = actual.get('c[]', actual.get('c[0]'))
        expected_sections = expected.get('c[]', expected.get('c[0]'))
        if sections != expected_sections or any(
                actual.get(key) != expected.get(key) for key in ('q', 't', 's', 'sd', 'l', 'd1', 'd2')):
            raise ValueError('Archive pagination changed the requested filters')
    return urls, next_url


def collect_archive_urls(page, since, until, max_pages, search_term=None, section='news/police-fire'):
    current = archive_url(since, until, search_term, section)
    seen_pages, urls = set(), []
    for number in range(1, max_pages + 1):
        if current in seen_pages:
            raise ValueError('Archive pagination loop detected')
        seen_pages.add(current)
        navigate(page, current)
        found, current = archive_links(page.content(), current)
        urls.extend(url for url in found if url not in urls)
        print(json.dumps({'archive_page': number, 'discovered': len(urls)}), flush=True)
        if current is None:
            return urls, True
    return urls, False


def visible_article_text(page):
    body = page.locator('[itemprop="articleBody"]').first
    if not body.count() or not body.is_visible():
        raise ValueError('Article body is not normally accessible; sign in with authorized access')
    paragraphs = [node.inner_text().strip() for node in body.locator('p').all() if node.is_visible()]
    content = '\n\n'.join(text for text in paragraphs if text)
    if len(content) < 100:
        raise ValueError('Article body is too short to confirm readable reporting')
    prompts = ('subscribe to continue', 'subscription required', 'sign in to continue', 'purchase a subscription')
    if any(prompt in content.lower() for prompt in prompts):
        raise ValueError('Subscription prompt found; article is not accessible')
    return content


def wait_for_article_text(page, timeout_ms=90000):
    previous = None
    stable = 0
    for _ in range(max(1, timeout_ms // 1000)):
        gated = page.locator('[itemprop="articleBody"] .subscriber-only').all()
        try:
            if any(not node.is_visible() for node in gated):
                raise ValueError('Subscriber article elements are still hidden')
            content = visible_article_text(page)
        except ValueError:
            previous = None
            stable = 0
        else:
            stable = stable + 1 if content == previous else 0
            previous = content
            if stable >= 3:
                return content
        page.wait_for_timeout(1000)
    raise ValueError('Article did not become normally readable within the loading timeout')


def navigate(page, url):
    response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
    if response is None or response.status != 200:
        status = response.status if response else 'no response'
        raise RuntimeError(f'Browser navigation stopped at HTTP {status}; no retries attempted')
    page.wait_for_timeout(5000)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorized', action='store_true', help='Confirm publisher permission to automate access')
    parser.add_argument('--login', action='store_true', help='Open the profile for normal manual sign-in, then save on Enter')
    parser.add_argument('--profile', type=Path, default=Path('downloads/standard-browser-profile'))
    parser.add_argument('--output', type=Path, default=Path('downloads/standard-export.json'))
    parser.add_argument('--max-articles', type=positive_int, default=5)
    parser.add_argument('--since', type=date.fromisoformat, help='Search the Police/Fire archive from this ISO date')
    parser.add_argument('--archive', action='store_true', help='Search the archive; omit --since to include all earlier years')
    parser.add_argument('--search-term', help='Use normal publisher search instead of section tags (historical migration fallback)')
    parser.add_argument('--archive-section', choices=['news/police-fire', 'news'], default='news/police-fire',
                        help='Broader local news recovers historical articles missing Police/Fire tags')
    parser.add_argument('--until', type=date.fromisoformat, default=date.today())
    parser.add_argument('--max-pages', type=positive_int, default=10)
    parser.add_argument('--skip-file', type=Path, help='Local JSON list of already stored article URLs')
    parser.add_argument('--resume', action='store_true', help='Resume an existing validated export checkpoint')
    parser.add_argument('--channel', choices=['chrome', 'msedge'], default='chrome')
    args = parser.parse_args(argv)
    if not args.authorized:
        parser.error('Publisher authorization is required')
    if not args.login and not args.profile.is_dir():
        parser.error('Use an existing locally authenticated browser profile')
    if not args.login and args.output.exists() and not args.resume:
        parser.error('Output already exists; use a new filename to preserve previous exports')
    if args.resume and not args.output.is_file():
        parser.error('--resume requires an existing export checkpoint')
    if args.since and args.since > args.until:
        parser.error('--since must not exceed --until')
    if args.search_term and not (args.archive or args.since):
        parser.error('--search-term requires --archive or --since')
    archive = args.archive or args.since is not None
    skipped = set()
    if args.skip_file:
        values = json.loads(args.skip_file.read_text(encoding='utf-8'))
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            parser.error('--skip-file must contain a JSON list of URLs')
        for value in values:
            validate_standard_url(value)
        skipped.update(values)
    from playwright.sync_api import sync_playwright
    records = []
    if args.resume:
        records = [{'url': row.url, 'headline': row.headline, 'content': row.content,
                    'date_published': row.date_published.isoformat(), 'author': row.author or ''}
                   for row in load_export(args.output)]
    skipped.update(record['url'] for record in records)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(args.profile.resolve()), channel=args.channel, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            if args.login:
                navigate(page, 'https://www.cortlandstandard.com/users/login/')
                input('Sign in normally in the browser, then press Enter here to save the local profile: ')
                return
            if archive:
                if args.search_term or args.archive_section != 'news/police-fire':
                    urls, exhausted = collect_archive_urls(page, args.since, args.until, args.max_pages,
                                                           args.search_term, args.archive_section)
                else:
                    urls, exhausted = collect_archive_urls(page, args.since, args.until, args.max_pages)
            else:
                navigate(page, SECTION_URL)
                urls, exhausted = discover_urls(page.content()), False
            if not urls and not archive:
                raise ValueError('No current section article URLs found')
            pending = [url for url in urls if url not in skipped]
            manifest = {'since': args.since.isoformat() if args.since else None, 'until': args.until.isoformat(),
                        'search_term': args.search_term, 'urls': urls,
                        'archive_section': args.archive_section if not args.search_term else None,
                        'archive_exhausted': exhausted, 'pending': len(pending)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json_checkpoint(args.output.with_suffix('.manifest.json'), manifest)
            print(json.dumps({'discovered': len(urls), 'pending': len(pending),
                              'archive_exhausted': exhausted}), flush=True)
            if not pending and not args.output.exists():
                write_json_checkpoint(args.output, {'articles': records})
            for url in pending[:args.max_articles]:
                page.wait_for_timeout(5000)
                navigate(page, url)
                validate_standard_url(page.url)
                if page.url != url:
                    raise ValueError('Article URL redirected; manual review required')
                record = extract_metadata(page.content())
                if archive:
                    published = date.fromisoformat(record['date_published'])
                    if published > args.until or (args.since and published < args.since):
                        raise ValueError('Article publication outside requested archive range')
                record.update(url=page.url, content=wait_for_article_text(page))
                records.append(record)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_json_checkpoint(args.output, {'articles': records})
                print(json.dumps({'exported': len(records), 'url': record['url'], 'date_published': record['date_published']}), flush=True)
        finally:
            context.close()
    print('Saved authorized export:', args.output)


if __name__ == '__main__':
    main()

