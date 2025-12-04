import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from scraper import sync_data
from database import init_db
import sys
from io import StringIO
import time
from utilities.tiering_logic import parse_tier_info, calculate_compliance, get_u11_u13_distribution, get_u15_u18_split, get_u15_u18_tier_distribution

try:
    import matplotlib
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Page Config
st.set_page_config(page_title="Hockey Calgary Analytics", layout="wide")

# Database Connection
DB_URL = "sqlite:///hockey_calgary.db"
engine = create_engine(DB_URL)

# Initialize Database (Ensure tables exist)
init_db()

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
        st.diff as Diff,
        st.source_url as Source
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
        
        # Exclude Girls Hockey Calgary
        df = df[df['Community'] != 'Girls Hockey Calgary']
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Sidebar ---

st.sidebar.title("🏒 Hockey Calgary Analytics")

# Navigation
page = st.sidebar.radio("Navigation", ["Analytics", "Tier 1 Dilution Analysis"])

# Scraper Control
st.sidebar.header("Data Sync")
if st.sidebar.button("Run Scraper (Sync Data)"):
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
            sync_data(reset=True, progress_callback=update_progress)
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

if page == "Analytics":
    # Export
    st.sidebar.header("Export Data")
    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download All Data (CSV)",
        data=csv,
        file_name='hockey_calgary_all_data.csv',
        mime='text/csv',
    )

    # Filters
    st.sidebar.header("Filters")

    # Season Filter
    all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
    default_seasons = ['2025-2026'] if '2025-2026' in all_seasons else [all_seasons[0]] if all_seasons else []
    selected_seasons = st.sidebar.multiselect("Select Seasons", all_seasons, default=default_seasons)

    # Season Type Filter
    season_types = df['Type'].unique().tolist()
    default_types = ['Seeding'] if 'Seeding' in season_types else [season_types[0]] if season_types else []
    selected_types = st.sidebar.multiselect("Season Type", season_types, default=default_types)

    # Age Category Filter
    age_categories = sorted(df['Age Category'].unique().tolist())
    default_ages = [age for age in ['U11', 'U13'] if age in age_categories]
    selected_ages = st.sidebar.multiselect("Age Category", age_categories, default=default_ages)

    # Community Filter
    all_communities = sorted(df['Community'].unique().tolist())

    # Division Selector
    division = st.sidebar.radio("Hockey Calgary Division", ["All", "North", "South"], index=0)

    north_communities = ['Springbank', 'North West', 'Bow River', 'McKnight', 'Raiders']
    south_communities = ['Trails West', 'Glenlake', 'Bow Valley', 'Knights', 'Southwest', 'Wolverines']

    if division == "North":
        community_options = [c for c in all_communities if c in north_communities]
    elif division == "South":
        community_options = [c for c in all_communities if c in south_communities]
    else:
        community_options = all_communities

    selected_communities = st.sidebar.multiselect("Select Communities", community_options, default=community_options)

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
    metric_map = {
        'Points': 'PTS',
        'Wins': 'W',
        'Losses': 'L',
        'Goal Diff': 'Diff',
        'Goals For': 'GF',
        'Goals Against': 'GA'
    }
    selected_metric_label = st.sidebar.selectbox("Select Metric", list(metric_map.keys()))
    selected_metric = metric_map[selected_metric_label]

    # --- Apply Filters ---
    filtered_df = df.copy()

    if selected_seasons:
        filtered_df = filtered_df[filtered_df['Season'].isin(selected_seasons)]

    if selected_types:
        filtered_df = filtered_df[filtered_df['Type'].isin(selected_types)]

    if selected_ages:
        filtered_df = filtered_df[filtered_df['Age Category'].isin(selected_ages)]

    if selected_communities:
        filtered_df = filtered_df[filtered_df['Community'].isin(selected_communities)]

    if selected_leagues:
        filtered_df = filtered_df[filtered_df['League'].isin(selected_leagues)]

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

    # Export Filtered Data
    st.sidebar.markdown("---")
    csv_filtered = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Filtered Data (CSV)",
        data=csv_filtered,
        file_name='hockey_calgary_filtered_data.csv',
        mime='text/csv',
    )

    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    # --- Data Completeness Check ---
    st.header("Data Completeness Check")
    with st.expander("View Data Completeness Matrix"):
        if not df.empty:
            # Group by Season, Type, and Age Category to count records
            completeness = df.groupby(['Season', 'Type', 'Age Category']).size().unstack(fill_value=0)
            
            # Display as a heatmap-style dataframe
            if HAS_MATPLOTLIB:
                st.dataframe(completeness.style.background_gradient(cmap="Greens", axis=None))
            else:
                st.dataframe(completeness)
            
            st.caption("Numbers represent the count of team records found for each Season/Type/Age Group combination.")
        else:
            st.warning("No data available to check.")

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
        st.dataframe(
            filtered_df,
            column_config={
                "Source": st.column_config.LinkColumn("Source URL")
            }
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
    st.header("📉 Systemic Dilution Analysis")
    st.markdown("""
    This analysis investigates the **"Systemic Dilution Effect"** caused by tiering thresholds.
    
    **Hypothesis:** When an association grows just large enough to require **two** Tier 1 teams (instead of one), 
    it doesn't just hurt the Tier 1 teams. It "starves" every subsequent tier of talent, causing a drop in 
    **overall performance across the entire age group** for that community.
    """)
    
    # --- Filters ---
    st.sidebar.header("Analysis Filters")
    
    # Season Filter
    all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
    default_seasons = ['2025-2026'] if '2025-2026' in all_seasons else [all_seasons[0]] if all_seasons else []
    selected_seasons = st.sidebar.multiselect("Select Seasons", all_seasons, default=default_seasons)

    # Season Type Filter
    season_types = df['Type'].unique().tolist()
    default_types = ['Seeding'] if 'Seeding' in season_types else [season_types[0]] if season_types else []
    selected_types = st.sidebar.multiselect("Season Type", season_types, default=default_types)

    # Age Category Filter
    age_categories = sorted(df['Age Category'].unique().tolist())
    default_ages = [age for age in ['U11', 'U13'] if age in age_categories]
    selected_ages = st.sidebar.multiselect("Age Category", age_categories, default=default_ages)

    # Community Filter
    all_communities = sorted(df['Community'].unique().tolist())
    
    # Division Selector
    division = st.sidebar.radio("Hockey Calgary Division", ["All", "North", "South"], index=0)

    north_communities = ['Springbank', 'North West', 'Bow River', 'McKnight', 'Raiders']
    south_communities = ['Trails West', 'Glenlake', 'Bow Valley', 'Knights', 'Southwest', 'Wolverines']

    if division == "North":
        community_options = [c for c in all_communities if c in north_communities]
    elif division == "South":
        community_options = [c for c in all_communities if c in south_communities]
    else:
        community_options = all_communities
        
    selected_communities = st.sidebar.multiselect("Select Communities", community_options, default=community_options)

    # Metric Selector
    metric_map = {
        'Points %': 'Points %',
        'Win %': 'Win %',
        'Goal Diff/Game': 'Goal Diff/Game'
    }
    selected_metric_label = st.sidebar.selectbox("Select Performance Metric", list(metric_map.keys()))
    selected_metric = metric_map[selected_metric_label]

    # --- Data Processing ---
    
    # 1. Filter Base Data
    analysis_df = df[
        (df['Season'].isin(selected_seasons)) &
        (df['Type'].isin(selected_types)) &
        (df['Age Category'].isin(selected_ages)) &
        (df['Community'].isin(selected_communities))
    ].copy()
    
    if analysis_df.empty:
        st.warning("No data matches the selected filters.")
        st.stop()
    
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
    
    # 5. Calculate OVERALL Performance per Community/Season/Age
    overall_stats = non_elite_df.groupby(['Season', 'Community', 'Age Category'])[selected_metric].mean().reset_index()
    overall_stats.rename(columns={selected_metric: 'Overall_Performance'}, inplace=True)
    
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
        # Define Groups relative to threshold
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
                if size == threshold: 
                    return "Just Above Threshold (Diluted)"
                return "Large (Established)"
            return "Other"

        merged_df['Threshold Category'] = merged_df.apply(categorize_threshold, axis=1)
        
        # --- Create Labels for Plots ---
        def get_label(row):
            name = row['Community']
            overrides = {"Knights": "K", "McKnight": "MK", "Wolverines": "WL", "Southwest": "SW", "Springbank": "SB"}
            abbrev = overrides.get(name, name[:2].upper())
            season_short = row['Season'].split('-')[-1][-2:]
            return f"{abbrev}-{season_short} ({row['Age Category']})"

        merged_df['Label'] = merged_df.apply(get_label, axis=1)

        # --- Visualizations ---
        
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
        
        # Filter for relevant categories
        contrast_df = merged_df[merged_df['Threshold Category'].isin([
            "Just Below Threshold (1 Team)", 
            "Just Above Threshold (Diluted)",
            "Large (Established)"
        ])].copy()
        
        # Imports for manual plotting
        import plotly.graph_objects as go
        import numpy as np
        
        # Define Categories and Colors
        categories = ["Just Below Threshold (1 Team)", "Just Above Threshold (Diluted)", "Large (Established)"]
        colors = {
            "Just Below Threshold (1 Team)": "#2ca02c", 
            "Just Above Threshold (Diluted)": "#d62728", 
            "Large (Established)": "#1f77b4"
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
            
        # Add Scatter Points (Jittered with Labels)
        for cat in categories:
            cat_data = contrast_df[contrast_df['Threshold Category'] == cat]
            if cat_data.empty: continue

            fig_cliff.add_trace(go.Scatter(
                x=cat_data['X_Jitter'],
                y=cat_data['Overall_Performance'],
                mode='markers+text',
                text=cat_data['Label'],
                textposition='top center',
                marker=dict(color=colors[cat], size=6),
                name=cat,
                showlegend=False, # Legend already shown by Box
                hovertext=cat_data.apply(lambda row: f"{row['Community']} ({row['Season']})<br>Teams: {row['Total_Community_Teams']}<br>Tier 1: {row['Tier1_Count']}", axis=1),
                hoverinfo='text+y'
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

        # --- NEW VISUALIZATION: Community Performance Trends ---
        st.subheader("2. Community Performance Trends")
        st.markdown("Track the performance of individual communities over time.")
        
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
        
        # Add a base size so points with 0% aggressiveness are still visible
        trend_agg_df['Visual_Size'] = trend_agg_df['Tiering_Aggressiveness'] + 0.05
        
        fig_trend = px.scatter(
            trend_agg_df,
            x='Season',
            y='Overall_Performance',
            color='Community',
            size='Visual_Size',
            hover_data={
                'Visual_Size': False,
                'Tiering_Aggressiveness': ':.1%',
                'Total_Community_Teams': True,
                'Tier1_Count': True,
                'Season': True,
                'Overall_Performance': ':.3f'
            },
            title=f"Community Performance & Aggressiveness Trends (Aggregated)",
            labels={
                'Overall_Performance': f"Avg Community {selected_metric_label}",
                'Tiering_Aggressiveness': 'Aggressiveness'
            },
            size_max=25
        )
        
        # Connect dots with lines to show the trend
        fig_trend.update_traces(mode='lines+markers')
        
        st.plotly_chart(fig_trend, use_container_width=True)
        st.caption("ℹ️ **Bubble Size** represents **Tiering Aggressiveness**. Larger bubbles = Higher % of teams in Tier 1.")

    # 5. Data Table
    with st.expander("View Analysis Data"):
        st.dataframe(merged_df.sort_values(by='Total_Community_Teams'))

