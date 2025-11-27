"""
Energy Asset Simulator - Streamlit Application

A tool to help users explore the financial impact of adding
solar PV, batteries, and EVs to their household.
"""

import streamlit as st
import pandas as pd

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


# Page configuration
st.set_page_config(
    page_title="Energy Asset Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        color: #FFD93D;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #e8e8e8;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
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
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e8e8e8;
    }
    section[data-testid="stSidebar"] label {
        color: #FFD93D !important;
        font-weight: 500;
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
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Energy Asset Simulator</h1>
        <p>Explore how solar panels, batteries, and EVs could transform your energy costs</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load configuration
    tariffs = load_tariffs()
    customers = get_available_customers()
    
    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## 🏠 Customer Selection")
        
        customer_id = st.selectbox(
            "Select Household",
            options=list(customers.keys()),
            format_func=lambda x: customers[x],
            help="Choose a customer profile to analyze"
        )
        
        st.markdown("---")
        st.markdown("## ☀️ Solar PV System")
        
        pv_enabled = st.toggle("Enable PV System", value=False)
        pv_capacity = st.slider(
            "System Size (kWp)",
            min_value=3.0,
            max_value=15.0,
            value=6.0,
            step=0.5,
            disabled=not pv_enabled,
            help="Typical residential systems: 3-10 kWp"
        )
        
        st.markdown("---")
        st.markdown("## 🔋 Battery Storage")
        
        battery_enabled = st.toggle("Enable Battery", value=False)
        battery_capacity = st.slider(
            "Capacity (kWh)",
            min_value=5.0,
            max_value=20.0,
            value=10.0,
            step=1.0,
            disabled=not battery_enabled,
            help="Typical home batteries: 5-15 kWh"
        )
        
        st.markdown("---")
        st.markdown("## 🚗 Electric Vehicle")
        
        ev_enabled = st.toggle("Enable EV", value=False)
        ev_km = st.slider(
            "Annual Driving (km)",
            min_value=5000,
            max_value=30000,
            value=15000,
            step=1000,
            disabled=not ev_enabled,
            help="Average annual driving distance"
        )
        
        # Charging schedule (expandable)
        if ev_enabled:
            with st.expander("Charging Schedule"):
                ev_charge_start = st.slider(
                    "Start Hour", 0, 23, 18,
                    help="When EV starts charging"
                )
                ev_charge_end = st.slider(
                    "End Hour", 0, 23, 7,
                    help="When EV stops charging"
                )
        else:
            ev_charge_start = 18
            ev_charge_end = 7
    
    # Load customer data
    consumption_df = load_customer_data(customer_id)
    consumption_summary = get_consumption_summary(consumption_df)
    
    # Create asset configurations
    pv = PVSystem(
        capacity_kwp=pv_capacity if pv_enabled else 0,
        enabled=pv_enabled
    )
    battery = Battery(
        capacity_kwh=battery_capacity if battery_enabled else 0,
        enabled=battery_enabled
    )
    ev = EV(
        annual_km=ev_km if ev_enabled else 0,
        enabled=ev_enabled,
        charging_start_hour=ev_charge_start,
        charging_end_hour=ev_charge_end
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
                export_revenue = with_assets_costs[best_tariff_id].get('export_revenue', 0)
                st.metric(
                    "Export Revenue",
                    f"€{export_revenue:,.0f}",
                    help="Annual income from feed-in tariff"
                )
    
    # Row 4: Load Profiles
    st.markdown('<div class="section-header">📈 Energy Profiles</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Weekly View", "Daily Average", "Monthly Costs"])
    
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
    
    with tab3:
        monthly_df = get_monthly_costs(simulated_df, tariffs)
        fig_monthly = create_monthly_costs_chart(monthly_df)
        st.plotly_chart(fig_monthly, use_container_width=True)
    
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


if __name__ == "__main__":
    main()

