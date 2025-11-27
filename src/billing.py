"""
Billing calculation module for different tariff types.
"""

from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from src.data_loader import load_market_prices


def calculate_dynamic_tariff_cost(
    df: pd.DataFrame,
    tariff_config: Dict[str, Any],
    market_prices: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """
    Calculate costs under dynamic (15-min varying) tariff using real market prices.
    
    Args:
        df: DataFrame with grid_import_kwh and grid_export_kwh columns
        tariff_config: Tariff configuration dictionary
        market_prices: Optional pre-loaded market prices DataFrame
    
    Returns:
        Dictionary with cost breakdown
    """
    base_fee = tariff_config["base_fee_monthly"]
    feed_in = tariff_config.get("feed_in_tariff", 0.08)
    
    # Load market prices if not provided
    if market_prices is None:
        market_prices = load_market_prices()
    
    # Get import data
    grid_import = df.get("grid_import_kwh", df["consumption_kwh"])
    grid_export = df.get("grid_export_kwh", pd.Series([0] * len(df), index=df.index))
    
    # Match market prices to consumption timestamps
    if not market_prices.empty:
        # Use merge_asof for nearest timestamp matching
        df_reset = df.reset_index()
        df_reset.columns = ["timestamp"] + list(df_reset.columns[1:])
        
        market_reset = market_prices.reset_index()
        market_reset.columns = ["timestamp", "price_eur_per_kwh"]
        
        merged = pd.merge_asof(
            df_reset.sort_values("timestamp"),
            market_reset.sort_values("timestamp"),
            on="timestamp",
            direction="nearest"
        )
        spot_prices = merged["price_eur_per_kwh"].fillna(0.10).values  # Fallback price
        
        # Calculate import cost using real spot prices
        import_cost = (grid_import.values * spot_prices).sum()
        
        # For export, use spot price (or feed-in if configured differently)
        # Using spot price for export as well (common in dynamic tariffs)
        export_revenue = (grid_export.values * spot_prices).sum()
        
        avg_price = np.nanmean(spot_prices)
    else:
        # Fallback to static hourly prices from config
        prices_by_hour = tariff_config.get("prices_by_hour", [0.15] * 24)
        hours = df.index.hour
        hourly_prices = np.array([prices_by_hour[h] for h in hours])
        
        import_cost = (grid_import * hourly_prices).sum()
        export_revenue = (grid_export * feed_in).sum()
        avg_price = np.mean(prices_by_hour)
    
    # Calculate number of months in data
    days = (df.index.max() - df.index.min()).days + 1
    months = days / 30.44  # Average days per month
    
    # Total base fees
    total_base_fee = base_fee * months
    
    # Net cost
    net_cost = import_cost + total_base_fee - export_revenue
    
    return {
        "tariff_name": tariff_config["name"],
        "import_cost": round(import_cost, 2),
        "base_fee": round(total_base_fee, 2),
        "export_revenue": round(export_revenue, 2),
        "net_cost": round(net_cost, 2),
        "total_import_kwh": round(grid_import.sum(), 1),
        "total_export_kwh": round(grid_export.sum(), 1),
        "avg_import_price": round(import_cost / max(grid_import.sum(), 1), 4),
        "avg_spot_price": round(avg_price, 4),
    }


def calculate_fixed_tariff_cost(
    df: pd.DataFrame,
    tariff_config: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate costs under fixed rate tariff.
    
    Args:
        df: DataFrame with grid_import_kwh and grid_export_kwh columns
        tariff_config: Tariff configuration dictionary
    
    Returns:
        Dictionary with cost breakdown
    """
    rate = tariff_config["rate"]
    base_fee = tariff_config["base_fee_monthly"]
    feed_in = tariff_config.get("feed_in_tariff", 0.0)  # No feed-in by default
    
    # Calculate import cost
    grid_import = df.get("grid_import_kwh", df["consumption_kwh"])
    import_cost = grid_import.sum() * rate
    
    # Calculate export revenue
    grid_export = df.get("grid_export_kwh", pd.Series([0] * len(df), index=df.index))
    export_revenue = grid_export.sum() * feed_in
    
    # Calculate number of months in data
    days = (df.index.max() - df.index.min()).days + 1
    months = days / 30.44
    
    # Total base fees
    total_base_fee = base_fee * months
    
    # Net cost
    net_cost = import_cost + total_base_fee - export_revenue
    
    return {
        "tariff_name": tariff_config["name"],
        "import_cost": round(import_cost, 2),
        "base_fee": round(total_base_fee, 2),
        "export_revenue": round(export_revenue, 2),
        "net_cost": round(net_cost, 2),
        "total_import_kwh": round(grid_import.sum(), 1),
        "total_export_kwh": round(grid_export.sum(), 1),
        "avg_import_price": round(rate, 4),
    }


def calculate_day_night_tariff_cost(
    df: pd.DataFrame,
    tariff_config: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate costs under day/night tariff.
    
    Args:
        df: DataFrame with grid_import_kwh and grid_export_kwh columns
        tariff_config: Tariff configuration dictionary
    
    Returns:
        Dictionary with cost breakdown
    """
    day_rate = tariff_config["day_rate"]
    night_rate = tariff_config["night_rate"]
    day_start = tariff_config.get("day_start_hour", 6)
    day_end = tariff_config.get("day_end_hour", 22)
    base_fee = tariff_config["base_fee_monthly"]
    feed_in = tariff_config.get("feed_in_tariff", 0.0)  # No feed-in by default
    
    # Determine day/night for each timestamp
    hours = df.index.hour
    is_day = (hours >= day_start) & (hours < day_end)
    
    # Get import data
    grid_import = df.get("grid_import_kwh", df["consumption_kwh"])
    
    # Calculate day and night consumption
    day_import = grid_import[is_day].sum()
    night_import = grid_import[~is_day].sum()
    
    # Calculate costs
    day_cost = day_import * day_rate
    night_cost = night_import * night_rate
    import_cost = day_cost + night_cost
    
    # Calculate export revenue
    grid_export = df.get("grid_export_kwh", pd.Series([0] * len(df), index=df.index))
    export_revenue = grid_export.sum() * feed_in
    
    # Calculate number of months in data
    days = (df.index.max() - df.index.min()).days + 1
    months = days / 30.44
    
    # Total base fees
    total_base_fee = base_fee * months
    
    # Net cost
    net_cost = import_cost + total_base_fee - export_revenue
    
    return {
        "tariff_name": tariff_config["name"],
        "import_cost": round(import_cost, 2),
        "day_cost": round(day_cost, 2),
        "night_cost": round(night_cost, 2),
        "base_fee": round(total_base_fee, 2),
        "export_revenue": round(export_revenue, 2),
        "net_cost": round(net_cost, 2),
        "total_import_kwh": round(grid_import.sum(), 1),
        "day_import_kwh": round(day_import, 1),
        "night_import_kwh": round(night_import, 1),
        "total_export_kwh": round(grid_export.sum(), 1),
        "avg_import_price": round(import_cost / max(grid_import.sum(), 1), 4),
    }


def calculate_all_tariffs(
    df: pd.DataFrame,
    tariffs_config: Dict[str, Any]
) -> Dict[str, Dict[str, float]]:
    """
    Calculate costs for all tariff types.
    
    Args:
        df: DataFrame with simulation results
        tariffs_config: Full tariffs configuration
    
    Returns:
        Dictionary mapping tariff_id to cost breakdown
    """
    results = {}
    
    # Dynamic tariff
    if "dynamic" in tariffs_config:
        results["dynamic"] = calculate_dynamic_tariff_cost(
            df, tariffs_config["dynamic"]
        )
    
    # Fixed 3-year tariff
    if "fixed_3year" in tariffs_config:
        results["fixed_3year"] = calculate_fixed_tariff_cost(
            df, tariffs_config["fixed_3year"]
        )
    
    # Day/night tariff
    if "daily_fix" in tariffs_config:
        results["daily_fix"] = calculate_day_night_tariff_cost(
            df, tariffs_config["daily_fix"]
        )
    
    return results


def compare_scenarios(
    baseline_costs: Dict[str, Dict[str, float]],
    with_assets_costs: Dict[str, Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    """
    Compare costs between baseline and with-assets scenarios.
    
    Args:
        baseline_costs: Costs without assets
        with_assets_costs: Costs with assets
    
    Returns:
        Dictionary with savings for each tariff
    """
    comparison = {}
    
    for tariff_id in baseline_costs:
        if tariff_id in with_assets_costs:
            baseline = baseline_costs[tariff_id]
            with_assets = with_assets_costs[tariff_id]
            
            savings = baseline["net_cost"] - with_assets["net_cost"]
            savings_pct = (savings / baseline["net_cost"]) * 100 if baseline["net_cost"] > 0 else 0
            
            comparison[tariff_id] = {
                "tariff_name": baseline["tariff_name"],
                "baseline_cost": baseline["net_cost"],
                "with_assets_cost": with_assets["net_cost"],
                "annual_savings": round(savings, 2),
                "savings_percent": round(savings_pct, 1),
                "export_revenue": with_assets.get("export_revenue", 0),
            }
    
    return comparison


def get_monthly_costs(
    df: pd.DataFrame,
    tariffs_config: Dict[str, Any]
) -> pd.DataFrame:
    """
    Calculate monthly costs for each tariff.
    
    Args:
        df: DataFrame with simulation results
        tariffs_config: Tariffs configuration
    
    Returns:
        DataFrame with monthly costs by tariff
    """
    # Group by month
    df_monthly = df.copy()
    df_monthly["month"] = df_monthly.index.to_period("M")
    
    monthly_data = []
    
    for month, group in df_monthly.groupby("month"):
        # Create a temporary DataFrame for this month
        month_df = group.drop(columns=["month"])
        
        # Calculate costs for each tariff
        costs = calculate_all_tariffs(month_df, tariffs_config)
        
        for tariff_id, cost_data in costs.items():
            monthly_data.append({
                "month": month.to_timestamp(),
                "tariff": cost_data["tariff_name"],
                "tariff_id": tariff_id,
                "net_cost": cost_data["net_cost"],
                "import_kwh": cost_data["total_import_kwh"],
                "export_kwh": cost_data.get("total_export_kwh", 0),
            })
    
    return pd.DataFrame(monthly_data)


def find_best_tariff(costs: Dict[str, Dict[str, float]]) -> str:
    """
    Find the tariff with the lowest net cost.
    
    Args:
        costs: Dictionary mapping tariff_id to cost breakdown
    
    Returns:
        tariff_id of the best tariff
    """
    best_tariff = min(costs.items(), key=lambda x: x[1]["net_cost"])
    return best_tariff[0]

