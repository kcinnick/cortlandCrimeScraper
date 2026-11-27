"""Export normally visible Standard articles using a publisher-authorized browser."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from police_fire.cortland_standard.import_articles import validate_standard_url
from police_fire.refresh_data import positive_int


SECTION_URL = 'https://www.cortlandstandard.com/news/police-fire/'


def discover_urls(html):
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    for link in soup.select('a[href]'):
        url = urljoin(SECTION_URL, link['href'])
        if '/news/' not in url or '/article_' not in url:
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
    parser.add_argument('--channel', choices=['chrome', 'msedge'], default='chrome')
    args = parser.parse_args(argv)
    if not args.authorized:
        parser.error('Publisher authorization is required')
    if not args.login and not args.profile.is_dir():
        parser.error('Use an existing locally authenticated browser profile')
    if not args.login and args.output.exists():
        parser.error('Output already exists; use a new filename to preserve previous exports')
    from playwright.sync_api import sync_playwright
    records = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(args.profile.resolve()), channel=args.channel, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            if args.login:
                navigate(page, 'https://www.cortlandstandard.com/users/login/')
                input('Sign in normally in the browser, then press Enter here to save the local profile: ')
                return
            navigate(page, SECTION_URL)
            urls = discover_urls(page.content())
            if not urls:
                raise ValueError('No current section article URLs found')
            for url in urls[:args.max_articles]:
                page.wait_for_timeout(5000)
                navigate(page, url)
                validate_standard_url(page.url)
                record = extract_metadata(page.content())
                record.update(url=page.url, content=wait_for_article_text(page))
                records.append(record)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps({'articles': records}, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'exported': len(records), 'url': record['url'], 'date_published': record['date_published']}))
        finally:
            context.close()
    print('Saved authorized export:', args.output)


if __name__ == '__main__':
    main()

