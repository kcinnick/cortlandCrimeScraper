# cortlandCrimeScraper

## Tested maintenance workflow (November 2026)

Use **Python 3.11** for the existing pinned dependencies. The editor's Python
3.14 environment has not been validated. A lightweight environment supports
offline tests and the bounded refresh runner without installing Torch or OCR:

```powershell
py -3.11 -m venv .venv-review
.\.venv-review\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv-review\Scripts\python.exe -m pytest -q
```

Default tests use disposable SQLite sessions and block network connections.
Live website/API tests are explicitly skipped, not counted as passing. Run them
with `--integration` only after configuring credentials and an isolated PostgreSQL
test database; some legacy integration tests still use PostgreSQL-specific inputs.
The old shared fixture no longer touches the development database.

### Credentials

Copy `.env.example` to the ignored `.env.local` file and edit it locally. **Never
paste keys into chat, commit credentials, or pass passwords on command lines.**
The refresh runner loads this file only when `--env-file` is supplied, overriding
stale environment values. Set `OPENAI_MODEL` to a model your account can access
(default: `gpt-4.1-mini`; choose a model your account supports). The legacy Standard
login helper uses `LOGIN_EMAIL` and `LOGIN_PASSWORD`; the current browser exporter
uses normal manual sign-in in a dedicated local profile. Cortland Voice is public
and does not require a login for its news articles.

### Safe data refresh

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --env-file .env.local --environment production --audit-only
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --env-file .env.local --environment development --max-pages 1 --max-articles 5
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --env-file .env.local --environment development --apply --parse-only --max-articles 1
```

The first command only reads counts and latest publication date. The second
previews public-source articles without writes or paid API calls. The third
parses stored articles and writes **unverified incident allegations**, not findings
of guilt. Unknown dates stay null; extraction is validated and committed atomically
per article. Re-runs skip parsed articles. Partial existing extractions stop for
manual review rather than guessing how to merge cases.

Production `--apply` requires a successful `pg_dump` backup first. Install PostgreSQL
client tools and put `pg_dump` on PATH. Backups are stored in ignored
`downloads/backups/`; restrict local access and verify restore procedures before
large runs. Backups are not automatically restored after failure. Each article
is its own transaction, so earlier successful articles remain committed.

This runner supports Cortland Voice and authorized local Cortland Standard exports,
and does not populate individual charge rows or perform destructive normalization.
Voice discovery returned HTTP 403 during the November audit; do not bypass access
restrictions. `--parse-only` works on already stored articles without discovery.

The November 27 normal headed-Chrome check loaded Voice's homepage (HTTP 200),
but the public Crime & Courts section returned Cloudflare's "Just a moment..."
security challenge (HTTP 403). Manual sign-in in the dedicated profile also failed.
This is not an OpenAI key or database-password problem. Issue #114 records the
Cloudflare Ray ID for publisher review. Do not automate challenges, spoof browser
identities, extract another browser's session cookies, or retry blocked routes in
a loop. Ask the publisher for approved access, an API/feed, or a content export.

### Voice discovery from a manually saved public RSS feed

Stored publisher HTML advertises **https://cortlandvoice.com/feed/**. The user
successfully opened this feed in their ordinary browser and supplied a saved XML
file. A later automated homepage check returned HTTP 403 as well; automated
website tests stopped. The manually saved feed provides a supported local discovery
route, not a repair of Cloudflare's automation restriction.

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.cortland_voice.feed_inventory --input 'C:\Path\To\cortlandvoice.xml' --output downloads/voice-feed-inventory.json
```

This command makes **no website requests, database writes, or paid API calls**. It
validates the publisher channel, canonical article URLs, timestamps/timezones,
duplicate URLs and the XML size; DTD/entity declarations are rejected. It selects
`Crime & Courts` by default; repeat `--category` to include other categories such as
`Public Safety`. Output files are not overwritten. Keep feeds/inventories under
ignored `downloads/`, not in Git.

