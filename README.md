# Hockey Calgary Analytics & Scraper

A comprehensive data analytics platform for minor hockey in Calgary. This tool scrapes historical performance data from **Hockey Calgary** and **Alberta One**, stores it in a local database, and provides an interactive dashboard to analyze community performance, tiering compliance, and systemic trends.

## 🚀 Features

### 1. Robust Data Scraping
*   **Multi-Source Support**: Scrapes data from:
    *   **Hockey Calgary**: U9, U13, U15, U18 (TeamLinkt & Legacy backends).
    *   **Alberta One**: U11 (RAMP Interactive backend).
*   **Historical Data**: Collects standings (GP, W, L, T, PTS, GF, GA, Diff) across multiple seasons.
*   **Smart Mapping**: Automatically maps team names to communities (e.g., "Bow Valley 1" -> "Bow Valley") with custom overrides via `community_map.json`.
*   **Progress Tracking**: Real-time progress bars and status updates during data sync.

### 2. Interactive Analytics Dashboard
The project includes a powerful **Streamlit** dashboard with four dedicated analysis modules:

#### 📊 General Analytics
*   **Trend Analysis**: View performance trends over time for specific communities.
*   **Head-to-Head**: Compare multiple communities directly.
*   **Data Export**: Download full or filtered datasets to CSV.

#### 📋 Tiering Compliance
*   **Alberta One Grids**: Compares actual community team counts against the standardized Alberta One Tiering Grids.
*   **Compliance Check**: Identifies if associations are over-tiering or under-tiering their teams based on their size.

#### 📈 Community Size Analysis
*   **Size vs. Performance**: Investigates the correlation between the size of an association (number of teams) and their on-ice success.
*   **Binning Analysis**: Groups communities into sizes (Small, Medium, Large, Mega) to find "sweet spots" for performance.

#### 📉 Systemic Dilution Analysis (New!)
*   **The "Dilution Cliff"**: Visualizes the performance drop-off that occurs when a community grows just large enough to mandate a second Tier 1 team.
*   **Threshold Detection**: Automatically identifies the "2-team threshold" for each age group.
*   **Tiering Aggressiveness**: Measures the impact of "aggressive tiering" (% of teams in Tier 1) on overall community performance.
*   **Visualizations**:
    *   **Cliff Box Plots**: Compares "Just Below Threshold" vs "Just Above Threshold".
    *   **Yearly Trends**: Color-coded strip plots showing performance by category over time.
    *   **Aggressiveness Scatter**: Regression analysis of Tier 1 ratios vs performance.

## 🛠️ Setup & Installation

1.  **Prerequisites**:
    *   Python 3.8+
    *   Git

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/seismik76/hockey-calgary-scraper.git
    cd hockey-calgary-scraper
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 💻 Usage

### 1. Launch the Dashboard (Recommended)
The easiest way to use the tool is via the web interface.

```bash
streamlit run app.py
```

This will open `http://localhost:8501` in your browser.

### 2. Sync Data
*   **Via Dashboard**: Click the **"Run Scraper (Sync Data)"** button in the sidebar.
*   **Via Command Line**:
    ```bash
    python scraper.py
    ```

## 📂 Project Structure

*   `app.py`: Main Streamlit application containing the dashboard logic and visualizations.
*   `scraper.py`: Core scraping logic for Hockey Calgary and Alberta One.
*   `hockey_calgary.db`: SQLite database storing all scraped data (created automatically).
*   `utilities/`: Helper scripts for tiering logic and data parsing.
*   `community_map.json`: Configuration file for mapping team names to community associations.

## 🔍 Methodology

*   **Dilution Hypothesis**: The "Systemic Dilution" analysis tests the theory that splitting the top talent pool into two teams (when an association barely meets the size threshold) dilutes talent enough to negatively impact the *entire* age group's performance, not just the top teams.
*   **Threshold Calculation**: The system dynamically calculates the "2-team threshold" based on historical data for each age category.

## 📄 License
[MIT License](LICENSE)
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
