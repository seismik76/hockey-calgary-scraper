import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from scraper import sync_data
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
page = st.sidebar.radio("Navigation", ["Analytics", "Tiering Compliance", "Community Size Analysis", "Tier 1 Dilution Analysis"])

# Scraper Control
st.sidebar.header("Data Sync")
if st.sidebar.button("Run Scraper (Sync Data)"):
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    
    def update_progress(pct, msg):
        progress_bar.progress(pct)
        status_text.text(msg)

    with st.spinner("Scraping data from Hockey Calgary... This may take a minute."):
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

elif page == "Tiering Compliance":
    st.header("📋 Tiering Compliance (Alberta One)")
    st.markdown("Comparison of actual community tiering vs. Alberta One Standardized Tiering Grids.")
    
    # Filters
    st.sidebar.header("Compliance Filters")
    
    # Season (Single)
    all_seasons = sorted(df['Season'].unique().tolist(), reverse=True)
    selected_season = st.sidebar.selectbox("Select Season", all_seasons)
    
    # Age Category (Single)
    age_categories = sorted(df['Age Category'].unique().tolist())
    valid_ages = [age for age in ['U11', 'U13', 'U15', 'U18'] if age in age_categories]
    selected_age = st.sidebar.selectbox("Select Age Category", valid_ages)
    
    # Community (Multi)
    all_communities = sorted(df['Community'].unique().tolist())
    selected_communities = st.sidebar.multiselect("Select Communities", all_communities, default=all_communities[:5])
    
    if not selected_communities:
        st.warning("Please select at least one community.")
        st.stop()
        
    # Filter Data
    # We need ALL teams for the selected communities in the selected season/age
    # We should filter by Type='Regular' usually, or 'Seeding'?
    # Tiering grids usually apply to the start of the season (Seeding/Regular).
    # Let's use 'Regular' as default, but maybe allow user to choose?
    # Actually, 'Seeding' is where initial placement happens.
    # But our data might have 'Regular' populated more reliably.
    # Let's try to find 'Regular' first.
    
    season_types = df['Type'].unique().tolist()
    # Prefer Regular, then Seeding
    default_type = 'Regular' if 'Regular' in season_types else season_types[0]
    selected_type = st.sidebar.selectbox("Season Type", season_types, index=season_types.index(default_type) if default_type in season_types else 0)
    
    compliance_data = df[
        (df['Season'] == selected_season) &
        (df['Age Category'] == selected_age) &
        (df['Community'].isin(selected_communities)) &
        (df['Type'] == selected_type)
    ].copy()
    
    if compliance_data.empty:
        st.warning(f"No data found for {selected_season} {selected_age} ({selected_type}).")
        st.stop()
        
    # Process each community
    for community in selected_communities:
        comm_df = compliance_data[compliance_data['Community'] == community]
        
        if comm_df.empty:
            continue
            
        st.subheader(f"{community}")
        
        tab_compliance, tab_raw = st.tabs(["Compliance", "Raw Data"])
        
        with tab_compliance:
            # Parse Tiers
            teams_info = []
            for _, row in comm_df.iterrows():
                parsed = parse_tier_info(row['League'])
                if parsed['tier'] is not None:
                    teams_info.append({
                        'team': row['Team'],
                        'tier': parsed['tier'],
                        'stream': parsed['stream'],
                        'league': row['League']
                    })
            
            if not teams_info:
                st.info("Could not parse tier information from league names.")
                continue
                
            total_teams = len(teams_info)
            st.write(f"**Total Teams:** {total_teams}")
            
            # Calculate Expected
            if selected_age in ['U11', 'U13']:
                # Separate AA/HADP from Tier 1-6
                aa_teams = [t for t in teams_info if t['tier'] == 'AA']
                tiered_teams = [t for t in teams_info if isinstance(t['tier'], int)]
                
                n_aa = len(aa_teams)
                n_tiered = len(tiered_teams)
                
                st.markdown(f"**AA/HADP Teams:** {n_aa}")
                if n_aa == 0:
                    st.warning("⚠️ No AA/HADP team found. (Check if required for this community size)")
                else:
                    st.success(f"✅ Found {n_aa} AA/HADP team(s).")
                
                st.markdown(f"**Tiered Teams (1-6):** {n_tiered}")
                
                if n_tiered > 0:
                    expected = get_u11_u13_distribution(n_tiered)
                    
                    # Count Actual
                    actual_counts = {i: 0 for i in range(1, 7)}
                    for t in tiered_teams:
                        if t['tier'] in actual_counts:
                            actual_counts[t['tier']] += 1
                        else:
                            # Handle tiers > 6 or 0?
                            pass
                    
                    # Create Comparison Table
                    comp_data = []
                    for i in range(1, 7):
                        exp = expected.get(i, 0)
                        act = actual_counts.get(i, 0)
                        diff = act - exp
                        status = "✅" if diff == 0 else ("⚠️" if abs(diff) == 1 else "❌")
                        
                        comp_data.append({
                            "Tier": f"Tier {i}",
                            "Expected": exp,
                            "Actual": act,
                            "Difference": diff,
                            "Status": status
                        })
                        
                    st.table(pd.DataFrame(comp_data))
                else:
                    st.info("No teams in Tiers 1-6 to analyze against grid.")
                
            elif selected_age in ['U15', 'U18']:
                # Split BC / NBC
                bc_teams = [t for t in teams_info if t['stream'] == 'BC']
                nbc_teams = [t for t in teams_info if t['stream'] == 'NBC']
                
                n_bc = len(bc_teams)
                n_nbc = len(nbc_teams)
                
                exp_bc, exp_nbc = get_u15_u18_split(total_teams)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Stream Split")
                    st.write(f"**Body Checking:** Actual {n_bc} vs Expected {exp_bc}")
                    st.write(f"**Non-Body Checking:** Actual {n_nbc} vs Expected {exp_nbc}")
                
                with col2:
                    st.markdown("#### Tiering Detail")
                    
                    # BC Tiering
                    if n_bc > 0:
                        exp_bc_tiers = get_u15_u18_tier_distribution(n_bc)
                        act_bc_tiers = {1:0, 2:0, 3:0}
                        for t in bc_teams:
                            if t['tier'] in act_bc_tiers: act_bc_tiers[t['tier']] += 1
                        
                        st.write("**Body Checking Tiers**")
                        bc_data = []
                        for i in range(1, 4):
                            e = exp_bc_tiers.get(i, 0)
                            a = act_bc_tiers.get(i, 0)
                            bc_data.append({"Tier": i, "Exp": e, "Act": a, "Diff": a-e})
                        st.dataframe(pd.DataFrame(bc_data), hide_index=True)

                    # NBC Tiering
                    if n_nbc > 0:
                        exp_nbc_tiers = get_u15_u18_tier_distribution(n_nbc)
                        act_nbc_tiers = {1:0, 2:0, 3:0}
                        for t in nbc_teams:
                            # Map NBC tiers? Usually NBC 1, 2, 3 are just 1, 2, 3 in our parsed logic
                            if t['tier'] in act_nbc_tiers: act_nbc_tiers[t['tier']] += 1
                        
                        st.write("**Non-Body Checking Tiers**")
                        nbc_data = []
                        for i in range(1, 4):
                            e = exp_nbc_tiers.get(i, 0)
                            a = act_nbc_tiers.get(i, 0)
                            nbc_data.append({"Tier": i, "Exp": e, "Act": a, "Diff": a-e})
                        st.dataframe(pd.DataFrame(nbc_data), hide_index=True)
        
        with tab_raw:
            st.dataframe(
                comm_df,
                column_config={
                    "Source": st.column_config.LinkColumn("Source URL")
                }
            )

