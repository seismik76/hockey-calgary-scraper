import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os
from scraper import sync_data
from database import init_db, engine, SessionLocal
from models import ScrapeRun
import sys
from io import StringIO
import time
from utilities.tiering_logic import parse_tier_info, calculate_compliance, get_u11_u13_distribution, get_u15_u18_split, get_u15_u18_tier_distribution
from utilities.utils import standardize_team_label, extract_tier_label

# Admin gate — controls visibility of the "Run Scraper" UI. If ADMIN_PASSWORD
# isn't set, the admin UI is hidden entirely (correct posture for any public
# deployment). When it IS set, a small unlock form appears in the sidebar.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

try:
    import matplotlib
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Page Config
st.set_page_config(page_title="Hockey Calgary Analytics", layout="wide")

# Initialize Database (Ensure tables exist). `engine` is imported from database.py
# and reads DATABASE_URL from the environment / .env.
init_db()


def render_footer():
    """Disclaimer + project context, rendered at the bottom of every page."""
    st.divider()
    st.caption(
        "Personal-interest project — not an authoritative source. Data is scraped from "
        "Hockey Calgary, RAMP (Alberta One), and TeamLinkt; accuracy depends on what "
        "those sources publish. Built for fun, not accountability."
    )


# Stable color mapping so a community gets the same color in every chart on
# every page. Anything not in the map falls back to a default plotly color.
COMMUNITY_COLORS = {
    "Bow River":   "#1f77b4",  # blue
    "Bow Valley":  "#2ca02c",  # green
    "Glenlake":    "#d62728",  # red
    "Knights":     "#9467bd",  # purple
    "McKnight":    "#ff7f0e",  # orange
    "North West":  "#17becf",  # cyan
    "Raiders":     "#8c564b",  # brown
    "Southwest":   "#e377c2",  # pink
    "Springbank":  "#bcbd22",  # olive
    "Trails West": "#7f7f7f",  # grey
    "Wolverines":  "#aec7e8",  # light blue
}


def get_last_scrape():
    db = SessionLocal()
    try:
        return (
            db.query(ScrapeRun)
            .filter(ScrapeRun.status == 'success')
            .order_by(ScrapeRun.finished_at.desc())
            .first()
        )
    finally:
        db.close()


def get_previous_scrape(before_id):
    """Most recent successful scrape strictly before the given id."""
    db = SessionLocal()
    try:
        return (
            db.query(ScrapeRun)
            .filter(ScrapeRun.status == 'success', ScrapeRun.id < before_id)
            .order_by(ScrapeRun.finished_at.desc())
            .first()
        )
    finally:
        db.close()

# --- Helper Functions ---

@st.cache_data
def load_data():
    """Loads data from the database into a Pandas DataFrame.

    Cached across reruns until invalidated (the scraper button calls
    st.cache_data.clear() after a successful sync).
    """
    # Note: community joins directly from standings.community_id (denormalized at scrape time).
    # Older rows fall back to teams.community_id via LEFT JOIN + COALESCE so historical
    # records that pre-date the column still resolve.
    query = """
    SELECT
        s.name as "Season",
        l.name as "League",
        l.type as "Type",
        l.stream as "Stream",
        COALESCE(c_st.name, c_t.name) as "Community",
        t.name as "Team",
        st.gp as "GP",
        st.w as "W",
        st.l as "L",
        st.t as "T",
        st.pts as "PTS",
        st.gf as "GF",
        st.ga as "GA",
        st.diff as "Diff",
        st.source_url as "Source"
    FROM standings st
    JOIN seasons s ON st.season_id = s.id
    JOIN leagues l ON st.league_id = l.id
    JOIN teams t ON st.team_id = t.id
    LEFT JOIN communities c_st ON st.community_id = c_st.id
    LEFT JOIN communities c_t ON t.community_id = c_t.id
    """
    try:
        df = pd.read_sql(query, engine)

        # Vectorized rate metrics (NaN-safe via .where; teams with GP=0 get 0).
        gp_positive = df['GP'] > 0
        df['Win %'] = (df['W'] / df['GP']).where(gp_positive, 0.0)
        df['Points %'] = (df['PTS'] / (df['GP'] * 2)).where(gp_positive, 0.0)
        df['Goal Diff/Game'] = (df['Diff'] / df['GP']).where(gp_positive, 0.0)

        # Pull the age category (U9, U11, ..., U21) out of the league name via regex.
        df['Age Category'] = df['League'].str.extract(r'(U\d{1,2})', expand=False).fillna('Other')

        # Tier label per row: 'AA', 'HADP', '1'..'6', or 'Other'.
        df['Tier'] = df['League'].apply(extract_tier_label)

        # Composed, consistent team display label — used wherever a Team appears
        # on screen. The raw `team.name` stays as `Team` for audit/CSV export.
        df['Team Label'] = df.apply(
            lambda r: standardize_team_label(r['Team'], r['League'], r['Community']),
            axis=1,
        )

        # Exclude Girls Hockey Calgary from the headline analytics.
        df = df[df['Community'] != 'Girls Hockey Calgary']

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Sidebar ---

