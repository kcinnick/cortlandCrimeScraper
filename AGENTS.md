# AGENTS.md - cortlandCrimeScraper

## 🔴 CRITICAL: Branch Workflow

**ALWAYS create a feature branch. NEVER commit directly to master.**

```bash
# ✅ CORRECT: Create feature branch
git checkout -b feat/your-feature
git add .
git commit -m "feat: description"
git push origin feat/your-feature

# ❌ WRONG: Never do this
git checkout master
git add .
git commit -m "quick fix"
git push
```

See `CONTRIBUTING.md` for complete workflow details.

---

## Project Overview

**cortlandCrimeScraper** is a Python web scraping and data extraction pipeline that ingests crime/incident news articles from local sources (Cortland Standard, Cortland Voice) and transforms them into structured incident and charge records stored in PostgreSQL.

**Three-Tier Data Hierarchy:**
```
Article (raw web content) → Incident (parsed incidents) → Charges (detailed legal charges)
```

This hierarchy is fundamental to the project. Each layer builds on the previous one with increasing specificity.

---

## Architecture & Data Flow

### Core Components

**1. Scraping Sources** (`police_fire/cortland_standard/`, `police_fire/cortland_voice/`)
- **Cortland Standard**: Structured HTML with incident data in "Accused/Charges/Details" format
- **Cortland Voice**: Unstructured article text requiring NLP extraction
- Both feed articles into the `Article` table with URL as unique identifier

**2. Extraction Pipeline** (`police_fire/cortland_standard/main.py`)
```python
# Standard orchestration (main.py shows the full flow):
scrape_articles_by_section() → 
  [for_each unscraped Article]:
    scrape_structured_incident_details() +
    scrape_unstructured_incident_details() →
      [Updates Article.incidents_scraped = True] →
  spellcheck_charges() → 
  scrape_charges_from_incidents() → 
  categorize_charges()
```

**3. Data Models** (`models/`)
- `Article`: Raw web source (headline, content, html_content, url as unique key)
  - Flags: `incidents_scraped`, `incidents_verified`
  - Sources: `Section` field tracks where article came from
- `Incident`: Parsed incident records (accused_name, charges, details, legal_actions, location)
  - Separate source fields: `cortlandStandardSource`, `cortlandVoiceSource` (one null per incident)
  - Location data: `incident_location` + lat/lng (from maps module)
  - Dates: `incident_reported_date`, `incident_date` (nullable, may be inferred from details)
- `Charges`: Foreign key relationship to Incident
  - Fields: `charge_description`, `charge_class` (felony/misdemeanor/violation/traffic_infraction), `degree`, `counts`
  - `category` field populated by `categorize_charges()` for analysis

**4. Database** (`database.py`)
- PostgreSQL with environment-specific databases (dev, test, production)
- Environment sourced from `DATABASE_USERNAME`, `DATABASE_PASSWORD` env vars
- All tables in `public` schema
- Alembic for migrations (`alembic/versions/`)
- Note: `base.py` module is imported but missing/empty - models define their own SQLAlchemy mappings

---

## Critical Developer Workflows

### Running the Full Pipeline
```python
# From police_fire/cortland_standard/main.py
python -m police_fire.cortland_standard.main
# Scrapes articles, extracts incidents (both structured/unstructured), 
# spellchecks charges, categorizes them
```

### Manual Verification/Re-scraping
```python
# From flask_app/app.py routes
# GET /verify_articles - page to verify newly scraped articles
# POST /rescrape/<article_id> - triggers rescrape for specific article
# Uses rescrape_article() from police_fire.cortland_voice.scrape_incidents_from_articles
```

### Database Management
```python
# Initialize/migrate database
python alembic/env.py  # Uses alembic init scripts

# Clean data (remove non-ASCII characters, etc.)
from database import clean_strings_in_table
clean_strings_in_table(environment='development')

# Run tests
pytest tests/
```

### Data Normalization Workflows
Located in `police_fire/data_normalization/` - run individually:
- `categorize_charges.py` - assigns charge categories
- `fix_charge_descriptions_with_misspellings.py` - spell-checks charges using diff matching
- `normalize_incident_locations.py` - standardizes location names
- `check_similar_names.py` - finds potential duplicates/common variations

---

## Key Patterns & Conventions

### 1. Environment Configuration
```python
# All database functions accept environment parameter
db_session, engine = get_database_session(environment='development')
# Options: 'test', 'development'/'dev', 'production' (default)
```

