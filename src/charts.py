"""
Plotly chart components for the Energy Asset Simulator.
"""

from typing import Dict, Any, List, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# Color palette - modern energy theme
COLORS = {
    "consumption": "#FF6B6B",      # Coral red
    "pv_generation": "#FFD93D",    # Solar yellow
    "battery_charge": "#6BCB77",   # Green
    "battery_discharge": "#4D96FF", # Blue
    "grid_import": "#C9CBCF",      # Gray
    "grid_export": "#95E1D3",      # Teal
    "ev": "#9B59B6",               # Purple
    "baseline": "#6c757d",         # Dark gray
    "savings": "#7DD3A3",          # Pastel mint green
}

TARIFF_COLORS = {
    "dynamic": "#FF6B6B",
    "fixed_3year": "#4D96FF",
    "daily_fix": "#FFD93D",
}


def create_bill_comparison_chart(
    baseline_costs: Dict[str, Dict[str, float]],
    with_assets_costs: Dict[str, Dict[str, float]],
) -> go.Figure:
    """
    Create a grouped bar chart comparing bills across tariffs.
    
    Args:
        baseline_costs: Costs without assets
        with_assets_costs: Costs with assets
    
    Returns:
        Plotly Figure
    """
    tariff_names = []
    baseline_values = []
    with_assets_values = []
    
    for tariff_id in baseline_costs:
        if tariff_id in with_assets_costs:
            tariff_names.append(baseline_costs[tariff_id]["tariff_name"])
            baseline_values.append(baseline_costs[tariff_id]["net_cost"])
            with_assets_values.append(with_assets_costs[tariff_id]["net_cost"])
    
    fig = go.Figure()
    
    # Baseline bars
    fig.add_trace(go.Bar(
        name="Without Assets",
        x=tariff_names,
        y=baseline_values,
        marker_color=COLORS["baseline"],
        text=[f"€{v:,.0f}" for v in baseline_values],
        textposition="inside",
        textfont=dict(color="white", size=12),
        insidetextanchor="middle",
    ))
    
    # With assets bars
    fig.add_trace(go.Bar(
        name="With Assets",
        x=tariff_names,
        y=with_assets_values,
        marker_color=COLORS["savings"],
        text=[f"€{v:,.0f}" for v in with_assets_values],
        textposition="inside",
        textfont=dict(color="#1a1a2e", size=12, weight="bold"),
        insidetextanchor="middle",
    ))
    
    fig.update_layout(
        title=dict(
            text="Annual Electricity Cost by Tariff",
            font=dict(size=20),
        ),
        xaxis_title="Tariff Type",
        yaxis_title="Annual Cost (€)",
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400,
        template="plotly_white",
        margin=dict(t=80, b=60),
    )
    
    return fig