st.sidebar.title("🏒 Hockey Calgary Analytics")

# Navigation
page = st.sidebar.radio("Navigation", ["Analytics", "Tier 1 Dilution Analysis"])

# Last scrape timestamp
last_run = get_last_scrape()
if last_run and last_run.finished_at:
    st.sidebar.caption(
        f"Last updated: {last_run.finished_at.strftime('%Y-%m-%d %H:%M UTC')} "
        f"({last_run.standings_count or 0} standings)"
    )
    if last_run.leagues_failed:
        st.sidebar.warning(
            f"{last_run.leagues_failed} league(s) failed during last scrape: "
            f"{last_run.failed_leagues or '(see logs)'}"
        )
    # Drift check against the prior successful scrape — surfaces silent URL-pattern breaks.
    prev = get_previous_scrape(last_run.id)
    if prev and prev.standings_count and last_run.standings_count:
        delta = last_run.standings_count - prev.standings_count
        pct = delta / prev.standings_count
        if pct < -0.05:
            st.sidebar.warning(
                f"Standings dropped {abs(delta)} rows ({pct:.0%}) vs previous scrape "
                f"({prev.standings_count} → {last_run.standings_count}). "
                "An upstream source may have changed."
            )
else:
    st.sidebar.caption("Last updated: never — run the scraper to populate.")

# Admin gate — only show Run Scraper controls when ADMIN_PASSWORD is set AND
# the visitor has unlocked it this session. The unlock persists per-session via
# st.session_state.
run_clicked = False
do_reset = False
if ADMIN_PASSWORD:
    if not st.session_state.get('admin_unlocked'):
        with st.sidebar.expander("🔐 Admin"):
            pw = st.text_input("Password", type="password", key="admin_pw_input")
            if st.button("Unlock", key="admin_unlock_btn"):
                if pw == ADMIN_PASSWORD:
                    st.session_state['admin_unlocked'] = True
                    st.rerun()
                else:
                    st.error("Wrong password.")
    else:
        # Unlocked: show the Data Sync expander.
        with st.sidebar.expander("⚙️ Data Sync", expanded=True):
            st.caption(
                "Runs the scraper against Hockey Calgary, RAMP, and TeamLinkt. "
                "Takes ~10-15 minutes; the page will block while it runs."
            )
            sync_mode = st.radio(
                "Mode",
                ["Update existing data", "Full reset (rebuild from scratch)"],
                index=0,
                help=(
                    "Update is safe and additive — existing standings stay, new/changed rows "
                    "get upserted. Full reset drops everything first; only use it if the DB "
                    "is corrupted or you want to start clean."
                ),
            )
            do_reset = sync_mode.startswith("Full reset")
            confirm = st.checkbox("I want to run the scraper now", key="confirm_scrape")
            run_clicked = st.button("Run Scraper (Sync Data)", disabled=not confirm)
            if st.button("Lock admin", key="admin_lock_btn"):
                st.session_state['admin_unlocked'] = False
                st.rerun()

if run_clicked:
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()

    def update_progress(pct, msg):
        progress_bar.progress(pct)
        status_text.text(msg)

    with st.spinner("Scraping data from Hockey Calgary... This can take up to 10 minutes."):
        # Capture stdout to show progress
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        try:
            sync_data(reset=do_reset, progress_callback=update_progress)
            st.success("Sync Complete!")
        except Exception as e:
            st.error(f"An error occurred: {e}")
        finally:
            sys.stdout = old_stdout
            
        # Show logs
        with st.expander("Scraper Logs"):
            st.text(mystdout.getvalue())
            
    # Clear cache to reload data
    st.cache_data.clear()

# Load Data
df = load_data()

if df.empty:
    st.warning("No data found. Please run the scraper first.")
    st.stop()

# Data-quality / coverage panel — meta info, available on every page from the sidebar.
with st.sidebar.expander("ℹ️ About this data"):
    st.caption(
        f"{len(df):,} team-season records across {df['Season'].nunique()} seasons "
        f"and {df['Community'].nunique()} communities. "
        "Coverage by Season × Type × Age below."
    )
    completeness = df.groupby(['Season', 'Type', 'Age Category']).size().unstack(fill_value=0)
    if HAS_MATPLOTLIB:
        st.dataframe(completeness.style.background_gradient(cmap="Greens", axis=None))
    else:
        st.dataframe(completeness)

