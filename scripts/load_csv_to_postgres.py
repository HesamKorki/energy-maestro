#!/usr/bin/env python3
"""
Script to load customer and market CSV files into PostgreSQL.
Run this after starting the database to migrate existing data.

Usage:
    python scripts/load_csv_to_postgres.py           # Load all data
    python scripts/load_csv_to_postgres.py --market  # Load only market prices
    python scripts/load_csv_to_postgres.py --customers  # Load only customers
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """Create a PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "energy"),
        password=os.getenv("POSTGRES_PASSWORD", "energy123"),
        dbname=os.getenv("POSTGRES_DB", "energy_maestro"),
    )


def load_customer_csv_files(data_dir: Path, batch_size: int = 10000):
    """
    Load all customer CSV files into the PostgreSQL metrics table.
    
    Args:
        data_dir: Path to the customers data directory
        batch_size: Number of rows to insert per batch
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    csv_files = sorted(data_dir.glob("customer_*.csv"))
    
    if not csv_files:
        print(f"No customer CSV files found in {data_dir}")
        return 0
    
    print(f"Found {len(csv_files)} customer files to load")
    
    total_rows = 0
    
    for csv_file in csv_files:
        customer_id = csv_file.stem  # e.g., "customer_1"
        
        print(f"  Loading {customer_id}...", end=" ", flush=True)
        
        # Read CSV file
        df = pd.read_csv(csv_file, parse_dates=["timestamp"])
        
        # Prepare data for insertion
        values = [
            (row["timestamp"], row[df.columns[1]], customer_id)
            for _, row in df.iterrows()
        ]
        
        # Insert in batches
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            execute_values(
                cursor,
                "INSERT INTO metrics (ts, value, customer_id) VALUES %s",
                batch,
                template="(%s, %s, %s)"
            )
        
        conn.commit()
        print(f"{len(values):,} rows")
        total_rows += len(values)
    
    cursor.close()
    conn.close()
    
    return total_rows


def load_market_csv_files(data_dir: Path, batch_size: int = 10000):
    """
    Load market price CSV files into the PostgreSQL market_prices table.
    
    Args:
        data_dir: Path to the market data directory
        batch_size: Number of rows to insert per batch
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    csv_files = sorted(data_dir.glob("Day-ahead_prices_*.csv"))
    
    if not csv_files:
        print(f"No market CSV files found in {data_dir}")
        return 0
    
    print(f"Found {len(csv_files)} market files to load")
    
    total_rows = 0
    
    for csv_file in csv_files:
        print(f"  Loading {csv_file.name}...", end=" ", flush=True)
        
        # Read CSV file
        df = pd.read_csv(csv_file, sep=";", low_memory=False)
        
        # Parse timestamps from "Start date" column (format: "Jan 1, 2022 12:00 AM")
        df["timestamp"] = pd.to_datetime(df["Start date"], format="%b %d, %Y %I:%M %p")
        
        # Get the Germany/Luxembourg price column and convert EUR/MWh to EUR/kWh
        price_col = "Germany/Luxembourg [€/MWh] Original resolutions"
        df["price_eur_per_kwh"] = pd.to_numeric(df[price_col], errors="coerce") / 1000.0
        
        # Drop rows with invalid prices
        df = df.dropna(subset=["price_eur_per_kwh"])
        
        # Prepare data for insertion
        values = [
            (row["timestamp"], row["price_eur_per_kwh"])
            for _, row in df.iterrows()
        ]
        
        # Insert in batches
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            execute_values(
                cursor,
                "INSERT INTO market_prices (ts, price_eur_per_kwh) VALUES %s",
                batch,
                template="(%s, %s)"
            )
        
        conn.commit()
        print(f"{len(values):,} rows")
        total_rows += len(values)
    
    cursor.close()
    conn.close()
    
    return total_rows


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load CSV data into PostgreSQL database"
    )
    parser.add_argument(
        "--customers",
        action="store_true",
        help="Load only customer consumption data"
    )
    parser.add_argument(
        "--market",
        action="store_true",
        help="Load only market price data"
    )
    args = parser.parse_args()
    
    # If neither flag is set, load both
    load_customers = args.customers or not (args.customers or args.market)
    load_market = args.market or not (args.customers or args.market)
    
    # Load environment variables from .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Determine data directories
    script_dir = Path(__file__).parent
    customers_dir = script_dir.parent / "data" / "customers"
    market_dir = script_dir.parent / "data" / "market"
    
    print(f"Target database: {os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'energy_maestro')}")
    print()
    
    try:
        # Load customer data
        if load_customers:
            if customers_dir.exists():
                print(f"Loading customer data from: {customers_dir}")
                customer_rows = load_customer_csv_files(customers_dir)
                print(f"  Total: {customer_rows:,} customer rows loaded\n")
            else:
                print(f"Warning: Customer data directory not found: {customers_dir}\n")
        
        # Load market data
        if load_market:
            if market_dir.exists():
                print(f"Loading market data from: {market_dir}")
                market_rows = load_market_csv_files(market_dir)
                print(f"  Total: {market_rows:,} market price rows loaded\n")
            else:
                print(f"Warning: Market data directory not found: {market_dir}\n")
        
        print("Done!")
        
    except psycopg2.OperationalError as e:
        print(f"\nError connecting to database: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  docker compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    main()
