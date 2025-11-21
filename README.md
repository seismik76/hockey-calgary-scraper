# Hockey Calgary Scraper

This project scrapes historical performance data for U9, U11, U13, and U15 teams from [hockeycalgary.ca](https://www.hockeycalgary.ca), including support for RAMP (U11) and TeamLinkt (U13+) data sources.

## Features

- **Comprehensive Scraping**: Collects standings (GP, W, L, T, PTS, GF, GA, Diff) across multiple seasons.
- **Historical Data**: Robust handling of legacy seasons and different league types (Regular, Seeding, Playoff).
- **Data Storage**: Stores structured data in a SQLite database (`hockey_calgary.db`).
- **Community Mapping**: Automatically maps team names to communities (e.g., "Bow Valley 1" -> "Bow Valley") with custom overrides via `community_map.json`.
- **Web Dashboard**: Interactive Streamlit dashboard to visualize trends, compare communities, and filter data.
- **Data Export**: Download full or filtered datasets directly to CSV from the dashboard.

## Setup

1.  **Install Dependencies**:
    The project uses Python. Ensure you have the required packages installed:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Database**:
    The database is automatically created and initialized when you run the scraper.

## Usage

### 1. Web Analysis Dashboard (Recommended)

The easiest way to use the tool is via the web dashboard.

```bash
streamlit run app.py
```

This will open a web page in your browser where you can:
- **Run the Scraper**: Click the "Run Scraper" button in the sidebar to sync the latest data.
- **Analyze Trends**: View performance trends over time for different communities.
- **Compare Communities**: See head-to-head comparisons and rankings.
- **Filter Data**: Filter by season, age category (U11, U13, etc.), community, and league type.
- **Export Data**: Download the complete dataset or your filtered view as a CSV file.

### 2. Sync Data (Command Line)

Alternatively, you can run the scraper from the command line:

```bash
python scraper.py
```

This will:
- Fetch all leagues for U9, U11, U13, U15.
- Handle data from Hockey Calgary (Legacy), RAMP, and TeamLinkt.
- Update the database with the latest stats.

### 3. Maintenance & Inspection

The project includes various scripts for debugging and maintenance, organized in the `scripts/` directory.

- **Export Data (CLI)**:
  ```bash
  python scripts/maintenance/export_data.py
  ```
- **Debug Legacy Scraping**:
  ```bash
  python scripts/inspection/debug_legacy.py
  ```
- **Clean/Fix Community Names**:
  ```bash
  python scripts/maintenance/fix_communities.py
  ```

### 4. Community Mapping

The scraper attempts to guess the community name from the team name.
To override or fix mappings, edit `community_map.json`.

Format:
```json
{
    "Team Name": "Community Name",
    "GHC Chaos": "Girls Hockey Calgary"
}
```

After editing the map, run `python scraper.py` (or use the "Run Scraper" button in the app) to update the database.

## Project Structure

- `app.py`: Streamlit web dashboard.
- `scraper.py`: Main scraping script.
- `models.py`: Database models (SQLAlchemy).
- `database.py`: Database connection setup.
- `utilities/`: Shared utility functions (e.g., community name normalization).
- `scripts/`:
  - `inspection/`: Scripts for debugging and inspecting source HTML/API responses.
  - `maintenance/`: Scripts for database cleanup and data fixes.
  - `testing/`: Unit tests and verification scripts.
  - `legacy/`: Older scraping scripts.
- `data/`:
  - `dumps/`: Raw data exports and debug dumps.
- `community_map.json`: Custom mappings for community names.
- `hockey_calgary.db`: SQLite database file.