def create_savings_chart(
    comparison: Dict[str, Dict[str, float]]
) -> go.Figure:
    """
    Create a horizontal bar chart showing savings by tariff.
    
    Args:
        comparison: Comparison data from compare_scenarios
    
    Returns:
        Plotly Figure
    """
    data = []
    for tariff_id, values in comparison.items():
        data.append({
            "tariff": values["tariff_name"],
            "savings": values["annual_savings"],
            "percent": values["savings_percent"],
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values("savings", ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df["savings"],
        y=df["tariff"],
        orientation="h",
        marker_color=[COLORS["savings"] if s > 0 else COLORS["consumption"] for s in df["savings"]],
        text=[f"€{s:,.0f} ({p:.0f}%)" for s, p in zip(df["savings"], df["percent"])],
        textposition="inside",
        textfont=dict(color=["#1a1a2e" if s > 0 else "white" for s in df["savings"]], size=11, weight="bold"),
        insidetextanchor="middle",
    ))
    
    fig.update_layout(
        title=dict(
            text="Annual Savings by Tariff",
            font=dict(size=18),
        ),
        xaxis_title="Annual Savings (€)",
        yaxis_title="",
        height=250,
        template="plotly_white",
        margin=dict(l=120, r=40, t=60, b=40),
    )
    
    return fig


def create_load_profile_chart(
    df: pd.DataFrame,
    date_range: Optional[tuple] = None
) -> go.Figure:
    """
    Create an interactive load profile chart.
    
    Args:
        df: DataFrame with simulation results
        date_range: Optional tuple of (start_date, end_date)
    
    Returns:
        Plotly Figure
    """
    # Filter by date range if provided
    if date_range:
        mask = (df.index >= date_range[0]) & (df.index <= date_range[1])
        plot_df = df[mask]
    else:
        # Default to first week
        plot_df = df.iloc[:7*24*4]  # 7 days of 15-min data
    
    fig = go.Figure()
    
    # Consumption
    fig.add_trace(go.Scatter(
        x=plot_df.index,
        y=plot_df["consumption_kwh"] * 4,  # Convert to kW
        name="Consumption",
        fill="tozeroy",
        line=dict(color=COLORS["consumption"], width=1),
        fillcolor=f"rgba(255, 107, 107, 0.3)",
    ))
    
    # PV generation
    if "pv_generation_kwh" in plot_df.columns and plot_df["pv_generation_kwh"].sum() > 0:
        fig.add_trace(go.Scatter(
            x=plot_df.index,
            y=plot_df["pv_generation_kwh"] * 4,
            name="PV Generation",
            fill="tozeroy",
            line=dict(color=COLORS["pv_generation"], width=1),
            fillcolor=f"rgba(255, 217, 61, 0.4)",
        ))
    
    # EV consumption
    if "ev_consumption_kwh" in plot_df.columns and plot_df["ev_consumption_kwh"].sum() > 0:
        fig.add_trace(go.Scatter(
            x=plot_df.index,
            y=plot_df["ev_consumption_kwh"] * 4,
            name="EV Charging",
            line=dict(color=COLORS["ev"], width=2, dash="dot"),
        ))
    
    fig.update_layout(
        title=dict(
            text="Load Profile",
            font=dict(size=18),
        ),
        xaxis_title="Time",
        yaxis_title="Power (kW)",
        height=350,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
    )
    
    return fig


def create_daily_profile_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create an average daily profile chart.
    
    Args:
        df: DataFrame with simulation results
    
    Returns:
        Plotly Figure
    """
    # Calculate hourly averages
    df_copy = df.copy()
    df_copy["hour"] = df_copy.index.hour
    
    hourly = df_copy.groupby("hour").agg({
        "consumption_kwh": "mean",
        "pv_generation_kwh": "mean" if "pv_generation_kwh" in df_copy.columns else lambda x: 0,
        "grid_import_kwh": "mean" if "grid_import_kwh" in df_copy.columns else lambda x: 0,
    }) * 4  # Convert to kW
    
    fig = go.Figure()
    
    # Consumption
    fig.add_trace(go.Scatter(
        x=hourly.index,
        y=hourly["consumption_kwh"],
        name="Avg Consumption",
        fill="tozeroy",
        line=dict(color=COLORS["consumption"], width=2),
        fillcolor=f"rgba(255, 107, 107, 0.3)",
    ))
    
    # PV
    if "pv_generation_kwh" in hourly.columns:
        pv_values = hourly["pv_generation_kwh"]
        if isinstance(pv_values, pd.Series) and pv_values.sum() > 0:
            fig.add_trace(go.Scatter(
                x=hourly.index,
                y=pv_values,
                name="Avg PV Generation",
                fill="tozeroy",
                line=dict(color=COLORS["pv_generation"], width=2),
                fillcolor=f"rgba(255, 217, 61, 0.4)",
            ))
    
    # Grid import
    if "grid_import_kwh" in hourly.columns:
        grid_values = hourly["grid_import_kwh"]
        if isinstance(grid_values, pd.Series):
            fig.add_trace(go.Scatter(
                x=hourly.index,
                y=grid_values,
                name="Avg Grid Import",
                line=dict(color=COLORS["grid_import"], width=2, dash="dash"),
            ))
    
    fig.update_layout(
        title=dict(
            text="Average Daily Profile",
            font=dict(size=18),
        ),
        xaxis_title="Hour of Day",
        yaxis_title="Power (kW)",
        height=350,
        template="plotly_white",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(0, 24, 3)),
            ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_monthly_costs_chart(
    monthly_df: pd.DataFrame
) -> go.Figure:
    """
    Create a monthly costs line chart.
    
    Args:
        monthly_df: DataFrame with monthly cost data
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    for tariff_id in monthly_df["tariff_id"].unique():
        tariff_data = monthly_df[monthly_df["tariff_id"] == tariff_id]
        
        fig.add_trace(go.Scatter(
            x=tariff_data["month"],
            y=tariff_data["net_cost"],
            name=tariff_data["tariff"].iloc[0],
            mode="lines+markers",
            line=dict(color=TARIFF_COLORS.get(tariff_id, "#888"), width=2),
            marker=dict(size=6),
        ))
    
    fig.update_layout(
        title=dict(
            text="Monthly Electricity Costs",
            font=dict(size=18),
        ),
        xaxis_title="Month",
        yaxis_title="Cost (€)",
        height=350,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
    )
    
    return fig


def create_energy_flow_chart(
    metrics: Dict[str, float]
) -> go.Figure:
    """
    Create a Sankey diagram showing energy flows.
    
    Args:
        metrics: Self-sufficiency metrics
    
    Returns:
        Plotly Figure
    """
    pv = metrics.get("total_pv_generation_kwh", 0)
    grid_import = metrics.get("grid_import_kwh", 0)
    grid_export = metrics.get("grid_export_kwh", 0)
    total_consumption = metrics.get("total_consumption_kwh", 0)
    
    # Self-consumed PV
    self_consumed = pv - grid_export
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["PV Generation", "Grid Import", "Self-Consumed", "Grid Export", "Total Consumption"],
            color=[COLORS["pv_generation"], COLORS["grid_import"], COLORS["battery_charge"], 
                   COLORS["grid_export"], COLORS["consumption"]],
        ),
        link=dict(
            source=[0, 0, 1, 2, 1],  # PV, PV, Grid, Self-consumed, Grid
            target=[2, 3, 4, 4, 4],  # Self-consumed, Export, Consumption, Consumption, Consumption
            value=[self_consumed, grid_export, grid_import, self_consumed, 0],
            color=["rgba(255, 217, 61, 0.6)", "rgba(149, 225, 211, 0.6)", 
                   "rgba(201, 203, 207, 0.7)", "rgba(107, 203, 119, 0.6)", "rgba(0,0,0,0)"],
        ),
    )])
    
    fig.update_layout(
        title=dict(
            text="Energy Flow (Annual)",
            font=dict(size=18),
        ),
        height=350,
        template="plotly_white",
    )
    
    return fig


