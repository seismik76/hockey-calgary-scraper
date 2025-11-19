import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from scraper import sync_data
import sys
from io import StringIO
import time

# Page Config
st.set_page_config(page_title="Hockey Calgary Analytics", layout="wide")

# Database Connection
DB_URL = "sqlite:///hockey_calgary.db"
engine = create_engine(DB_URL)

# --- Helper Functions ---

def load_data():
    """Loads data from the database into a Pandas DataFrame."""
    query = """
    SELECT 
        s.name as Season,
        l.name as League,
        l.type as Type,
        l.stream as Stream,
        c.name as Community,
        t.name as Team,
        st.gp as GP,
        st.w as W,
        st.l as L,
        st.t as T,
        st.pts as PTS,
        st.gf as GF,
        st.ga as GA,
        st.diff as Diff
    FROM standings st
    JOIN seasons s ON st.season_id = s.id
    JOIN leagues l ON st.league_id = l.id
    JOIN teams t ON st.team_id = t.id
    JOIN communities c ON t.community_id = c.id
    WHERE st.gp > 0
    """
    try:
        df = pd.read_sql(query, engine)
        
        # Feature Engineering
        df['Win %'] = df['W'] / df['GP']
        df['Points %'] = df['PTS'] / (df['GP'] * 2)
        df['Goal Diff/Game'] = df['Diff'] / df['GP']
        
        # Extract Age Category (U9, U11, etc.) from League Name
        def get_age_category(league_name):
            if 'U9' in league_name: return 'U9'
            if 'U11' in league_name: return 'U11'
            if 'U13' in league_name: return 'U13'
            if 'U15' in league_name: return 'U15'
            if 'U18' in league_name: return 'U18'
            if 'U21' in league_name: return 'U21'
            return 'Other'
            
        df['Age Category'] = df['League'].apply(get_age_category)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Sidebar ---

st.sidebar.title("🏒 Hockey Calgary Analytics")

# Scraper Control
st.sidebar.header("Data Sync")
if st.sidebar.button("Run Scraper (Sync Data)"):
    with st.spinner("Scraping data from Hockey Calgary... This may take a minute."):
        # Capture stdout to show progress
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        
        try:
            sync_data()
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

# Filters
st.sidebar.header("Filters")

# Season Filter
all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
selected_seasons = st.sidebar.multiselect("Select Seasons", all_seasons, default=all_seasons)

# Season Type Filter
season_types = df['Type'].unique().tolist()
selected_types = st.sidebar.multiselect("Season Type", season_types, default=['Regular'])

# Age Category Filter
age_categories = sorted(df['Age Category'].unique().tolist())
default_ages = [age for age in ['U11', 'U13', 'U15'] if age in age_categories]
selected_ages = st.sidebar.multiselect("Age Category", age_categories, default=default_ages)

# Community Filter
all_communities = sorted(df['Community'].unique().tolist())
selected_communities = st.sidebar.multiselect("Select Communities", all_communities, default=all_communities)

# League Filter
available_leagues = sorted(df[
    (df['Season'].isin(selected_seasons)) &
    (df['Type'].isin(selected_types)) & 
    (df['Age Category'].isin(selected_ages))
]['League'].unique().tolist())
selected_leagues = st.sidebar.multiselect("Select Leagues (Optional)", available_leagues, default=[])

# Team Filter (Optional)
# Filter teams based on selected communities to avoid too many options
available_teams = sorted(df[df['Community'].isin(selected_communities)]['Team'].unique().tolist())
selected_teams = st.sidebar.multiselect("Select Teams (Optional)", available_teams, default=[])

# Metric Selector
metric_options = ['Win %', 'Points %', 'Goal Diff/Game', 'PTS', 'W', 'L']
selected_metric = st.sidebar.selectbox("Performance Metric", metric_options, index=1)

# Apply Filters
filtered_df = df[
    (df['Season'].isin(selected_seasons)) &
    (df['Type'].isin(selected_types)) & 
    (df['Age Category'].isin(selected_ages)) &
    (df['Community'].isin(selected_communities))
]

if selected_leagues:
    filtered_df = filtered_df[filtered_df['League'].isin(selected_leagues)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

# --- Main Content ---

st.title("Community Performance Analysis")

# 1. Trend Over Time
st.subheader(f"📈 {selected_metric} Trends by Community")
st.markdown("How has performance changed over the seasons?")

# Aggregate by Season and Community
trend_df = filtered_df.groupby(['Season', 'Community'])[selected_metric].mean().reset_index()

fig_trend = px.line(
    trend_df, 
    x='Season', 
    y=selected_metric, 
    color='Community', 
    markers=True,
    title=f"Average {selected_metric} over Seasons",
    category_orders={"Season": sorted(df['Season'].unique())}
)
st.plotly_chart(fig_trend, use_container_width=True)

# 2. Systemic Gap Analysis (Overall Ranking)
st.subheader("🏆 Strongest vs. Weakest (Systemic Gap)")
st.markdown(f"Ranking communities by average **{selected_metric}** over the selected period.")

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
        title=f"Overall Average {selected_metric}"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.dataframe(ranking_df.style.format({selected_metric: "{:.3f}"}), use_container_width=True)

# 3. Detailed Stats View
st.subheader("📋 Detailed Data")
with st.expander("View Raw Data"):
    st.dataframe(filtered_df)

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
        title=f"{selected_metric} Heatmap"
    )
    st.plotly_chart(fig_heat, use_container_width=True)
