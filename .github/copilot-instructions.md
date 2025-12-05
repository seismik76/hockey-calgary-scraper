# Hockey Calgary Scraper & Analytics - AI Instructions

## 🏗 Project Architecture
This project is a data analytics platform for minor hockey in Calgary, consisting of three main components:
1.  **Scraper (`scraper.py`)**: Fetches data from multiple backends (Hockey Calgary Legacy, RAMP Interactive, TeamLinkt).
2.  **Database (`models.py`, `database.py`)**: SQLite database using SQLAlchemy ORM to store seasons, leagues, teams, and standings.
3.  **Dashboard (`app.py`)**: Streamlit web application for visualizing trends, specifically "Dilution Analysis" and community performance.

### Key Data Flow
1.  `scraper.py` fetches HTML/JSON from league sites.
2.  Data is parsed and normalized (especially team names -> communities).
3.  Data is stored in `hockey_calgary.db`.
4.  `app.py` queries the DB to generate visualizations.

## 🛠 Critical Workflows

### Running the Application
- **Dashboard**: `streamlit run app.py` (Access at http://localhost:8501)
- **Full Scrape**: `python scraper.py` (Syncs all configured seasons/leagues)

### Debugging & Inspection
The `scripts/` directory is the primary toolset for debugging. **Do not modify core logic without verifying with these scripts.**
- **Inspect Specific Scrapers**: Use `scripts/inspection/` to test parsers against specific URLs or local dumps.
  - Example: `python scripts/inspection/inspect_ramp_links.py`
- **Database Inspection**: Use `scripts/inspection/inspect_db_u11.py` to verify data integrity after scraping.

## 🧩 Project Patterns & Conventions

### 1. Community Mapping (CRITICAL)
- **Concept**: Team names (e.g., "Bow Valley 1") must be mapped to a canonical `Community` (e.g., "Bow Valley").
- **Mechanism**: 
  - `community_map.json` defines explicit overrides.
  - `utilities.utils.normalize_community_name` handles fuzzy matching.
- **Rule**: When processing team names, ALWAYS apply normalization logic. Never store raw team names as the primary grouping key.

### 2. Scraping Strategy
- **Backends**: The scraper handles different HTML structures:
  - **Legacy**: Standard Hockey Calgary pages.
  - **RAMP**: Used for U11 (Alberta One).
  - **TeamLinkt**: Newer backend for some divisions.
- **Concurrency**: `scraper.py` uses `concurrent.futures`. Ensure database writes are thread-safe or use the global `db_lock`.
- **Network**: `verify=False` is often required for requests due to certificate issues on some league sites.

### 3. Tiering Logic
- **Domain Knowledge**: Tiering follows "Alberta One" standards.
- **Logic**: See `utilities/tiering_logic.py` for grid calculations (e.g., how many teams in Tier 1 vs Tier 2 based on association size).
- **Streams**: Distinguish between "BC" (Body Checking) and "NBC" (Non-Body Checking) for U15/U18.

### 4. Database Access
- Use `database.SessionLocal()` for DB interactions.
- **Schema**: 
  - `League` has `slug`, `stream`, and `type` (Regular, Seeding, Playoff).
  - `Standing` links `Team`, `League`, and `Season`.

## ⚠️ Common Pitfalls
- **Duplicate Teams**: "Bow Valley 1" might exist in "Seeding" and "Regular" leagues. They are treated as the same entity if the name matches, but context matters.
- **Season Formats**: Season names are strings (e.g., "2023-2024"). Ensure consistency when querying.
- **Missing Data**: Some leagues (especially U9) may not have full standings. Handle missing `GF`/`GA` gracefully.
