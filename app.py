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
    
    # Age Category
    age_categories = sorted(df['Age Category'].unique().tolist())
    valid_ages = [age for age in ['U11', 'U13', 'U15', 'U18'] if age in age_categories]
    selected_age = st.sidebar.selectbox("Select Age Category", valid_ages, index=0)
    
    # Season Type
    season_types = df['Type'].unique().tolist()
    default_type = 'Regular' if 'Regular' in season_types else season_types[0]
    selected_type = st.sidebar.selectbox("Season Type", season_types, index=season_types.index(default_type) if default_type in season_types else 0)

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
        (df['Age Category'] == selected_age) &
        (df['Type'] == selected_type)
    ].copy()
    
    # 2. Identify Elite (AA/HADP) to exclude from Community Size Count
    def is_elite(league_name):
        name_upper = league_name.upper()
        if 'AA' in name_upper: return True
        if 'HADP' in name_upper: return True
        return False
        
    analysis_df['Is_Elite'] = analysis_df['League'].apply(is_elite)
    
    # 3. Calculate Community Size (Total Non-Elite Teams) per Season/Community
    # We use the full dataset (minus elite) to count total teams
    non_elite_df = analysis_df[~analysis_df['Is_Elite']].copy()
    
    community_sizes = non_elite_df.groupby(['Season', 'Community'])['Team'].nunique().reset_index()
    community_sizes.rename(columns={'Team': 'Total_Community_Teams'}, inplace=True)
    
    # 4. Identify Tier 1 Teams (for Threshold Logic)
    def is_tier_1(league_name):
        parsed = parse_tier_info(league_name)
        if parsed['tier'] == 1:
            if parsed['stream'] == 'NBC': return False
            return True
        return False
        
    analysis_df['Is_Tier_1'] = analysis_df['League'].apply(is_tier_1)
    
    # Calculate Tier 1 Count per Community/Season
    tier1_counts = analysis_df[analysis_df['Is_Tier_1']].groupby(['Season', 'Community'])['Team'].nunique().reset_index()
    tier1_counts.rename(columns={'Team': 'Tier1_Count'}, inplace=True)
    
    # 5. Calculate OVERALL Performance per Community/Season (Non-Elite)
    # This is the key change: We look at the average of ALL teams in the community
    overall_stats = non_elite_df.groupby(['Season', 'Community'])[selected_metric].mean().reset_index()
    overall_stats.rename(columns={selected_metric: 'Overall_Performance'}, inplace=True)
    
    # 6. Merge Data
    merged_df = pd.merge(community_sizes, tier1_counts, on=['Season', 'Community'], how='left')
    merged_df = pd.merge(merged_df, overall_stats, on=['Season', 'Community'], how='left')
    
    # Fill NaN Tier 1 Count with 0
    merged_df['Tier1_Count'] = merged_df['Tier1_Count'].fillna(0)
    merged_df.dropna(subset=['Total_Community_Teams'], inplace=True)
    
    # --- NEW LOGIC: Threshold Analysis ---
    
    # Identify the Threshold PER SEASON
    # Find the minimum community size that has fielded 2 Tier 1 teams for each season
    season_thresholds = merged_df[merged_df['Tier1_Count'] >= 2].groupby('Season')['Total_Community_Teams'].min().to_dict()
    
    if not season_thresholds:
        st.warning("Not enough data to identify the 2-team threshold (no communities with 2+ Tier 1 teams found).")
    else:
        # Define Groups relative to threshold
        def categorize_threshold(row):
            season = row['Season']
            if season not in season_thresholds:
                return "Other"
                
            threshold = int(season_thresholds[season])
            size = row['Total_Community_Teams']
            t1_count = row['Tier1_Count']
            
            if t1_count == 1:
                # Check if they are "Just Below" (Large 1-team associations)
                if size >= threshold - 3: 
                    return "Just Below Threshold (1 Team)"
                return "Small (1 Team)"
            elif t1_count >= 2:
                # Check if they are "Just Above" (Small 2-team associations)
                if size == threshold: 
                    return "Just Above Threshold (Diluted)"
                return "Large (Established)"
            return "Other"

        merged_df['Threshold Category'] = merged_df.apply(categorize_threshold, axis=1)
        
        # --- Create Labels for Plots ---
        def get_label(row):
            name = row['Community']
            
            # Specific Overrides
            overrides = {
                "Knights": "K",
                "McKnight": "MK",
                "Wolverines": "WL",
                "Southwest": "SW",
                "Springbank": "SB"
            }
            
            if name in overrides:
                abbrev = overrides[name]
            else:
                # Default Abbreviation Logic
                words = name.split()
                if len(words) > 1: abbrev = "".join([w[0] for w in words]).upper()
                else: abbrev = name[:2].upper()
            
            # Season Logic: 2024-2025 -> 25
            season_short = row['Season'].split('-')[-1][-2:]
            return f"{abbrev}-{season_short}"

        merged_df['Label'] = merged_df.apply(get_label, axis=1)

        # --- Visualizations ---
        
        # 1. The "Cliff" Comparison (Overall Performance)
        st.subheader("1. The 'Dilution Cliff' (Community-Wide)")
        
        # Display Thresholds
        st.markdown("### Dynamic Thresholds by Season")
        st.markdown("The size threshold for requiring 2 Tier 1 teams changes year-to-year based on Hockey Calgary rules.")
        
        threshold_df = pd.DataFrame(list(season_thresholds.items()), columns=['Season', 'Threshold (Teams)'])
        st.table(threshold_df.sort_values('Season', ascending=False))

        st.markdown(f"""
        Comparing the **Average Performance of ALL Teams** in the community.
        
        *   **Just Below Threshold**: 1-3 teams smaller than that season's threshold (1 Tier 1).
        *   **Just Above Threshold**: Exactly at that season's threshold (2 Tier 1s).
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

        # 2. Scatter: Size vs Overall Performance
        st.subheader("2. Size vs. Overall Performance")
        st.markdown("Does the entire community suffer when they cross the threshold?")
        
        merged_df['Tier 1 Teams'] = merged_df['Tier1_Count'].astype(str)
        
        try:
            import statsmodels
            fig_scatter = px.scatter(
                merged_df,
                x='Total_Community_Teams',
                y='Overall_Performance',
                color='Tier 1 Teams',
                symbol='Season',
                hover_data=['Community', 'Season', 'Tier1_Count'],
                trendline="lowess",
                title=f"Community-Wide {selected_metric_label} by Size",
                labels={'Total_Community_Teams': 'Total Community Teams', 'Overall_Performance': f"Avg Community {selected_metric_label}"}
            )
        except ImportError:
            fig_scatter = px.scatter(
                merged_df,
                x='Total_Community_Teams',
                y='Overall_Performance',
                color='Tier 1 Teams',
                hover_data=['Community', 'Season', 'Tier1_Count'],
                title=f"Community-Wide {selected_metric_label} by Size",
                labels={'Total_Community_Teams': 'Total Community Teams', 'Overall_Performance': f"Avg Community {selected_metric_label}"}
            )
            
        st.plotly_chart(fig_scatter, use_container_width=True)

        # --- NEW VISUALIZATION: Yearly Performance by Category ---
        st.subheader("3. Yearly Performance Trends")
        st.markdown(f"""
        Performance over time, categorized by community status relative to the threshold (**{threshold} teams**).
        *   <span style='color:#2ca02c'>**Single Tier 1 Team**</span>: Any size, but only 1 Tier 1 team.
        *   <span style='color:#bcbd22'>**Threshold Size ({threshold})**</span>: The specific size that forces the split to 2 teams.
        *   <span style='color:#1f77b4'>**Established (> {threshold})**</span>: Larger communities comfortably supporting 2+ teams.
        """, unsafe_allow_html=True)

        def categorize_yearly(row):
            size = row['Total_Community_Teams']
            t1_count = row['Tier1_Count']
            
            if t1_count == 1:
                return "Single Tier 1 Team"
            elif t1_count >= 2:
                if size == threshold:
                    return f"Threshold Size ({threshold})"
                elif size > threshold:
                    return "Established (> Threshold)"
            return "Other"

        merged_df['Yearly_Category'] = merged_df.apply(categorize_yearly, axis=1)
        
        # Filter out "Other"
        yearly_df = merged_df[merged_df['Yearly_Category'] != "Other"].copy()
        
        # Sort seasons
        yearly_df = yearly_df.sort_values('Season')

        fig_yearly = px.scatter(
            yearly_df,
            x='Season',
            y='Overall_Performance',
            color='Yearly_Category',
            text='Label',
            hover_data=['Community', 'Total_Community_Teams', 'Tier1_Count'],
            title=f"Community Performance by Season & Category",
            labels={'Overall_Performance': f"Avg Community {selected_metric_label}"},
            color_discrete_map={
                "Single Tier 1 Team": "#2ca02c", # Green
                f"Threshold Size ({threshold})": "#bcbd22", # Yellow
                "Established (> Threshold)": "#1f77b4" # Blue
            }
        )
        fig_yearly.update_traces(marker=dict(size=8, opacity=0.7), textposition='top center')
        st.plotly_chart(fig_yearly, use_container_width=True)

        # --- NEW VISUALIZATION: Tiering Aggressiveness ---
        st.subheader("4. Tiering Aggressiveness Analysis")
        st.markdown("""
        **Tiering Aggressiveness** = (Tier 1 Teams / Total Teams).
        
        This metric measures the percentage of a community's teams that are placed in Tier 1.
        *   **Higher %**: More aggressive placement (e.g., 20%).
        *   **Lower %**: More conservative placement (e.g., 8%).
        """)
        
        merged_df['Tiering_Aggressiveness'] = merged_df['Tier1_Count'] / merged_df['Total_Community_Teams']
        
        try:
            import statsmodels
            fig_agg = px.scatter(
                merged_df,
                x='Tiering_Aggressiveness',
                y='Overall_Performance',
                color='Threshold Category',
                size='Total_Community_Teams',
                text='Label',
                hover_data=['Community', 'Season', 'Tier1_Count', 'Total_Community_Teams'],
                trendline="ols",
                title=f"Impact of Tiering Aggressiveness on {selected_metric_label}",
                labels={
                    'Tiering_Aggressiveness': 'Tiering Aggressiveness (Tier 1 / Total Teams)', 
                    'Overall_Performance': f"Avg Community {selected_metric_label}"
                },
                color_discrete_map={
                    "Just Below Threshold (1 Team)": "#2ca02c", 
                    "Just Above Threshold (Diluted)": "#d62728", 
                    "Large (Established)": "#1f77b4"
                }
            )
        except (ImportError, TypeError):
            fig_agg = px.scatter(
                merged_df,
                x='Tiering_Aggressiveness',
                y='Overall_Performance',
                color='Threshold Category',
                size='Total_Community_Teams',
                text='Label',
                hover_data=['Community', 'Season', 'Tier1_Count', 'Total_Community_Teams'],
                title=f"Impact of Tiering Aggressiveness on {selected_metric_label}",
                labels={
                    'Tiering_Aggressiveness': 'Tiering Aggressiveness (Tier 1 / Total Teams)', 
                    'Overall_Performance': f"Avg Community {selected_metric_label}"
                },
                color_discrete_map={
                    "Just Below Threshold (1 Team)": "#2ca02c", 
                    "Just Above Threshold (Diluted)": "#d62728", 
                    "Large (Established)": "#1f77b4"
                }
            )
            
        fig_agg.update_traces(textposition='top center')
        fig_agg.update_layout(xaxis_tickformat='.1%')
        
        st.plotly_chart(fig_agg, use_container_width=True)

    # 5. Data Table
    with st.expander("View Analysis Data"):
        st.dataframe(merged_df.sort_values(by='Total_Community_Teams'))

