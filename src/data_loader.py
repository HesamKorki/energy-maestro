"""
Data loader module for consumption data and tariff configuration.
"""

from pathlib import Path
from functools import lru_cache
from typing import Dict, Any

import pandas as pd
import yaml


DATA_DIR = Path(__file__).parent.parent / "data" / "customers"
MARKET_DIR = Path(__file__).parent.parent / "data" / "market"
CONFIG_DIR = Path(__file__).parent.parent / "config"


@lru_cache(maxsize=10)
def load_customer_data(customer_id: str) -> pd.DataFrame:
    """
    Load consumption data for a customer.
    
    Args:
        customer_id: Customer identifier (e.g., 'customer_1')
    
    Returns:
        DataFrame with timestamp index and consumption values
    """
    file_path = DATA_DIR / f"{customer_id}.csv"
    
    df = pd.read_csv(file_path, parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    df.columns = ["consumption_kwh"]
    
    # Ensure the data is sorted by timestamp
    df.sort_index(inplace=True)
    
    return df


def get_available_customers() -> Dict[str, str]:
    """
    Get list of available customers with display names.
    
    Returns:
        Dictionary mapping customer_id to display name
    """
    customers = {}
    for file_path in sorted(DATA_DIR.glob("customer_*.csv")):
        customer_id = file_path.stem
        # Create a friendly display name
        customer_num = customer_id.split("_")[1]
        customers[customer_id] = f"Household {customer_num}"
    
    return customers


def load_tariffs() -> Dict[str, Any]:
    """
    Load tariff configuration from YAML file.
    
    Returns:
        Dictionary with tariff configurations
    """
    config_path = CONFIG_DIR / "tariffs.yaml"
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_consumption_summary(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate summary statistics for consumption data.
    
    Args:
        df: DataFrame with consumption data
    
    Returns:
        Dictionary with summary statistics
    """
    # Convert 15-min intervals to hourly for some metrics
    total_kwh = df["consumption_kwh"].sum()
    
    # Calculate daily consumption
    daily = df.resample("D")["consumption_kwh"].sum()
    
    # Peak 15-min consumption
    peak_15min = df["consumption_kwh"].max()
    
    # Convert to approximate peak power (kW) - 15 min = 0.25 hours
    peak_power_kw = peak_15min * 4  # kWh per 15 min * 4 = kW
    
    return {
        "total_annual_kwh": round(total_kwh, 1),
        "avg_daily_kwh": round(daily.mean(), 2),
        "max_daily_kwh": round(daily.max(), 2),
        "min_daily_kwh": round(daily.min(), 2),
        "peak_power_kw": round(peak_power_kw, 2),
        "days_of_data": len(daily),
    }


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based features to the consumption dataframe.
    
    Args:
        df: DataFrame with timestamp index
    
    Returns:
        DataFrame with additional time columns
    """
    df = df.copy()
    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month
    df["is_weekend"] = df["day_of_week"] >= 5
    
    return df


def get_hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate average hourly consumption profile.
    
    Args:
        df: DataFrame with consumption data and hour column
    
    Returns:
        DataFrame with average consumption by hour
    """
    df_with_hour = add_time_features(df)
    
    hourly_avg = df_with_hour.groupby("hour")["consumption_kwh"].mean() * 4  # Convert to kW
    
    return hourly_avg.to_frame("avg_power_kw")


def get_weekly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate average weekly consumption profile.
    
    Args:
        df: DataFrame with consumption data
    
    Returns:
        DataFrame with average consumption by day of week
    """
    df_with_features = add_time_features(df)
    
    daily = df_with_features.groupby("day_of_week")["consumption_kwh"].sum() / \
            (len(df) // (24 * 4 * 7) + 1)  # Approximate weeks
    
    return daily.to_frame("avg_daily_kwh")


@lru_cache(maxsize=1)
def load_market_prices() -> pd.DataFrame:
    """
    Load EPEX spot market prices from CSV files.
    
    Returns:
        DataFrame with timestamp index and price_eur_per_kwh column
    """
    dfs = []
    
    # Look for Day-ahead price files
    for file_path in sorted(MARKET_DIR.glob("Day-ahead_prices_*.csv")):
        df = pd.read_csv(file_path, sep=";", low_memory=False)
        dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    # Combine all years
    market_df = pd.concat(dfs, ignore_index=True)
    
    # Parse timestamps from "Start date" column (format: "Jan 1, 2022 12:00 AM")
    market_df["timestamp"] = pd.to_datetime(market_df["Start date"], format="%b %d, %Y %I:%M %p")
    
    # Get the Germany/Luxembourg price column
    price_col = "Germany/Luxembourg [€/MWh] Original resolutions"
    
    # Convert EUR/MWh to EUR/kWh
    market_df["price_eur_per_kwh"] = pd.to_numeric(market_df[price_col], errors="coerce") / 1000.0
    
    # Keep only relevant columns and set index
    result = market_df[["timestamp", "price_eur_per_kwh"]].copy()
    result.set_index("timestamp", inplace=True)
    result.sort_index(inplace=True)
    
    # Remove any duplicate timestamps (keep first)
    result = result[~result.index.duplicated(keep="first")]
    
    # Drop any NaN prices
    result = result.dropna()
    
    return result


def get_market_prices_for_period(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    Get market prices for a specific period.
    
    Args:
        start_date: Start of period
        end_date: End of period
    
    Returns:
        DataFrame with prices for the period
    """
    market_df = load_market_prices()
    
    if market_df.empty:
        return market_df
    
    mask = (market_df.index >= start_date) & (market_df.index <= end_date)
    return market_df[mask]

