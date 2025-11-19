# Hockey Calgary Scraper

This project scrapes historical performance data for U9, U11, U13, and U15 teams from [hockeycalgary.ca](https://www.hockeycalgary.ca).

## Features

- Scrapes standings (GP, W, L, T, PTS, GF, GA, Diff) for multiple seasons.
- Stores data in a SQLite database (`hockey_calgary.db`).
- Maps team names to communities (e.g., "Bow Valley 1" -> "Bow Valley").
- Supports custom community mapping via `community_map.json`.
- Exports data to CSV for viewing and editing.
- **Web Dashboard**: Interactive analytics dashboard to visualize trends and compare communities.

## Setup

1.  **Install Dependencies**:
    The project uses Python. Ensure you have the required packages installed:
    ```bash
    pip install requests beautifulsoup4 pandas sqlalchemy streamlit plotly
    ```

2.  **Database**:
    The database is automatically created when you run the scraper.

## Usage

### 1. Web Analysis Dashboard (Recommended)

The easiest way to use the tool is via the web dashboard.

```bash
streamlit run app.py
```

This will open a web page in your browser where you can:
- **Run the Scraper**: Click the "Run Scraper" button in the sidebar to fetch the latest data.
- **Analyze Trends**: View performance trends over time for different communities.
- **Compare Communities**: See head-to-head comparisons and rankings.
- **Filter Data**: Filter by season, age category (U11, U13, etc.), and community.

### 2. Sync Data (Command Line)

Alternatively, you can run the scraper from the command line:

```bash
python scraper.py
```

This will:
- Fetch all leagues for U9, U11, U13, U15.
- Iterate through available seasons.
- Update the database with the latest stats.

### 3. View/Export Data

To export the data to a CSV file (`hockey_calgary_stats.csv`):

```bash
python export_data.py
```

You can then open this CSV file in Excel or any spreadsheet viewer.

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

After editing the map, run `python scraper.py` again to update the community names in the database.

## Project Structure

- `app.py`: Streamlit web dashboard.
- `scraper.py`: Main scraping script.
- `models.py`: Database models (SQLAlchemy).
- `database.py`: Database connection setup.
- `utils.py`: Helper functions for community name normalization.
- `export_data.py`: Script to export DB to CSV.
- `community_map.json`: Custom mappings for community names.
- `hockey_calgary.db`: SQLite database file (created after running scraper).