if page == "Analytics":
    st.title("🏒 Hockey Calgary Analytics")
    st.markdown(
        "Performance data for Calgary minor hockey communities, 2020-2026. "
        "Filter by season, age, and community in the sidebar; see the "
        "**Tier 1 Dilution Analysis** tab for the hypothesis this project was built to test."
    )

    # Filters — grouped by purpose. Time + Scope are the common case;
    # League/Team live behind a "Refine" expander to keep the sidebar scannable.
    st.sidebar.header("Filters")

    # Metric is always-visible at the top — it changes what the whole page is about.
    metric_map = {
        'Points': 'PTS',
        'Wins': 'W',
        'Losses': 'L',
        'Goal Diff': 'Diff',
        'Goals For': 'GF',
        'Goals Against': 'GA',
    }
    selected_metric_label = st.sidebar.selectbox("Metric", list(metric_map.keys()))
    selected_metric = metric_map[selected_metric_label]

    with st.sidebar.expander("📅 Time", expanded=True):
        all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
        default_seasons = all_seasons[:2]  # current + previous season
        selected_seasons = st.multiselect("Seasons", all_seasons, default=default_seasons)

        season_types = df['Type'].unique().tolist()
        default_types = [t for t in ['Regular', 'Seeding'] if t in season_types]
        if not default_types and season_types:
            default_types = [season_types[0]]
        selected_types = st.multiselect("Season Type", season_types, default=default_types)

    with st.sidebar.expander("🏘️ Scope", expanded=True):
        age_categories = sorted(df['Age Category'].unique().tolist())
        default_ages = [a for a in ['U11', 'U13'] if a in age_categories] or age_categories
        selected_ages = st.multiselect("Age Category", age_categories, default=default_ages)

        # Tier: AA / HADP / 1-6 / Other — ordered for usefulness, not alphabet.
        _TIER_ORDER = ['AA', 'HADP', '1', '2', '3', '4', '5', '6', 'Other']
        present_tiers = set(df['Tier'].unique())
        tier_options = [t for t in _TIER_ORDER if t in present_tiers]
        selected_tiers = st.multiselect("Tier", tier_options, default=tier_options)

        division = st.radio("Hockey Calgary Division", ["All", "North", "South"], index=0, horizontal=True)
        north_communities = ['Springbank', 'North West', 'Bow River', 'McKnight', 'Raiders']
        south_communities = ['Trails West', 'Glenlake', 'Bow Valley', 'Knights', 'Southwest', 'Wolverines']
        all_communities = sorted(df['Community'].unique().tolist())
        if division == "North":
            community_options = [c for c in all_communities if c in north_communities]
        elif division == "South":
            community_options = [c for c in all_communities if c in south_communities]
        else:
            community_options = all_communities
        selected_communities = st.multiselect("Communities", community_options, default=community_options)

    with st.sidebar.expander("🔬 Refine (optional)", expanded=False):
        available_leagues = sorted(df[
            (df['Season'].isin(selected_seasons)) &
            (df['Type'].isin(selected_types)) &
            (df['Age Category'].isin(selected_ages))
        ]['League'].unique().tolist())
        selected_leagues = st.multiselect("Leagues", available_leagues, default=[])

        # Use the standardized Team Label for selection — far easier to scan
        # than the raw upstream names that vary by source/era.
        available_teams = sorted(df[df['Community'].isin(selected_communities)]['Team Label'].unique().tolist())
        selected_teams = st.multiselect("Teams", available_teams, default=[])

    # --- Apply Filters ---
    filtered_df = df.copy()

    if selected_seasons:
        filtered_df = filtered_df[filtered_df['Season'].isin(selected_seasons)]

    if selected_types:
        filtered_df = filtered_df[filtered_df['Type'].isin(selected_types)]

    if selected_ages:
        filtered_df = filtered_df[filtered_df['Age Category'].isin(selected_ages)]

    if selected_tiers:
        filtered_df = filtered_df[filtered_df['Tier'].isin(selected_tiers)]

    if selected_communities:
        filtered_df = filtered_df[filtered_df['Community'].isin(selected_communities)]

    if selected_leagues:
        filtered_df = filtered_df[filtered_df['League'].isin(selected_leagues)]

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team Label'].isin(selected_teams)]

    # Single download — defaults to the current filtered view; toggle to get everything.
    st.sidebar.markdown("---")
    include_all = st.sidebar.checkbox("Include all rows (ignore filters)", value=False, key="dl_all")
    export_df = df if include_all else filtered_df
    export_name = 'hockey_calgary_all_data.csv' if include_all else 'hockey_calgary_filtered_data.csv'
    st.sidebar.download_button(
        label=f"Download CSV ({len(export_df):,} rows)",
        data=export_df.to_csv(index=False).encode('utf-8'),
        file_name=export_name,
        mime='text/csv',
    )

    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    # --- Current-view summary ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Teams", filtered_df['Team'].nunique())
    m2.metric("Leagues", filtered_df['League'].nunique())
    m3.metric("Seasons", filtered_df['Season'].nunique())
    m4.metric("Communities", filtered_df['Community'].nunique())

    # --- Main Content ---

    st.header(f"{selected_metric_label} Analysis")

    # 1. Trend Over Time
    st.subheader(f"📈 {selected_metric_label} Trends by Community")
    st.markdown("How has performance changed over the seasons?")

    # Aggregate by Season and Community
    trend_df = filtered_df.groupby(['Season', 'Community'])[selected_metric].mean().reset_index()

    fig_trend = px.line(
        trend_df,
        x='Season',
        y=selected_metric,
        color='Community',
        color_discrete_map=COMMUNITY_COLORS,
        markers=True,
        title=f"Average {selected_metric_label} over Seasons",
        category_orders={"Season": sorted(filtered_df['Season'].unique())}
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # 2. Systemic Gap Analysis (Overall Ranking)
    st.subheader("🏆 Strongest vs. Weakest (Systemic Gap)")
    st.markdown(f"Ranking communities by average **{selected_metric_label}** over the selected period.")

    ranking_df = filtered_df.groupby('Community')[selected_metric].mean().reset_index()
    ranking_df = ranking_df.sort_values(by=selected_metric, ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_bar = px.bar(
            ranking_df, 
            x='Community', 
            y=selected_metric, 
            color=selected_metric,
            color_continuous_scale='RdYlGn',
            title=f"Overall Average {selected_metric_label}"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.dataframe(ranking_df.style.format({selected_metric: "{:.3f}"}), use_container_width=True)

    # 3. Detailed Stats View
    st.subheader("📋 Detailed Data")
    with st.expander("View Raw Data"):
        # Lead with the standardized Team Label; raw Team / League / Stream still
        # available by scrolling, useful for audit and CSV export.
        display_cols = [
            'Team Label', 'Community', 'Season', 'Age Category', 'Tier', 'Type',
            'GP', 'W', 'L', 'T', 'PTS', 'GF', 'GA', 'Diff',
            'Win %', 'Points %', 'Goal Diff/Game',
            'Team', 'League', 'Stream', 'Source',
        ]
        display_cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(
            filtered_df[display_cols],
            column_config={
                "Source": st.column_config.LinkColumn("Source URL"),
            },
            use_container_width=True,
        )

    # 4. Head-to-Head Matrix (Heatmap)
    if len(selected_communities) > 1:
        st.subheader("🔥 Performance Heatmap")
        st.markdown("Compare performance intensity across seasons.")
        
        heatmap_df = filtered_df.pivot_table(
            index='Community', 
            columns='Season', 
            values=selected_metric, 
            aggfunc='mean'
        )
        
        fig_heat = px.imshow(
            heatmap_df,
            text_auto=".2f",
            color_continuous_scale='RdYlGn',
            title=f"{selected_metric_label} Heatmap"
        )
        st.plotly_chart(fig_heat, use_container_width=True)



elif page == "Tier 1 Dilution Analysis":
    st.title("📉 Tier 1 Dilution Analysis")
    st.markdown(
        "**The claim:** communities that just barely cross the threshold for fielding "
        "a *second* Tier 1 team underperform — not just at Tier 1, but **across every tier** "
        "in that age group. The talent pool gets split too thin."
    )
    with st.expander("How this is calculated"):
        st.markdown(
            "For each (Season × Age Category), the scraper infers a *threshold* — the team count "
            "above which an association is expected to field 2+ Tier 1 teams. Communities are "
            "then bucketed:\n\n"
            "- **Just Below Threshold** — 1-3 teams shy of the threshold, fielding 1 Tier 1\n"
            "- **Just Above Threshold (Diluted)** — exactly at the threshold, forced to field 2 Tier 1s\n"
            "- **Large (Established)** — well above the threshold, comfortably fielding 2+\n\n"
            "Performance is averaged across **all teams** in the age group (not just Tier 1), "
            "so the metric captures community-wide impact."
        )
    
    # --- Filters ---
    st.sidebar.header("Analysis Filters")

    metric_map = {
        'Points %': 'Points %',
        'Win %': 'Win %',
        'Goal Diff/Game': 'Goal Diff/Game',
    }
    selected_metric_label = st.sidebar.selectbox("Performance Metric", list(metric_map.keys()))
    selected_metric = metric_map[selected_metric_label]

    with st.sidebar.expander("📅 Time", expanded=True):
        all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
        default_seasons = all_seasons[:2]  # current + previous season
        selected_seasons = st.multiselect("Seasons", all_seasons, default=default_seasons)

        season_types = df['Type'].unique().tolist()
        default_types = [t for t in ['Regular', 'Seeding'] if t in season_types]
        if not default_types and season_types:
            default_types = [season_types[0]]
        selected_types = st.multiselect("Season Type", season_types, default=default_types)

    with st.sidebar.expander("🏘️ Scope", expanded=True):
        age_categories = sorted(df['Age Category'].unique().tolist())
        default_ages = [a for a in ['U11', 'U13'] if a in age_categories] or age_categories
        selected_ages = st.multiselect("Age Category", age_categories, default=default_ages)

        # Tier: AA / HADP / 1-6 / Other — ordered for usefulness, not alphabet.
        _TIER_ORDER = ['AA', 'HADP', '1', '2', '3', '4', '5', '6', 'Other']
        present_tiers = set(df['Tier'].unique())
        tier_options = [t for t in _TIER_ORDER if t in present_tiers]
        selected_tiers = st.multiselect("Tier", tier_options, default=tier_options)

        division = st.radio("Hockey Calgary Division", ["All", "North", "South"], index=0, horizontal=True)
        north_communities = ['Springbank', 'North West', 'Bow River', 'McKnight', 'Raiders']
        south_communities = ['Trails West', 'Glenlake', 'Bow Valley', 'Knights', 'Southwest', 'Wolverines']
        all_communities = sorted(df['Community'].unique().tolist())
        if division == "North":
            community_options = [c for c in all_communities if c in north_communities]
        elif division == "South":
            community_options = [c for c in all_communities if c in south_communities]
        else:
            community_options = all_communities
        selected_communities = st.multiselect("Communities", community_options, default=community_options)

    # --- Data Processing ---
    
    # 1. Filter Base Data
    analysis_df = df[
        (df['Season'].isin(selected_seasons)) &
        (df['Type'].isin(selected_types)) &
        (df['Age Category'].isin(selected_ages)) &
        (df['Tier'].isin(selected_tiers)) &
        (df['Community'].isin(selected_communities))
    ].copy()
    
    if analysis_df.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    # --- Current-view summary ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Teams", analysis_df['Team'].nunique())
    m2.metric("Leagues", analysis_df['League'].nunique())
    m3.metric("Seasons", analysis_df['Season'].nunique())
    m4.metric("Communities", analysis_df['Community'].nunique())

    # 2. Identify Elite (AA/HADP) to exclude from Community Size Count
    def is_elite(league_name):
        name_upper = league_name.upper()
        if 'AA' in name_upper: return True
        if 'HADP' in name_upper: return True
        return False
        
    analysis_df['Is_Elite'] = analysis_df['League'].apply(is_elite)
    
    # 3. Calculate Community Size (Total Non-Elite Teams) per Season/Community/Age
    non_elite_df = analysis_df[~analysis_df['Is_Elite']].copy()
    
    # Group by Age Category as well
    community_sizes = non_elite_df.groupby(['Season', 'Community', 'Age Category'])['Team'].nunique().reset_index()
    community_sizes.rename(columns={'Team': 'Total_Community_Teams'}, inplace=True)
    
    # 4. Identify Tier 1 Teams (for Threshold Logic)
    def is_tier_1(league_name):
        parsed = parse_tier_info(league_name)
        if parsed['tier'] == 1:
            if parsed['stream'] == 'NBC': return False
            return True
        return False
        
    analysis_df['Is_Tier_1'] = analysis_df['League'].apply(is_tier_1)
    
    # Calculate Tier 1 Count per Community/Season/Age
    tier1_counts = analysis_df[analysis_df['Is_Tier_1']].groupby(['Season', 'Community', 'Age Category'])['Team'].nunique().reset_index()
    tier1_counts.rename(columns={'Team': 'Tier1_Count'}, inplace=True)
    
    # 5. Calculate OVERALL Performance per Community/Season/Age — weighted by GP.
    # Naive mean(rate) gives a 3-game team the same weight as a 30-game team, which
    # silently warps the community average. Sum the rate*GP and divide by sum(GP)
    # so the result equals "total events / total games" across the community.
    performance_df = non_elite_df[non_elite_df['GP'] > 0].copy()
    performance_df['_w'] = performance_df[selected_metric] * performance_df['GP']
    grouped = performance_df.groupby(['Season', 'Community', 'Age Category'])
    overall_stats = grouped.agg(_w_sum=('_w', 'sum'), _gp_sum=('GP', 'sum')).reset_index()
    overall_stats['Overall_Performance'] = overall_stats['_w_sum'] / overall_stats['_gp_sum']
    overall_stats = overall_stats[['Season', 'Community', 'Age Category', 'Overall_Performance']]
    
    # 6. Merge Data
    merged_df = pd.merge(community_sizes, tier1_counts, on=['Season', 'Community', 'Age Category'], how='left')
    merged_df = pd.merge(merged_df, overall_stats, on=['Season', 'Community', 'Age Category'], how='left')
    
    # Fill NaN Tier 1 Count with 0
    merged_df['Tier1_Count'] = merged_df['Tier1_Count'].fillna(0)
    merged_df.dropna(subset=['Total_Community_Teams'], inplace=True)
    
    # --- NEW LOGIC: Threshold Analysis ---
    
    # Identify the Threshold PER SEASON AND AGE
    # We calculate thresholds from the FULL dataset (filtered by Type/Age only) to ensure accuracy
    # even if specific communities are filtered out of the view.
    full_analysis_df = df[
        (df['Type'].isin(selected_types)) & 
        (df['Age Category'].isin(selected_ages))
    ].copy()
    full_analysis_df['Is_Tier_1'] = full_analysis_df['League'].apply(is_tier_1)
    full_analysis_df['Is_Elite'] = full_analysis_df['League'].apply(is_elite)
    full_non_elite = full_analysis_df[~full_analysis_df['Is_Elite']]
    
    full_sizes = full_non_elite.groupby(['Season', 'Community', 'Age Category'])['Team'].nunique().reset_index()
    full_sizes.rename(columns={'Team': 'Total_Community_Teams'}, inplace=True)
    
    full_t1 = full_analysis_df[full_analysis_df['Is_Tier_1']].groupby(['Season', 'Community', 'Age Category'])['Team'].nunique().reset_index()
    full_t1.rename(columns={'Team': 'Tier1_Count'}, inplace=True)
    
    full_merged = pd.merge(full_sizes, full_t1, on=['Season', 'Community', 'Age Category'], how='left')
    full_merged['Tier1_Count'] = full_merged['Tier1_Count'].fillna(0)
    
    # Calculate thresholds map: (Season, Age) -> Inferred Threshold
    # Algorithm: Find T that minimizes (Size < T & T1>=2) + (Size >= T & T1=1)
    season_age_thresholds = {}
    outliers_map = {} # (Season, Age) -> List of outlier strings
    threshold_summary_data = []

    grouped_thresholds = full_merged.groupby(['Season', 'Age Category'])

    for (season, age), group in grouped_thresholds:
        best_t = 0
        max_score = -1
        best_outliers = []
        
        # Range of possible team sizes in this group
        if group.empty: continue
        min_teams = int(group['Total_Community_Teams'].min())
        max_teams = int(group['Total_Community_Teams'].max())
        
        # Brute force search for best threshold
        # We look for a transition point. 
        # If no 2-team communities exist, threshold is effectively infinite (or max+1)
        if group['Tier1_Count'].max() < 2:
             season_age_thresholds[(season, age)] = 999
             continue

        for t in range(min_teams, max_teams + 2):
            # Rule: If Size >= t, expect T1 >= 2. Else T1 = 1.
            compliant = group[
                ((group['Total_Community_Teams'] < t) & (group['Tier1_Count'] <= 1)) |
                ((group['Total_Community_Teams'] >= t) & (group['Tier1_Count'] >= 2))
            ]
            score = len(compliant)
            
            if score > max_score:
                max_score = score
                best_t = t
                
                # Identify outliers for this T
                non_compliant = group[
                    ~(((group['Total_Community_Teams'] < t) & (group['Tier1_Count'] <= 1)) |
                      ((group['Total_Community_Teams'] >= t) & (group['Tier1_Count'] >= 2)))
                ]
                
                outlier_list = []
                for _, row in non_compliant.iterrows():
                    # reason = "Playing Up" if row['Tier1_Count'] >= 2 else "Playing Down"
                    outlier_list.append(f"{row['Community']} ({int(row['Total_Community_Teams'])} teams, {int(row['Tier1_Count'])} T1)")
                best_outliers = outlier_list
        
        season_age_thresholds[(season, age)] = best_t
        outliers_map[(season, age)] = best_outliers
        
        threshold_summary_data.append({
            "Season": season,
            "Age Category": age,
            "Inferred Threshold": best_t,
            "Outliers": ", ".join(best_outliers) if best_outliers else "None"
        })

    if not season_age_thresholds:
        st.warning("Not enough data to identify 2-team thresholds (no communities with 2+ Tier 1 teams found in selected scope).")
    else:
        # Define Groups relative to threshold.
        # Window sizes:
        #   - "Just Below"    = 1 Tier 1, size in [threshold-3, threshold-1]  (3-team window)
        #   - "Just Above"    = 2+ Tier 1, size in [threshold, threshold+1]   (2-team window)
        #     (Widened from `size == threshold` exactly — that 0-team window often
        #      produced cohorts of 1-3 communities, far too noisy to compare.)
        #   - "Large"         = 2+ Tier 1, size > threshold+1
        #   - "Small"         = 1 Tier 1, size < threshold-3
        def categorize_threshold(row):
            key = (row['Season'], row['Age Category'])
            if key not in season_age_thresholds:
                return "Other"

            threshold = int(season_age_thresholds[key])
            size = row['Total_Community_Teams']
            t1_count = row['Tier1_Count']

            if t1_count == 1:
                if size >= threshold - 3:
                    return "Just Below Threshold (1 Team)"
                return "Small (1 Team)"
            elif t1_count >= 2:
                if threshold <= size <= threshold + 1:
                    return "Just Above Threshold (Diluted)"
                return "Large (Established)"
            return "Other"

        merged_df['Threshold Category'] = merged_df.apply(categorize_threshold, axis=1)
        
        # --- Create Labels for Plots ---
        def get_label(row):
            name = row['Community']
            overrides = {
                "Bow River": "BR",
                "Bow Valley": "BV",
                "Glenlake": "GL",
                "Knights": "K",
                "McKnight": "MK",
                "North West": "NW",
                "Raiders": "R",
                "Southwest": "SW",
                "Springbank": "SB",
                "Trails West": "TW",
                "Wolverines": "W"
            }
            abbrev = overrides.get(name, name[:2].upper())
            season_short = row['Season'].split('-')[-1][-2:]
            return f"{abbrev}-{season_short} ({row['Age Category']})"

        merged_df['Label'] = merged_df.apply(get_label, axis=1)

        # --- Headline result: the answer to "does the data support the claim?" ---
        st.subheader("Headline result")
        cohort_stats = (
            merged_df[merged_df['Threshold Category'].isin([
                "Small (1 Team)",
                "Just Below Threshold (1 Team)",
                "Just Above Threshold (Diluted)",
                "Large (Established)",
            ])]
            .groupby('Threshold Category')['Overall_Performance']
            .agg(['mean', 'count'])
        )

        def _stat(label):
            if label in cohort_stats.index:
                m = cohort_stats.loc[label, 'mean']
                n = int(cohort_stats.loc[label, 'count'])
                return m, n
            return None, 0

        small_m, small_n = _stat("Small (1 Team)")
        below_m, below_n = _stat("Just Below Threshold (1 Team)")
        diluted_m, diluted_n = _stat("Just Above Threshold (Diluted)")
        large_m, large_n = _stat("Large (Established)")

        # Delta of Diluted vs the average of its neighbours (Below + Large) — the
        # direct test of the dilution claim.
        neighbour_means = [m for m in (below_m, large_m) if m is not None]
        delta_vs_neighbours = (
            (diluted_m - sum(neighbour_means) / len(neighbour_means))
            if (diluted_m is not None and neighbour_means) else None
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Small (1 T1)", f"{small_m:.3f}" if small_m is not None else "—",
                  help=f"n = {small_n}")
        c2.metric("Just Below", f"{below_m:.3f}" if below_m is not None else "—",
                  help=f"n = {below_n}")
        c3.metric(
            "⚠️ Just Above (Diluted)",
            f"{diluted_m:.3f}" if diluted_m is not None else "—",
            delta=(f"{delta_vs_neighbours:+.3f} vs neighbours"
                   if delta_vs_neighbours is not None else None),
            delta_color="inverse",  # negative delta = red = dilution evidence
            help=f"n = {diluted_n}",
        )
        c4.metric("Large (Established)", f"{large_m:.3f}" if large_m is not None else "—",
                  help=f"n = {large_n}")

        if delta_vs_neighbours is not None and diluted_n >= 3:
            direction = "below" if delta_vs_neighbours < 0 else "above"
            st.caption(
                f"Diluted communities perform **{abs(delta_vs_neighbours):.3f} {direction}** "
                f"the average of their neighbouring cohorts "
                f"({selected_metric_label}, n={diluted_n} community-season-age observations)."
            )
        elif diluted_n < 3:
            st.caption(
                f"⚠️ Only {diluted_n} observation(s) in the Diluted cohort — "
                "widen your Season/Age filters for a meaningful comparison."
            )

        # --- Visualizations ---
        st.divider()

        # 1. The "Cliff" Comparison
        st.subheader("1. The 'Dilution Cliff' (Community-Wide)")
        
        # Display Thresholds Table
        st.markdown("### Dynamic Thresholds")
        st.markdown("The size threshold for requiring 2 Tier 1 teams varies by Season and Age Category.")
        
        if threshold_summary_data:
            thresh_display = pd.DataFrame(threshold_summary_data)
            st.table(thresh_display.sort_values(['Season', 'Age Category'], ascending=[False, True]))
        else:
            st.info("No threshold data available.")

        st.markdown(f"""
        Comparing the **Average Performance of ALL Teams** in the community.
        *   **Just Below Threshold**: 1-3 teams smaller than the threshold (1 Tier 1).
        *   **Just Above Threshold**: Exactly at the threshold (2 Tier 1s).
        """)
        
        # Show all four cohorts so the visual comparison is complete. The keystone
        # claim is that "Diluted" underperforms BOTH neighbouring cohorts (Small + Just Below).
        contrast_df = merged_df[merged_df['Threshold Category'].isin([
            "Small (1 Team)",
            "Just Below Threshold (1 Team)",
            "Just Above Threshold (Diluted)",
            "Large (Established)",
        ])].copy()

        # Imports for manual plotting
        import plotly.graph_objects as go
        import numpy as np

        # Categories ordered left→right by community size; colors:
        #   Small / Just Below = green (healthy 1 T1)
        #   Just Above (Diluted) = red (the hypothesis)
        #   Large = blue (healthy 2+ T1)
        categories = [
            "Small (1 Team)",
            "Just Below Threshold (1 Team)",
            "Just Above Threshold (Diluted)",
            "Large (Established)",
        ]
        colors = {
            "Small (1 Team)":                 "#86c486",  # pale green
            "Just Below Threshold (1 Team)":  "#2ca02c",  # green
            "Just Above Threshold (Diluted)": "#d62728",  # red
            "Large (Established)":            "#1f77b4",  # blue
        }
        
        # Map Categories to X-values for Jittering
        cat_map = {cat: i for i, cat in enumerate(categories)}
        contrast_df['X_Base'] = contrast_df['Threshold Category'].map(cat_map)
        
        # Add Jitter (Random offset)
        np.random.seed(42) # For consistent jitter
        contrast_df['X_Jitter'] = contrast_df['X_Base'] + np.random.uniform(-0.2, 0.2, size=len(contrast_df))
        
        fig_cliff = go.Figure()
        
        # Add Box Plots (Background)
        for cat in categories:
            cat_data = contrast_df[contrast_df['Threshold Category'] == cat]
            if cat_data.empty: continue
            
            fig_cliff.add_trace(go.Box(
                y=cat_data['Overall_Performance'],
                x=[cat_map[cat]] * len(cat_data), # Position at integer x
                name=cat,
                marker_color=colors[cat],
                boxpoints=False, # We add points manually
                showlegend=True
            ))
            
        # Add Scatter Points (Jittered; hover-only — per-point labels overlap
        # to the point of illegibility once a cohort has 5+ communities).
        for cat in categories:
            cat_data = contrast_df[contrast_df['Threshold Category'] == cat]
            if cat_data.empty: continue

            fig_cliff.add_trace(go.Scatter(
                x=cat_data['X_Jitter'],
                y=cat_data['Overall_Performance'],
                mode='markers',
                marker=dict(color=colors[cat], size=7, opacity=0.75,
                            line=dict(width=0.5, color='white')),
                name=cat,
                showlegend=False,  # Legend already shown by Box
                hovertext=cat_data.apply(
                    lambda row: f"{row['Community']} ({row['Season']}) — {row['Age Category']}<br>"
                                f"Teams: {row['Total_Community_Teams']}, Tier 1: {row['Tier1_Count']}",
                    axis=1,
                ),
                hoverinfo='text+y',
            ))

        # Update Layout
        fig_cliff.update_layout(
            title=f"Community-Wide Performance Drop at Threshold",
            yaxis_title=f"Avg Community {selected_metric_label}",
            xaxis=dict(
                tickmode='array',
                tickvals=list(cat_map.values()),
                ticktext=list(cat_map.keys()),
                title="Threshold Category"
            ),
            showlegend=True
        )
            
        st.plotly_chart(fig_cliff, use_container_width=True)

        # --- NEW VISUALIZATION: Impact of Aggressiveness on Performance ---
        st.subheader("2. Impact of Tiering Aggressiveness")
        st.markdown("""
        This chart visualizes the relationship between **Tiering Aggressiveness** (% of teams in Tier 1) and **Overall Performance**.
        *   **Trails** connect seasons chronologically.
        *   **Down & Right**: Community became more aggressive and performance dropped (Dilution).
        *   **Up & Right**: Community became more aggressive and performance improved/sustained.
        """)
        
        # Calculate Tiering Aggressiveness for the trend chart
        merged_df['Tiering_Aggressiveness'] = merged_df['Tier1_Count'] / merged_df['Total_Community_Teams']

        # For the trend line, we aggregate by Season/Community (averaging across Age Categories if multiple selected)
        # This gives a cleaner "Overall Community Health" view
        trend_agg_df = merged_df.groupby(['Season', 'Community']).agg({
            'Overall_Performance': 'mean',
            'Tiering_Aggressiveness': 'mean',
            'Total_Community_Teams': 'sum',
            'Tier1_Count': 'sum'
        }).reset_index()
        
        trend_agg_df = trend_agg_df.sort_values('Season')
        
        # Create short season label for the chart text
        trend_agg_df['Season_Label'] = trend_agg_df['Season'].apply(lambda x: "'" + x.split('-')[-1][-2:])

        fig_trend = px.line(
            trend_agg_df,
            x='Tiering_Aggressiveness',
            y='Overall_Performance',
            color='Community',
            color_discrete_map=COMMUNITY_COLORS,
            text='Season_Label',
            markers=True,
            hover_data={
                'Season': True,
                'Tiering_Aggressiveness': ':.1%',
                'Overall_Performance': ':.3f',
                'Total_Community_Teams': True,
                'Tier1_Count': True,
                'Season_Label': False
            },
            title=f"Performance vs. Tiering Aggressiveness (Trajectory)",
            labels={
                'Overall_Performance': f"Avg Community {selected_metric_label}",
                'Tiering_Aggressiveness': 'Tiering Aggressiveness (% T1)'
            }
        )
        
        fig_trend.update_traces(textposition="top center")
        fig_trend.update_layout(xaxis_tickformat='.0%')
        
        st.plotly_chart(fig_trend, use_container_width=True)

    # 5. Data Table
    with st.expander("View Analysis Data"):
        st.dataframe(merged_df.sort_values(by='Total_Community_Teams'))


render_footer()

