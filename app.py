"""
Energy Maestro - Streamlit Application

A tool to help users explore the financial impact of adding
solar PV, batteries, and EVs to their household.
"""

import streamlit as st
import pandas as pd
import base64
from pathlib import Path


def get_logo_base64():
    """Read logo and return base64 encoded string."""
    logo_path = Path(__file__).parent / "img" / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

from src.data_loader import (
    load_customer_data,
    get_available_customers,
    load_tariffs,
    get_consumption_summary,
)
from src.assets import (
    PVSystem,
    Battery,
    EV,
    simulate_all_assets,
    get_self_sufficiency_metrics,
    PVSizingConfig,
    RoofType,
    Orientation,
    calculate_recommended_pv_size,
    ORIENTATION_FACTORS,
)
from src.billing import (
    calculate_all_tariffs,
    compare_scenarios,
    get_monthly_costs,
    find_best_tariff,
)
from src.charts import (
    create_bill_comparison_chart,
    create_savings_chart,
    create_load_profile_chart,
    create_daily_profile_chart,
    create_monthly_costs_chart,
    create_self_sufficiency_gauge,
    create_battery_soc_chart,
)
from src.chat import chat_with_bedrock


# Page configuration
st.set_page_config(
    page_title="Energy Maestro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main header styling - matching sidebar light theme */
    .main-header {
        background: linear-gradient(135deg, #e8f4fc 0%, #d4e8f5 50%, #c5dced 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border: 1px solid #b8d4e8;
    }
    .main-header h1 {
        color: #0f3460;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #2d4a6f;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Sidebar logo */
    .sidebar-logo {
        display: flex;
        justify-content: center;
        padding: 0 0 0 0;
    }
    .sidebar-logo img {
        height: 200px;
        width: auto;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #FFD93D;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.3rem;
    }
    
    /* Savings highlight */
    .savings-card {
        background: linear-gradient(145deg, #d4edda 0%, #c3e6cb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        border: 2px solid #28a745;
    }
    .savings-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #155724;
    }
    .savings-label {
        color: #155724;
        font-size: 0.9rem;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #f8f9fa 0%, transparent 100%);
        padding: 0.8rem 1rem;
        border-left: 3px solid #FFD93D;
        margin: 1.5rem 0 1rem 0;
        font-weight: 600;
        color: #1a1a2e;
    }
    
    /* Sidebar styling - light theme for better readability */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e8f4fc 0%, #d4e8f5 50%, #c5dced 100%);
        min-width: 380px !important;
        width: 380px !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 380px !important;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #1a1a2e;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #0f3460 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h5 {
        color: #16213e !important;
    }
    section[data-testid="stSidebar"] label {
        color: #0f3460 !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stCaption {
        color: #2d4a6f !important;
    }
    section[data-testid="stSidebar"] p {
        color: #1a1a2e !important;
    }
    
    /* Toggle styling */
    .stCheckbox label {
        font-weight: 500;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Better chart container */
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* AI Chat button - circular goldish orange */
    .chat-button-container button {
        background: linear-gradient(135deg, #F4A020 0%, #E8850C 100%) !important;
        border: none !important;
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        padding: 0 !important;
        font-size: 1.5rem !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(244, 160, 32, 0.4) !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .chat-button-container button:hover {
        background: linear-gradient(135deg, #FFB830 0%, #F4A020 100%) !important;
        box-shadow: 0 6px 20px rgba(244, 160, 32, 0.5) !important;
        transform: scale(1.05) !important;
    }
    .chat-button-container button p {
        margin: 0 !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Header with chat button
    header_col, chat_btn_col = st.columns([6, 1])
    
    with header_col:
        st.markdown("""
        <div class="main-header">
            <h1>Energy Maestro</h1>
            <p>Explore how solar panels, batteries, and EVs could transform your energy costs</p>
        </div>
        """, unsafe_allow_html=True)
    
    with chat_btn_col:
        # Initialize chat state early
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        if "chat_open" not in st.session_state:
            st.session_state.chat_open = False
        
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        chat_icon = "✕" if st.session_state.chat_open else "AI Assistant 💬"
        st.markdown('<div class="chat-button-container">', unsafe_allow_html=True)
        if st.button(chat_icon, key="toggle_chat_top", help="AI Energy Advisor"):
            st.session_state.chat_open = not st.session_state.chat_open
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Load configuration
    tariffs = load_tariffs()
    customers = get_available_customers()
    
    # Sidebar - Configuration
    with st.sidebar:
        # Logo at top of sidebar
        logo_b64 = get_logo_base64()
        if logo_b64:
            st.markdown(f"""
            <div class="sidebar-logo">
                <img src="data:image/png;base64,{logo_b64}" alt="Energy Maestro Logo">
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("## 🏠 Customer Selection")
        
        customer_id = st.selectbox(
            "Select Household",
            options=list(customers.keys()),
            format_func=lambda x: customers[x],
            help="Choose a customer profile to analyze"
        )
        
        # Load customer data early to use in PV wizard
        consumption_df = load_customer_data(customer_id)
        consumption_summary = get_consumption_summary(consumption_df)
        yearly_consumption_kwh = consumption_summary['total_annual_kwh']
        
        st.caption(f"📊 Annual consumption: **{yearly_consumption_kwh:,.0f} kWh**")
        
        st.markdown("---")
        st.markdown("## ☀️ Solar PV System")
        
        pv_enabled = st.toggle("Enable PV System", value=False)
        
        if pv_enabled:
            pv_mode = st.radio(
                "Configuration Mode",
                options=["🏠 Guided Wizard", "⚙️ Advanced"],
                horizontal=True,
                help="Wizard helps calculate optimal size; Advanced lets you set kWp directly"
            )
            
            if pv_mode == "🏠 Guided Wizard":
                st.markdown("##### 🏗️ Roof Configuration")
                
                # Roof surface
                pv_roof_surface = st.slider(
                    "Roof Surface (m²)",
                    min_value=10,
                    max_value=200,
                    value=50,
                    step=5,
                    help="Total usable roof area for solar panels"
                )
                
                # Roof type
                roof_type_options = {
                    "Gable (pitched, 2 sides)": RoofType.GABLE,
                    "Hip (4-sided pitched)": RoofType.HIP,
                    "Mono (single slope)": RoofType.MONO,
                    "Flat": RoofType.FLAT,
                }
                pv_roof_type_label = st.selectbox(
                    "House/Roof Type",
                    options=list(roof_type_options.keys()),
                    help="Type of roof structure"
                )
                pv_roof_type = roof_type_options[pv_roof_type_label]
                
                # Use both sides (only for gable)
                pv_use_both_sides = False
                if pv_roof_type == RoofType.GABLE:
                    pv_use_both_sides = st.checkbox(
                        "Use both sides of roof?",
                        value=False,
                        help="Install panels on both sides of gable roof"
                    )
                
                # Roof inclination
                pv_inclination = st.slider(
                    "Roof Inclination (°)",
                    min_value=0,
                    max_value=60,
                    value=30,
                    step=5,
                    help="Angle of roof from horizontal (optimal: 30-35°)"
                )
                
                # Orientation
                orientation_options = {
                    "🧭 South": Orientation.SOUTH,
                    "↗️ South-East": Orientation.SOUTH_EAST,
                    "↙️ South-West": Orientation.SOUTH_WEST,
                    "➡️ East": Orientation.EAST,
                    "⬅️ West": Orientation.WEST,
                    "↗️ North-East": Orientation.NORTH_EAST,
                    "↙️ North-West": Orientation.NORTH_WEST,
                    "⬆️ North": Orientation.NORTH,
                }
                pv_orientation_label = st.selectbox(
                    "Roof Orientation",
                    options=list(orientation_options.keys()),
                    help="Direction your roof faces (align with map)"
                )
                pv_orientation = orientation_options[pv_orientation_label]
                
                # Calculate recommended size using actual consumption data and roof config
                pv_config = PVSizingConfig(
                    roof_surface_m2=float(pv_roof_surface),
                    roof_type=pv_roof_type,
                    use_both_sides=pv_use_both_sides,
                    roof_inclination=pv_inclination,
                    orientation=pv_orientation,
                    yearly_consumption_kwh=yearly_consumption_kwh,
                )
                
                sizing_result = calculate_recommended_pv_size(pv_config)
                
                # Display recommendation
                st.markdown("##### 📊 Recommendation")
                st.success(f"**Recommended: {sizing_result['recommended_kwp']} kWp**")
                
                rec_col1, rec_col2 = st.columns(2)
                with rec_col1:
                    st.caption(f"Max from roof: {sizing_result['max_from_roof_kwp']} kWp")
                    st.caption(f"Usable area: {sizing_result['usable_roof_area_m2']} m²")
                with rec_col2:
                    st.caption(f"Est. production: {sizing_result['estimated_annual_production_kwh']:,.0f} kWh/yr")
                    st.caption(f"Coverage: ~{sizing_result['coverage_percent']}%")
                
                # Efficiency breakdown
                with st.expander("Efficiency Details"):
                    st.write(f"Orientation factor: {sizing_result['orientation_factor']}")
                    st.write(f"Inclination factor: {sizing_result['inclination_factor']}")
                    st.write(f"Combined efficiency: {sizing_result['efficiency_factor']}")
                
                # Allow adjustment from recommendation
                pv_capacity = st.slider(
                    "Adjust System Size (kWp)",
                    min_value=2.0,
                    max_value=30.0,
                    value=float(sizing_result['recommended_kwp']),
                    step=0.5,
                    help="Adjust from recommendation if needed"
                )
                
                pv_efficiency_factor = sizing_result['efficiency_factor']
            
            else:  # Advanced mode
                st.markdown("##### ⚙️ Direct Configuration")
                
                pv_capacity = st.slider(
                    "System Size (kWp)",
                    min_value=2.0,
                    max_value=30.0,
                    value=6.0,
                    step=0.5,
                    help="Set your PV system capacity directly (up to 30 kWp)"
                )
                
                # Orientation for advanced users
                adv_orientation_options = {
                    "South (100%)": Orientation.SOUTH,
                    "South-East (95%)": Orientation.SOUTH_EAST,
                    "South-West (95%)": Orientation.SOUTH_WEST,
                    "East (80%)": Orientation.EAST,
                    "West (80%)": Orientation.WEST,
                    "North-East (55%)": Orientation.NORTH_EAST,
                    "North-West (55%)": Orientation.NORTH_WEST,
                    "North (45%)": Orientation.NORTH,
                }
                adv_orientation_label = st.selectbox(
                    "Orientation",
                    options=list(adv_orientation_options.keys()),
                    help="Roof orientation affects efficiency"
                )
                pv_orientation = adv_orientation_options[adv_orientation_label]
                
                pv_inclination = st.slider(
                    "Inclination (°)",
                    min_value=0,
                    max_value=90,
                    value=30,
                    step=5,
                    help="Roof angle (optimal: 30-35°)"
                )
                
                pv_efficiency_factor = ORIENTATION_FACTORS.get(pv_orientation, 1.0)
                
                st.caption(f"Efficiency factor: {pv_efficiency_factor:.0%}")
                est_production = pv_capacity * 950 * pv_efficiency_factor
                st.caption(f"Est. annual production: {est_production:,.0f} kWh")
        else:
            pv_capacity = 0.0
            pv_efficiency_factor = 1.0
            pv_orientation = Orientation.SOUTH
            pv_inclination = 30
        
        st.markdown("---")
        st.markdown("## 🔋 Battery Storage")
        
        # Battery only makes sense with PV - it charges from excess solar
        if not pv_enabled:
            st.caption("⚠️ *Enable PV system first to add battery storage*")
            battery_enabled = False
            battery_capacity = 10.0
        else:
            battery_enabled = st.toggle("Enable Battery", value=False)
            battery_capacity = st.slider(
                "Capacity (kWh)",
                min_value=5.0,
                max_value=20.0,
                value=10.0,
                step=1.0,
                disabled=not battery_enabled,
                help="Typical home batteries: 5-15 kWh. Charges from excess solar during the day."
            )
        
        st.markdown("---")
        st.markdown("## 🚗 Electric Vehicle")
        
        ev_enabled = st.toggle("Enable EV", value=False)
        
        ev_battery_capacity = st.slider(
            "Battery Capacity (kWh)",
            min_value=30.0,
            max_value=100.0,
            value=60.0,
            step=5.0,
            disabled=not ev_enabled,
            help="EV battery size (e.g., Tesla Model 3: 60kWh, Model Y: 75kWh)"
        )
        
        # Charging configuration (expandable)
        if ev_enabled:
            with st.expander("⚡ Charging Configuration"):
                ev_charging_power = st.select_slider(
                    "Charging Power (kW)",
                    options=[2.3, 3.7, 4.0, 7.4, 11.0, 22.0],
                    value=4.0,
                    help="Home charger power (typical: 3.7-4kW single-phase, 11kW three-phase)"
                )
                
                st.markdown("##### 🕐 Charging Schedule")
                ev_charge_start = st.slider(
                    "Start Hour", 0, 23, 18,
                    help="When EV arrives home and starts charging"
                )
                ev_charge_end = st.slider(
                    "End Hour", 0, 23, 7,
                    help="When charging window ends"
                )
                
                st.markdown("##### 🔋 Battery State")
                st.caption("EV arrives home at **40% SOC** and charges to **80%** each day")
                
                # Calculate and show charging info
                energy_per_session = ev_battery_capacity * 0.40  # 40% to 80% = 40%
                charging_time_hours = energy_per_session / ev_charging_power
                st.info(f"📊 Daily charge: **{energy_per_session:.1f} kWh** | "
                       f"Time to charge: **{charging_time_hours:.1f} hours**")
        else:
            ev_charge_start = 18
            ev_charge_end = 7
            ev_charging_power = 4.0
        
    
    # Create asset configurations (consumption_df and consumption_summary loaded in sidebar)
    pv = PVSystem(
        capacity_kwp=pv_capacity if pv_enabled else 0,
        enabled=pv_enabled,
        orientation=pv_orientation if pv_enabled else Orientation.SOUTH,
        roof_inclination=pv_inclination if pv_enabled else 30,
        efficiency_factor=pv_efficiency_factor if pv_enabled else 1.0,
    )
    battery = Battery(
        capacity_kwh=battery_capacity if battery_enabled else 0,
        enabled=battery_enabled
    )
    ev = EV(
        battery_capacity_kwh=ev_battery_capacity if ev_enabled else 0,
        enabled=ev_enabled,
        charging_power_kw=ev_charging_power if ev_enabled else 7.4,
        charging_start_hour=ev_charge_start,
        charging_end_hour=ev_charge_end,
        starting_soc_pct=0.40,
        target_soc_pct=0.80,
    )
    
    # Run simulation
    baseline_df = consumption_df.copy()
    baseline_df["grid_import_kwh"] = baseline_df["consumption_kwh"]
    baseline_df["grid_export_kwh"] = 0.0
    
    simulated_df = simulate_all_assets(consumption_df, pv, battery, ev, tariffs)
    
    # Calculate costs
    baseline_costs = calculate_all_tariffs(baseline_df, tariffs)
    with_assets_costs = calculate_all_tariffs(simulated_df, tariffs)
    comparison = compare_scenarios(baseline_costs, with_assets_costs)
    
    # Get self-sufficiency metrics
    metrics = get_self_sufficiency_metrics(simulated_df)
    
    # Find best tariff
    best_tariff_id = find_best_tariff(with_assets_costs)
    best_tariff = with_assets_costs[best_tariff_id]
    
    # Main content
    # Row 1: Key Metrics
    st.markdown('<div class="section-header">📊 Consumption Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{consumption_summary['total_annual_kwh']:,.0f}</div>
            <div class="metric-label">Annual kWh</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{consumption_summary['avg_daily_kwh']:.1f}</div>
            <div class="metric-label">Avg Daily kWh</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{consumption_summary['peak_power_kw']:.1f}</div>
            <div class="metric-label">Peak Power kW</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{consumption_summary['days_of_data']}</div>
            <div class="metric-label">Days of Data</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Row 2: Bill Comparison and Savings
    st.markdown('<div class="section-header">💰 Cost Analysis</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_comparison = create_bill_comparison_chart(baseline_costs, with_assets_costs)
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    with col2:
        # Best tariff recommendation
        st.markdown(f"""
        <div class="savings-card">
            <div class="savings-label">Best Tariff With Your Assets</div>
            <div class="savings-value">{best_tariff['tariff_name']}</div>
            <div style="font-size: 1.4rem; color: #155724; margin-top: 0.5rem;">
                €{best_tariff['net_cost']:,.0f}/year
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Savings summary
        if any([pv_enabled, battery_enabled, ev_enabled]):
            max_savings = max(c["annual_savings"] for c in comparison.values())
            best_savings_tariff = max(comparison.items(), key=lambda x: x[1]["annual_savings"])
            
            if max_savings > 0:
                st.markdown(f"""
                <div class="savings-card">
                    <div class="savings-label">Maximum Annual Savings</div>
                    <div class="savings-value">€{max_savings:,.0f}</div>
                    <div style="font-size: 0.9rem; color: #155724; margin-top: 0.5rem;">
                        with {best_savings_tariff[1]['tariff_name']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Savings breakdown
    if any([pv_enabled, battery_enabled, ev_enabled]):
        fig_savings = create_savings_chart(comparison)
        st.plotly_chart(fig_savings, use_container_width=True)
    
    # Monthly costs breakdown
    monthly_df = get_monthly_costs(simulated_df, tariffs)
    fig_monthly = create_monthly_costs_chart(monthly_df)
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Row 3: Self-Sufficiency Metrics (only if PV enabled)
    if pv_enabled:
        st.markdown('<div class="section-header">🔋 Self-Sufficiency Metrics</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_gauges = create_self_sufficiency_gauge(metrics)
            st.plotly_chart(fig_gauges, use_container_width=True)
        
        with col2:
            metric_col1, metric_col2 = st.columns(2)
            
            with metric_col1:
                st.metric(
                    "PV Generation",
                    f"{metrics['total_pv_generation_kwh']:,.0f} kWh",
                    help="Total annual solar generation"
                )
                st.metric(
                    "Grid Import",
                    f"{metrics['grid_import_kwh']:,.0f} kWh",
                    delta=f"-{consumption_summary['total_annual_kwh'] - metrics['grid_import_kwh']:,.0f}",
                    delta_color="inverse",
                    help="Energy bought from grid"
                )
            
            with metric_col2:
                st.metric(
                    "Grid Export",
                    f"{metrics['grid_export_kwh']:,.0f} kWh",
                    help="Excess energy sold to grid"
                )
                
                # Show battery contribution if enabled
                if battery_enabled and metrics.get('battery_discharged_kwh', 0) > 0:
                    st.metric(
                        "🔋 Battery Used",
                        f"{metrics['battery_discharged_kwh']:,.0f} kWh",
                        help="Energy provided by battery (reduces grid import)"
                    )
    
    # Row 4: Load Profiles
    st.markdown('<div class="section-header">📈 Energy Profiles</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Weekly View", "Daily Average"])
    
    with tab1:
        # Date selector for load profile
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input(
                "Start Date",
                value=simulated_df.index.min().date(),
                min_value=simulated_df.index.min().date(),
                max_value=simulated_df.index.max().date(),
            )
        with date_col2:
            end_date = st.date_input(
                "End Date",
                value=min(
                    simulated_df.index.min().date() + pd.Timedelta(days=7),
                    simulated_df.index.max().date()
                ),
                min_value=simulated_df.index.min().date(),
                max_value=simulated_df.index.max().date(),
            )
        
        fig_load = create_load_profile_chart(
            simulated_df,
            date_range=(pd.Timestamp(start_date), pd.Timestamp(end_date) + pd.Timedelta(days=1))
        )
        st.plotly_chart(fig_load, use_container_width=True)
        
        # Battery SOC if enabled
        if battery_enabled:
            fig_soc = create_battery_soc_chart(
                simulated_df,
                date_range=(pd.Timestamp(start_date), pd.Timestamp(end_date) + pd.Timedelta(days=1))
            )
            if fig_soc.data:
                st.plotly_chart(fig_soc, use_container_width=True)
    
    with tab2:
        fig_daily = create_daily_profile_chart(simulated_df)
        st.plotly_chart(fig_daily, use_container_width=True)
    
    # Footer with tariff details
    st.markdown('<div class="section-header">📋 Tariff Details</div>', unsafe_allow_html=True)
    
    with st.expander("View Tariff Configuration"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Dynamic Tariff**")
            st.write(f"Base fee: €{tariffs['dynamic']['base_fee_monthly']}/month")
            st.write("Prices: Real-time spot market")
            feed_in = tariffs['dynamic'].get('feed_in_tariff', 0)
            st.write(f"Feed-in: €{feed_in}/kWh")
        
        with col2:
            st.markdown("**Fixed 3-Year**")
            st.write(f"Base fee: €{tariffs['fixed_3year']['base_fee_monthly']}/month")
            st.write(f"Rate: €{tariffs['fixed_3year']['rate']}/kWh")
            feed_in = tariffs['fixed_3year'].get('feed_in_tariff', 0)
            st.write(f"Feed-in: {'€' + str(feed_in) + '/kWh' if feed_in else 'None'}")
        
        with col3:
            st.markdown("**Day/Night Tariff**")
            st.write(f"Base fee: €{tariffs['daily_fix']['base_fee_monthly']}/month")
            day_start = tariffs['daily_fix'].get('day_start_hour', 6)
            day_end = tariffs['daily_fix'].get('day_end_hour', 22)
            st.write(f"Day ({day_start:02d}-{day_end:02d}h): €{tariffs['daily_fix']['day_rate']}/kWh")
            st.write(f"Night: €{tariffs['daily_fix']['night_rate']}/kWh")
    
    # ==================== AI Chat Panel (toggle from top button) ====================
    # Build page context for the AI
    page_context = {
        "customer_id": customer_id,
        "customer_name": customers.get(customer_id, customer_id),
        "consumption_summary": consumption_summary,
        "pv_enabled": pv_enabled,
        "pv_capacity": pv_capacity if pv_enabled else 0,
        "battery_enabled": battery_enabled,
        "battery_capacity": battery_capacity if battery_enabled else 0,
        "ev_enabled": ev_enabled,
        "ev_battery_kwh": ev_battery_capacity if ev_enabled else 0,
        "ev_charging_power_kw": ev_charging_power if ev_enabled else 0,
        "best_tariff": best_tariff.get("tariff_name", ""),
        "metrics": metrics if pv_enabled else {},
    }
    
    # Show chat panel when open (button is at the top of the page)
    if st.session_state.chat_open:
        st.markdown("---")
        st.markdown("### 🤖 AI Energy Advisor")
        st.caption("Ask me about your energy data, tariffs, or recommendations!")
        
        chat_container = st.container(height=350)
        
        with chat_container:
            if not st.session_state.chat_messages:
                with st.chat_message("assistant"):
                    st.markdown("👋 Hi! I'm your Energy Advisor. Ask me anything about your energy setup, tariffs, or how to save money!")
            
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask about your energy...", key="main_chat"):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            with st.spinner("Thinking..."):
                response = chat_with_bedrock(st.session_state.chat_messages, page_context)
            
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        if st.session_state.chat_messages:
            if st.button("🗑️ Clear Chat", key="clear_main_chat"):
                st.session_state.chat_messages = []
                st.rerun()
        
        st.markdown("---")


if __name__ == "__main__":
    main()