The supplied November feed contains ten items, six in `Crime & Courts`. Those six
are truncated descriptions and none has a `content:encoded` body. The inventory
preserves publication timestamps, marks incomplete summaries and leaves `content`
null. **Do not import excerpts into Article.content or mark them parsed.** Even an
encoded-body availability indicator is not certification of complete/accurate
reporting. Full article exports from normal authorized access or a publisher API
are still required for new incident parsing. This feed covers recent items, not
historical backfill or complete current-source coverage. Issue #114 remains open.

For a complete report normally readable in the working browser, save **HTML only**
and use the saved-article importer. It previews without database access by default:

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.cortland_voice.import_saved_article --input downloads/voice-report.html --confirmed-full-text
```

Use `--expected-url` with the canonical URL from the feed inventory to verify the
saved page is the intended article. The importer requires the article body, headline,
canonical Voice URL and displayed publication date; it rejects challenge pages,
truncation/access prompts, oversized files and inline-hidden reporting. It removes
scripts/embeds and stores only reporting text, not the raw browser page. Manual
full-text confirmation is required; offline HTML parsing cannot certify all CSS
visibility or source accuracy. The displayed publication date is used, not the UTC
calendar day or later modification date.

Add `--environment production --env-file .env.local --apply` to import after a
successful production backup, and `--parse` to extract allegations using the locally
configured API key. Existing URLs are not overwritten; parsed articles are skipped
without paid API calls. Imports and parsing commit separately, leaving an imported
article unparsed if extraction fails. Source attribution and unverified flags are
preserved. This manual-export route does not remove the automated website block.

The November 26 read-only production audit found 1,769 articles, 3,050 incidents,
7,804 charges, latest publication 2024-05-30, and 127 unparsed Voice articles.
No production data was refreshed during that audit.

A later backed-up November 26 run successfully parsed six stored Voice articles,
adding five **unverified** incidents (IDs 4003–4007). At that point production had 3,055
incidents and 121 unparsed Voice articles. Article and individual charge counts
remain 1,769 and 7,804. This refreshed stored backlog, not current news: the
latest publication was 2024-05-30 and publisher discovery access remained blocked.

### Cortland Standard refresh

The Standard import phase uses `--source standard` and makes **no publisher website
requests**. The initial November 27 audit found 593 stored Standard articles, all marked
parsed, with latest publication 2024-05-30. The legacy login/browse endpoints
returned HTTP 429, login credentials are absent, and robots directives exclude
several AI crawlers. Do not change crawler identities or bypass access restrictions.
Issue #126 tracks the site migration. Publisher authorization was subsequently
confirmed by the user, and normal browser access to the current Police/Fire section
was verified. Do not run the legacy Standard main pipeline against production.

With publisher permission, use the optional browser exporter and installed Chrome
or Edge. No stealth settings, access bypass, hidden text extraction, or automatic
login are used. Keep the browser profile under ignored `downloads/` because it
contains session data. Sign in normally if required, then save the profile:

```powershell
.\.venv-review\Scripts\python.exe -m pip install -r requirements-browser.txt
.\.venv-review\Scripts\python.exe -m police_fire.cortland_standard.browser_export --authorized --login
.\.venv-review\Scripts\python.exe -m police_fire.cortland_standard.browser_export --authorized --max-articles 5 --output downloads/standard-export.json
```

The exporter waits up to 90 seconds for normally visible article text and subscriber
elements to settle. A five-second wait was insufficient; the tested blotter became
readable after nine seconds. HTTP/access failures stop navigation without retries.
Successful articles are checkpointed to the export; output files are not overwritten.

For historical coverage, the browser exporter supports the publisher's normal
Police/Fire archive search and follows its validated next-page links. Archive
discovery excludes unrelated sidebar stories. Set explicit dates and bounds:

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.cortland_standard.browser_export --authorized --since 2024-05-30 --until 2026-11-27 --max-pages 10 --max-articles 1000 --output downloads/standard-full-export.json
```

Use `--skip-file downloads/standard-existing-urls.json` with a local JSON list of
already stored canonical Standard URLs to avoid downloading them again. Add
`--resume` to continue a validated existing export, without refetching its articles.
Checkpoints use a temporary file and atomic replacement. The adjacent
`.manifest.json` records discovered URLs, pending count, dates, and whether archive
pagination was exhausted. Hitting an article/page bound or an access failure is
**not** a complete refresh; reconcile manifest URLs against stored URLs afterwards.
The import runner remains bounded; raise `--max-articles` explicitly to cover the
export, then run source-specific `--apply --parse-only` for remaining stored backlog.