### 2. OpenAI LLM Integration
```python
# From utilities/utilities.py
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Used for:
# - Extracting structured incident data from unstructured text
# - Resolving date references (relative dates like "yesterday")
# - Categorizing charges
```

### 3. Structured vs Unstructured Parsing
- **Structured** (`scrape_structured_police_fire_details.py`): HTML articles with predictable HTML structure
  - Pattern: `<strong>Accused</strong>: Name<br><strong>Charges</strong>: ...`
  - Uses regex + HTML parsing
- **Unstructured** (`scrape_unstructured_police_fire_details.py`): Free-form text
  - Uses OpenAI API to extract incident details as JSON
  - Handles diverse writing styles and formats

### 4. Error Tracking
- Failed incident extractions add entry to `IncidentsWithErrors` table
- Tracks `article_id` and URL for manual review
- Useful for debugging edge cases in scraping logic

### 5. Source Attribution
```python
incident.cortlandStandardSource = article.url  # OR
incident.cortlandVoiceSource = article.url     # Only one is set per incident
```
This is critical for traceability and deduplication across sources.

### 6. Date Handling
- `Article.date_published`: Always populated (from website)
- `Incident.incident_reported_date`: Always populated (publication date of article)
- `Incident.incident_date`: Nullable, extracted from article content (when the incident actually occurred)
- Complex logic in utilities: handles "3 days ago", "January 15", partial dates, etc.

### 7. CSV-Based Reference Data
```python
# Located in police_fire/classification/manually_classified_records.csv
# Used for:
# - Training charge categorization
# - Manual incident verification
# - Pattern reference for normalization
```

---

## Integration Points & Dependencies

### External Dependencies
- **PostgreSQL**: Database backend (localhost:5432 default)
- **OpenAI API**: LLM extraction and categorization
- **BeautifulSoup4**: HTML parsing from websites
- **SQLAlchemy**: ORM and database abstraction
- **Alembic**: Schema migrations
- **requests**: HTTP client for web scraping
- **regex**: Advanced regex (named groups, recursion)
- **tqdm**: Progress bars

### Cross-Component Communication
1. **Database** → All components read/write via SQLAlchemy session
2. **Flask Web App** → Uses same models/database for verification UI
3. **PDF Downloads** (`download_pdfs.py`) → Separate workflow for e-edition content
4. **Maps Module** (`police_fire/maps/`) → Called from scrape_structured to geocode locations
5. **Analysis Module** (`police_fire/analysis/`) → Generates reports from final data

### No Direct File Dependencies
- Project uses database as single source of truth
- No config files needed (environment variables only)
- CSV files are reference data only (not integration points)

---

## Common Modification Patterns

### Adding a New Data Source
1. Create scraper in `police_fire/{source_name}/scrape_articles.py`
2. Follow `scrape_article()` → `Article` model pattern
3. Add corresponding incident scraper
4. Update `main.py` to include in pipeline
5. Run migrations if adding Article fields

### Fixing Charge Categorization
- Edit `police_fire/classification/manually_classified_records.csv` with examples
- Run `police_fire/data_normalization/categorize_charges.py` to regenerate categories

### Handling Parsing Edge Cases
1. Check `IncidentsWithErrors` for articles that failed
2. Add test case to `police_fire/cortland_standard/tests/`
3. Modify unstructured/structured parsing logic
4. Run `python -m pytest tests/` to validate
5. Consider if needs OpenAI prompt engineering vs regex fix

---

## Testing & Debugging

### Key Test Locations
- `tests/` - main test suite
- `police_fire/cortland_standard/tests/` - parsing logic tests
- `police_fire/data_normalization/tests/` - normalization tests

### Debugging Common Issues
**Import Error on `from base import Base`**: Expected - base.py is missing but models work because they import `declarative_base` independently. Alembic `env.py` tries to import it but `Base.metadata` still resolves correctly.

**Duplicate Incidents**: Check `incident.cortlandStandardSource` vs `cortlandVoiceSource` - same incident from different sources should share incident_id if already in database.

**Date Parsing Failures**: Check `Incident.incident_date` null vs populated; look at `IncidentsWithErrors` for list of articles where date extraction failed.

---

## Project-Specific Code Style

- **Naming**: snake_case variables and functions, PascalCase classes
- **Database Queries**: Use SQLAlchemy ORM (filter, query) not raw SQL
- **Progress Feedback**: Use `tqdm` for loops that interact with database
- **Commits**: After DB writes, explicitly call `database_session.commit()`
- **File Paths**: Use environment setup not hardcoded paths
- **Logging**: Currently uses print() statements; consider adding structured logging

