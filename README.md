# Hockey Calgary Scraper

This project scrapes historical performance data for U9, U11, U13, and U15 teams from [hockeycalgary.ca](https://www.hockeycalgary.ca).

## Features

- Scrapes standings (GP, W, L, T, PTS, GF, GA, Diff) for multiple seasons.
- Stores data in a SQLite database (`hockey_calgary.db`).
- Maps team names to communities (e.g., "Bow Valley 1" -> "Bow Valley").
- Supports custom community mapping via `community_map.json`.
- Exports data to CSV for viewing and editing.

## Setup

1.  **Install Dependencies**:
    The project uses Python. Ensure you have the required packages installed:
    ```bash
    pip install requests beautifulsoup4 pandas sqlalchemy
    ```

2.  **Database**:
    The database is automatically created when you run the scraper.

## Usage

### 1. Sync Data (Scrape)

To download the latest data from the website:

```bash
python scraper.py
```

This will:
- Fetch all leagues for U9, U11, U13, U15.
- Iterate through available seasons.
- Update the database with the latest stats.

### 2. View/Export Data

To export the data to a CSV file (`hockey_calgary_stats.csv`):

```bash
python export_data.py
```

You can then open this CSV file in Excel or any spreadsheet viewer.

### 3. Community Mapping

The scraper attempts to guess the community name from the team name.
To override or fix mappings, edit `community_map.json`.

Format:
```json
{
    "Team Name": "Community Name",
    "GHC Chaos": "Girls Hockey Calgary"
}
```

After editing the map, run `python scraper.py` again to update the community names in the database.

## Project Structure

- `scraper.py`: Main scraping script.
- `models.py`: Database models (SQLAlchemy).
- `database.py`: Database connection setup.
- `utils.py`: Helper functions for community name normalization.
- `export_data.py`: Script to export DB to CSV.
- `community_map.json`: Custom mappings for community names.
- `hockey_calgary.db`: SQLite database file (created after running scraper).