elif page == "Community Size Analysis":
    st.header("📊 Community Size vs. Performance Analysis")
    st.markdown("""
    This analysis explores the relationship between the **size of a community** (number of teams fielded) 
    and their **performance** (Win %, Points %, Goal Differential).
    
    **Methodology:**
    *   **Size:** Count of teams fielded by a community in a specific Season and Age Category.
    *   **Exclusions:** AA and HADP teams are excluded from the count and performance metrics.
    *   **Inclusions:** U15/U18 counts include both Body Contact (BC) and Non-Body Contact (NBC) streams.
    """)
    
    # --- Filters ---
    st.sidebar.header("Analysis Filters")
    
    # Age Category (Single Select for clarity in scatter plot)
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
    # Filter by Age and Type first
    analysis_df = df[
        (df['Age Category'] == selected_age) &
        (df['Type'] == selected_type)
    ].copy()
    
    # 2. Exclude AA and HADP
    # Identify AA/HADP leagues
    # Logic: Look for "AA" or "HADP" in League Name. 
    # Note: Some leagues might be "U11 HADP", "U13 AA", "U15 AA", "U18 AA"
    # Be careful not to exclude "Haida" or similar if that existed (unlikely).
    # Also exclude "Elite" or "Quadrant" if they appear here (usually they are separate communities like 'Buffaloes', but good to be safe).
    
    def is_elite(league_name):
        name_upper = league_name.upper()
        if 'AA' in name_upper: return True
        if 'HADP' in name_upper: return True
        return False
        
    analysis_df['Is_Elite'] = analysis_df['League'].apply(is_elite)
    
    # Filter out Elite
    filtered_df = analysis_df[~analysis_df['Is_Elite']].copy()
    
    if filtered_df.empty:
        st.warning("No data available after filtering AA/HADP.")
        st.stop()
        
    # 3. Group by Season + Community to calculate Size and Performance
    # We want one point per Community per Season
    
    grouped = filtered_df.groupby(['Season', 'Community']).agg(
        Team_Count=('Team', 'nunique'),
        Performance=(selected_metric, 'mean')
    ).reset_index()
    
    # 4. Binning Logic
    # User defined bins: <=8, 9, 10, >10
    def categorize_size(count):
        if count <= 8: return 'Small (<=8)'
        if count == 9: return 'Medium (9)'
        if count == 10: return 'Large (10)'
        return 'Mega (>10)'
        
    grouped['Size Category'] = grouped['Team_Count'].apply(categorize_size)
    
    # --- Visualizations ---
    
    # 1. Scatter Plot: Size vs Performance
    st.subheader(f"Scatter Plot: Community Size vs {selected_metric_label}")
    
    # Add a trendline (OLS)
    # Plotly Express trendline requires statsmodels
    try:
        import statsmodels
        fig_scatter = px.scatter(
            grouped,
            x='Team_Count',
            y='Performance',
            color='Size Category', # Color by size category to see clusters
            symbol='Season', # Different shapes for seasons
            hover_data=['Community', 'Season'],
            trendline="ols",
            title=f"{selected_metric_label} by Community Size ({selected_age})",
            labels={'Team_Count': 'Number of Teams (Size)', 'Performance': selected_metric_label},
            category_orders={'Size Category': ['Small (<=8)', 'Medium (9)', 'Large (10)', 'Mega (>10)']}
        )
    except ImportError:
        st.info("Install 'statsmodels' to see trendlines.")
        fig_scatter = px.scatter(
            grouped,
            x='Team_Count',
            y='Performance',
            color='Size Category',
            hover_data=['Community', 'Season'],
            title=f"{selected_metric_label} by Community Size ({selected_age})",
            labels={'Team_Count': 'Number of Teams (Size)', 'Performance': selected_metric_label}
        )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 2. Box Plot by Size Category
    st.subheader("Distribution by Size Category")
    
    # Order categories
    category_order = ['Small (<=8)', 'Medium (9)', 'Large (10)', 'Mega (>10)']
    
    fig_box = px.box(
        grouped,
        x='Size Category',
        y='Performance',
        color='Size Category',
        category_orders={'Size Category': category_order},
        points="all", # Show all points
        hover_data=['Community', 'Season'],
        title=f"{selected_metric_label} Distribution by Community Size",
        labels={'Performance': selected_metric_label}
    )
    st.plotly_chart(fig_box, use_container_width=True)
    
    # 3. Correlation Stats
    st.subheader("Statistical Correlation")
    correlation = grouped['Team_Count'].corr(grouped['Performance'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Correlation Coefficient (r)", f"{correlation:.3f}")
        if abs(correlation) < 0.3:
            st.caption("Weak or no correlation.")
        elif abs(correlation) < 0.7:
            st.caption("Moderate correlation.")
        else:
            st.caption("Strong correlation.")
            
    with col2:
        st.markdown("""
        *   **Positive r**: Larger communities tend to perform better.
        *   **Negative r**: Larger communities tend to perform worse.
        *   **Near 0**: No linear relationship.
        """)

    # 4. Data Table
    st.subheader("Analysis Data")
    with st.expander("View Data Table"):
        st.dataframe(grouped.sort_values(by='Team_Count', ascending=False))

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
    
    # Identify the Threshold
    # Find the minimum community size that has ever fielded 2 Tier 1 teams in this dataset
    min_size_2_teams = merged_df[merged_df['Tier1_Count'] >= 2]['Total_Community_Teams'].min()
    
    if pd.isna(min_size_2_teams):
        st.warning("Not enough data to identify the 2-team threshold (no communities with 2+ Tier 1 teams found).")
    else:
        threshold = int(min_size_2_teams)
        
        # Define Groups relative to threshold
        def categorize_threshold(row):
            size = row['Total_Community_Teams']
            t1_count = row['Tier1_Count']
            
            if t1_count == 1:
                # Check if they are "Just Below" (Large 1-team associations)
                if size >= threshold - 3: 
                    return "Just Below Threshold (1 Team)"
                return "Small (1 Team)"
            elif t1_count >= 2:
                # Check if they are "Just Above" (Small 2-team associations)
                if size <= threshold + 3: 
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
        st.markdown(f"""
        Comparing the **Average Performance of ALL Teams** in the community.
        
        *   **Just Below Threshold**: {threshold-3}-{threshold-1} teams (1 Tier 1). Talent is concentrated.
        *   **Just Above Threshold**: {threshold}-{threshold+3} teams (2 Tier 1s). Talent is diluted across all tiers.
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
            title=f"Community-Wide Performance Drop at Threshold ({threshold} Teams)",
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

