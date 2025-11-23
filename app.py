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
page = st.sidebar.radio("Navigation", ["Analytics", "Tiering Compliance"])

# Scraper Control
st.sidebar.header("Data Sync")
if st.sidebar.button("Run Scraper (Sync Data)"):
    with st.spinner("Scraping data from Hockey Calgary... This may take a minute."):
        # Capture stdout to show progress
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        
        try:
            sync_data(reset=True)
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

