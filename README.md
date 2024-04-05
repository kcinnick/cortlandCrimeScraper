# cortlandCrimeScraper

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
