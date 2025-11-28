"""
Data loader module for consumption data and tariff configuration.
Reads customer data from PostgreSQL database.
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any

import pandas as pd
import psycopg2
import yaml


CONFIG_DIR = Path(__file__).parent.parent / "config"


def _get_db_connection():
    """
    Create a PostgreSQL database connection.
    
    Returns:
        psycopg2 connection object
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "energy"),
        password=os.getenv("POSTGRES_PASSWORD", "energy123"),
        dbname=os.getenv("POSTGRES_DB", "energy_maestro"),
    )


@lru_cache(maxsize=10)
def load_customer_data(customer_id: str) -> pd.DataFrame:
    """
    Load consumption data for a customer from PostgreSQL.
    
    Args:
        customer_id: Customer identifier
    
    Returns:
        DataFrame with timestamp index and consumption values
    """
    try:
        conn = _get_db_connection()
    except psycopg2.OperationalError as e:
        raise ConnectionError(
            f"Cannot connect to PostgreSQL database. "
            f"Make sure the database is running (docker compose up -d). "
            f"Error: {e}"
        ) from e
    
    try:
        query = """
            SELECT ts as timestamp, value as consumption_kwh
            FROM metrics
            WHERE customer_id = %s
            ORDER BY ts
        """
        df = pd.read_sql(query, conn, params=(customer_id,), parse_dates=["timestamp"])
        df.set_index("timestamp", inplace=True)
        
        if df.empty:
            raise ValueError(
                f"No data found for customer '{customer_id}'. "
                f"Make sure data is loaded in the database."
            )
        
        return df
    finally:
        conn.close()


def get_available_customers() -> Dict[str, str]:
    """
    Get list of available customers from PostgreSQL.
    
    Returns:
        Dictionary mapping customer_id to display name
    """
    try:
        conn = _get_db_connection()
    except psycopg2.OperationalError as e:
        raise ConnectionError(
            f"Cannot connect to PostgreSQL database. "
            f"Make sure the database is running (docker compose up -d). "
            f"Error: {e}"
        ) from e
    
    try:
        query = "SELECT DISTINCT customer_id FROM metrics ORDER BY customer_id"
        df = pd.read_sql(query, conn)
        
        if df.empty:
            raise ValueError(
                "No customers found in database. "
                "Run 'python scripts/load_csv_to_postgres.py' to load data."
            )
        
        customers = {}
        for customer_id in df["customer_id"]:
            # Create a friendly display name
            if customer_id.startswith("customer_"):
                customer_num = customer_id.split("_")[1]
                customers[customer_id] = f"Household {customer_num}"
            else:
                customers[customer_id] = customer_id
        
        return customers
    finally:
        conn.close()


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
    Load EPEX spot market prices from PostgreSQL.
    
    Returns:
        DataFrame with timestamp index and price_eur_per_kwh column
    """
    try:
        conn = _get_db_connection()
    except psycopg2.OperationalError as e:
        raise ConnectionError(
            f"Cannot connect to PostgreSQL database. "
            f"Make sure the database is running (docker compose up -d). "
            f"Error: {e}"
        ) from e
    
    try:
        query = """
            SELECT ts as timestamp, price_eur_per_kwh
            FROM market_prices
            ORDER BY ts
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df
    finally:
        conn.close()


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