A backed-up full refresh was started November 27: authorized Standard archive
coverage from May 30, 2024 through November 27, 2026, plus all 121 then-unparsed
stored Voice articles. Private runtime progress is recorded in
`downloads/full-refresh-status.json`; browser progress is recorded in
`downloads/standard-full-export-status.log`. These files and the local job script
are ignored, not repository artifacts. The running job validates the production
backup with `pg_restore --list`, imports/parses each article atomically, and records
article-level failures for review. Current Voice website discovery remains blocked
by HTTP 403. Individual charge-row generation, geocoding, destructive normalization,
and manual verification are not part of this refresh. Do not interpret starting
the job or exhausting Standard pagination as complete two-source coverage.

That run later stopped on `net::ERR_NETWORK_IO_SUSPENDED`, preserving earlier
commits: 245 additional Standard articles and 1,256 additional incidents since its
starting audit. Totals at that checkpoint were 2,019 articles, 4,367 incidents and
7,804 individual charge rows. All 121 stored Voice backlog articles were processed;
Standard had seven parsing failures and 240 discovered URLs still missing. Those
figures are a partial refresh, not complete historical coverage (issue #128).

### Backfill 2025 and all earlier available reporting

Use `--archive` without `--since` to leave the publisher search's lower date bound
unset. `--until 2025-12-31` excludes 2026. The broader local-news section can recover
crime reports whose migrated Police/Fire tags are missing; non-crime articles must
not generate accused records. A separate normal search recovers untagged blotters:

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.cortland_standard.browser_export --authorized --archive --archive-section news --until 2025-12-31 --max-pages 1000 --max-articles 1000 --output downloads/standard-history-local-news.json
.\.venv-review\Scripts\python.exe -m police_fire.cortland_standard.browser_export --authorized --archive --search-term '"police blotter"' --until 2025-12-31 --max-pages 1000 --max-articles 1000 --output downloads/standard-history-blotters.json
```

Use a fresh stored-URL `--skip-file` and `--resume` as appropriate. Query and section
filters are preserved across pagination; publication bounds are also checked on
article pages. Empty searches create explicit empty export/manifest checkpoints.
Import and parse after backup using the source-specific refresh runner above.

The November 27 check found 45 local-news articles through 2025 plus four blotters
outside those local-news tags. A general search before 2025 returned only ten test
articles, not genuine reporting. Thus **no lower cutoff does not mean complete
historical availability**: earlier reporting requires the publisher's legacy archive
or an authorized export. The local historical job records private progress in
`downloads/historical-backfill-status.json`, validates its backup with
`pg_restore --list`, and retains extraction failures for review. Do not commit
profiles, exports, job scripts, credentials, or backups from `downloads/`.

Obtain a publisher-authorized JSON export and save it under ignored `downloads/`.
The file must contain an object with an `articles` list. Each article requires:
- `url`: canonical HTTPS Standard article URL, without tracking query/fragment;
- `headline` and `content`: non-empty strings, with authorized full article text;
- `date_published`: an ISO date (`YYYY-MM-DD`);
- optional `author` and `html_content` strings.

Do not commit exports. Files are limited to 20 MiB; split larger exports. All rows
are validated before opening the database or creating a backup. Duplicate URLs
within a file are rejected; already stored URLs are skipped without overwriting.

```powershell
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --source standard --environment production --audit-only
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --source standard --import-file downloads/standard-export.json --max-articles 5
.\.venv-review\Scripts\python.exe -m police_fire.refresh_data --source standard --env-file .env.local --import-file downloads/standard-export.json --environment production --apply --parse --max-articles 5
```

The second command previews without writes or paid API calls. The third backs up
production, imports up to five new articles, then parses up to five unparsed
Standard articles. Incidents use `cortlandStandardSource`, remain unverified,
and retain unknown dates as null. Imports and extraction commit per article;
earlier successful articles remain committed if a later article fails. No fuzzy
cross-source merging or individual charge-row generation is performed. Use
`--source standard --apply --parse-only` to parse already stored Standard backlog
without importing or contacting the publisher.

The successful November 27 Standard batch imported five current articles and added
56 unverified incidents (IDs 4008–4063). Production totals: 1,774 articles, 3,111
incidents, and 7,804 individual charge rows. The latest stored publication is now
2026-11-27; Standard has 598 articles and zero unparsed articles. The Voice backlog
still has 121 unparsed articles. Source links and name mentions were checked, not
manually certified; the new records still need review. This covers a five-article
current batch, not all historical reporting since 2024.

The November 27 date repair filled `incident_date` for all 56 batch incidents
(4008–4063), after a production backup. Weekday references resolve to the latest
matching day on or before publication: "charged Tuesday" in the November 27
article means November 24. Explicit month/day references such as “Nov. 12” use
the latest matching date on or before publication, handling year boundaries.
An explicitly reported occurrence date takes precedence; when only a dated
arrest/charge is reported, that date is used. This does not establish when an
alleged underlying offense occurred. Court dates are not used, ambiguous dates
remain unknown, and existing dates are never overwritten by backfill.

New refresh extraction includes these rules and a deterministic fallback using
each incident's details and legal actions separately. To repair missing dates in
the latest five stored Standard articles without website requests or paid APIs:

```powershell
python -m police_fire.refresh_data --source standard --environment production --env-file .env.local --backfill-dates --max-articles 5
```

This previews only. Add `--apply` to write after a successful production backup;
updates commit per article. Repeating the completed batch repair proposes zero
updates. Article, incident, and charge counts are unchanged, and records remain
unverified.

### Local app preview

```powershell
.\.venv-review\Scripts\python.exe -m flask_app.run --env-file .env.local --environment production --port 5000
```

Visit **http://127.0.0.1:5000**. The launcher forces read-only mode, binds only to
loopback, and disables debug/reloading. Database sessions open lazily and close
after each request; startup does not create tables. Main pages and the five new
incident pages have been checked over HTTP. Raw charges display even before
spellchecking or individual charge-row extraction.

For other startup methods, `DATABASE_ENV` defaults to development and
`APP_READ_ONLY` defaults to `1`. Write requests are blocked unless read-only mode
is explicitly disabled and a configured `FLASK_ADMIN_TOKEN` matches the request's
`X-Admin-Token` header; global CSRF validation also applies. Administrative browser
login/token handling is not implemented, so use the preview for viewing, not editing.
Set a stable `FLASK_SECRET_KEY` for any administrative deployment. Do not expose
the development server publicly. Remaining destructive-script safeguards and
production authentication requirements are tracked in issue #115.

## Overview
`cortlandCrimeScraper` is a Python-based web scraping tool designed to gather and store detailed information about local news stories from the Cortland Standard & Cortland Voice websites. The primary purpose of this tool is to facilitate data collection for analysis and querying of local news incidents.

## Features
- Scrapes local news articles from the Cortland Standard and Cortland Voice websites.
- Extracts and stores article details such as title, author, publish date, and content.
- Populates an `incidents` table with relevant data extracted from articles.
- Further refines data into a `charges` table for detailed analysis.

## Design

### Article Table
- **Purpose**: Serves as the primary data source, capturing all relevant information from each news article.
- **Fields**: Includes title, author, publish date, URL, and content.
- **Role**: Acts as a foundational table from which other, more specific data tables are populated.

### Incident Table
- **Derived From**: Article table data.
- **Function**: Focuses on specific incidents reported in Police/Fire categorized articles, extracting key details for deeper analysis.
- **Relation to Article Table**: Each incident is linked to an article to maintain traceability and context.

### Charges Table
- **Derived From**: Incident table data.
- **Purpose**: Provides a granular view of the charges associated with each incident, supporting detailed legal and statistical analyses.
- **Relation to Incident Table**: Each entry in the charges table corresponds to a specific incident, allowing for a clear understanding of the legal aspects associated with each case.
