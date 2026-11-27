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
(default: `gpt-4.1-mini`; choose a model your account supports). Cortland Standard
also requires legitimate `LOGIN_EMAIL` and `LOGIN_PASSWORD` credentials.

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

This runner currently supports Cortland Voice, not authenticated Standard ingestion,
and does not populate individual charge rows or perform destructive normalization.
Voice discovery returned HTTP 403 during the November audit; do not bypass access
restrictions. `--parse-only` works on already stored articles without discovery.

The November 26 read-only production audit found 1,769 articles, 3,050 incidents,
7,804 charges, latest publication 2024-05-30, and 127 unparsed Voice articles.
No production data was refreshed during that audit.

A later backed-up November 26 run successfully parsed six stored Voice articles,
adding five **unverified** incidents (IDs 4003–4007). Production now has 3,055
incidents and 121 unparsed Voice articles. Article and individual charge counts
remain 1,769 and 7,804. This refreshed stored backlog, not current news: the
latest publication is still 2024-05-30 and publisher discovery access remains blocked.

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