def create_self_sufficiency_gauge(
    metrics: Dict[str, float]
) -> go.Figure:
    """
    Create gauge charts for self-sufficiency metrics.
    
    Args:
        metrics: Self-sufficiency metrics
    
    Returns:
        Plotly Figure
    """
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=("Self-Sufficiency", "Self-Consumption"),
    )
    
    # Self-sufficiency gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=metrics.get("self_sufficiency_pct", 0),
            number=dict(suffix="%", font=dict(size=36)),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["savings"]),
                steps=[
                    dict(range=[0, 30], color="rgba(255, 107, 107, 0.3)"),
                    dict(range=[30, 60], color="rgba(255, 217, 61, 0.3)"),
                    dict(range=[60, 100], color="rgba(107, 203, 119, 0.3)"),
                ],
                threshold=dict(
                    line=dict(color="black", width=2),
                    value=metrics.get("self_sufficiency_pct", 0),
                ),
            ),
        ),
        row=1, col=1
    )
    
    # Self-consumption gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=metrics.get("self_consumption_pct", 0),
            number=dict(suffix="%", font=dict(size=36)),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=COLORS["pv_generation"]),
                steps=[
                    dict(range=[0, 30], color="rgba(255, 107, 107, 0.3)"),
                    dict(range=[30, 60], color="rgba(255, 217, 61, 0.3)"),
                    dict(range=[60, 100], color="rgba(107, 203, 119, 0.3)"),
                ],
                threshold=dict(
                    line=dict(color="black", width=2),
                    value=metrics.get("self_consumption_pct", 0),
                ),
            ),
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=280,
        template="plotly_white",
        margin=dict(t=60, b=20),
    )
    
    return fig


def create_battery_soc_chart(
    df: pd.DataFrame,
    date_range: Optional[tuple] = None
) -> go.Figure:
    """
    Create a battery state of charge chart.
    
    Args:
        df: DataFrame with battery_soc column
        date_range: Optional date range filter
    
    Returns:
        Plotly Figure
    """
    if "battery_soc" not in df.columns or df["battery_soc"].sum() == 0:
        return go.Figure()
    
    # Filter by date range
    if date_range:
        mask = (df.index >= date_range[0]) & (df.index <= date_range[1])
        plot_df = df[mask]
    else:
        plot_df = df.iloc[:7*24*4]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=plot_df.index,
        y=plot_df["battery_soc"],
        name="Battery SOC",
        fill="tozeroy",
        line=dict(color=COLORS["battery_charge"], width=2),
        fillcolor=f"rgba(107, 203, 119, 0.6)",
    ))
    
    fig.update_layout(
        title=dict(
            text="Battery State of Charge",
            font=dict(size=18),
        ),
        xaxis_title="Time",
        yaxis_title="Energy (kWh)",
        height=300,
        template="plotly_white",
    )
    
    return fig

