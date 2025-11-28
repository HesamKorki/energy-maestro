"""
Asset simulation module for PV, Battery, and EV.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Literal
from enum import Enum

import numpy as np
import pandas as pd


class RoofType(Enum):
    """Types of roof configurations."""
    FLAT = "flat"
    GABLE = "gable"  # Two-sided pitched roof
    HIP = "hip"      # Four-sided pitched roof
    MONO = "mono"    # Single-pitched roof (shed style)


class HeatWaterType(Enum):
    """Hot water heating system types."""
    ELECTRIC_BOILER = "electric_boiler"
    HEAT_PUMP_BOILER = "heat_pump_boiler"
    OTHER = "other"  # Oil, gas, wood, district heat


class HeatingSystemType(Enum):
    """Space heating system types."""
    ELECTRIC = "electric"
    HEAT_PUMP = "heat_pump"
    OTHER = "other"  # Oil, gas, wood, district heat


class CoolingType(Enum):
    """Cooling/AC usage."""
    YES = "yes"
    NO = "no"
    SOMETIMES = "sometimes"


class Orientation(Enum):
    """Roof orientation/azimuth."""
    SOUTH = "south"
    SOUTH_EAST = "south_east"
    SOUTH_WEST = "south_west"
    EAST = "east"
    WEST = "west"
    NORTH_EAST = "north_east"
    NORTH_WEST = "north_west"
    NORTH = "north"


# Efficiency factors for different orientations (relative to South)
ORIENTATION_FACTORS = {
    Orientation.SOUTH: 1.00,
    Orientation.SOUTH_EAST: 0.95,
    Orientation.SOUTH_WEST: 0.95,
    Orientation.EAST: 0.80,
    Orientation.WEST: 0.80,
    Orientation.NORTH_EAST: 0.55,
    Orientation.NORTH_WEST: 0.55,
    Orientation.NORTH: 0.45,
}

# Efficiency factors for roof inclination (optimal is ~35° for Luxembourg)
INCLINATION_FACTORS = {
    0: 0.87,    # Flat
    10: 0.93,
    15: 0.95,
    20: 0.97,
    25: 0.99,
    30: 1.00,   # Near optimal
    35: 1.00,   # Optimal
    40: 0.99,
    45: 0.97,
    50: 0.94,
    60: 0.87,
    70: 0.78,
    80: 0.67,
    90: 0.55,   # Vertical (wall-mounted)
}

# Panel efficiency: Watts per m² (modern panels ~200W/m²)
PANEL_WATTS_PER_M2 = 200

# Usable roof fraction by roof type
USABLE_ROOF_FRACTION = {
    RoofType.FLAT: 0.70,    # Some spacing needed for tilt mounting
    RoofType.GABLE: 0.80,   # Good utilization on pitched roofs
    RoofType.HIP: 0.60,     # Less usable due to hip ridges
    RoofType.MONO: 0.85,    # Single slope is very efficient
}


@dataclass
class PVSizingConfig:
    """Configuration for PV system sizing based on roof characteristics."""
    roof_surface_m2: float = 50.0
    roof_type: RoofType = RoofType.GABLE
    use_both_sides: bool = False  # For gable roofs
    roof_inclination: int = 30  # degrees
    orientation: Orientation = Orientation.SOUTH
    yearly_consumption_kwh: float = 4000.0


def calculate_recommended_pv_size(config: PVSizingConfig) -> Dict[str, Any]:
    """
    Calculate recommended PV system size based on roof configuration.
    
    Args:
        config: PV sizing configuration with roof details
        
    Returns:
        Dictionary with recommended size, max possible, and factors
    """
    # Calculate usable roof area
    base_area = config.roof_surface_m2
    
    # For gable roofs with both sides, double the area
    if config.roof_type == RoofType.GABLE and config.use_both_sides:
        effective_area = base_area * 2
    else:
        effective_area = base_area
    
    # Apply usable fraction based on roof type
    usable_area = effective_area * USABLE_ROOF_FRACTION[config.roof_type]
    
    # Calculate maximum possible capacity from roof area (kWp)
    max_capacity_from_roof = (usable_area * PANEL_WATTS_PER_M2) / 1000
    
    # Get efficiency factors
    orientation_factor = ORIENTATION_FACTORS.get(config.orientation, 0.8)
    
    # Interpolate inclination factor
    inclination_keys = sorted(INCLINATION_FACTORS.keys())
    inclination = config.roof_inclination
    if inclination <= inclination_keys[0]:
        inclination_factor = INCLINATION_FACTORS[inclination_keys[0]]
    elif inclination >= inclination_keys[-1]:
        inclination_factor = INCLINATION_FACTORS[inclination_keys[-1]]
    else:
        # Linear interpolation
        lower = max(k for k in inclination_keys if k <= inclination)
        upper = min(k for k in inclination_keys if k >= inclination)
        if lower == upper:
            inclination_factor = INCLINATION_FACTORS[lower]
        else:
            ratio = (inclination - lower) / (upper - lower)
            inclination_factor = (
                INCLINATION_FACTORS[lower] * (1 - ratio) + 
                INCLINATION_FACTORS[upper] * ratio
            )
    
    # Combined efficiency factor
    efficiency_factor = orientation_factor * inclination_factor
    
    # Rule of thumb: 1 kWp produces ~950 kWh/year in Luxembourg
    annual_yield_per_kwp = 950 * efficiency_factor
    
    # Calculate ideal size to cover consumption (aim for ~100% coverage)
    ideal_size_for_consumption = config.yearly_consumption_kwh / annual_yield_per_kwp
    
    # Recommended size is minimum of roof capacity and consumption-based ideal
    recommended_kwp = min(max_capacity_from_roof, ideal_size_for_consumption)
    
    # Round to nearest 0.5 kWp
    recommended_kwp = round(recommended_kwp * 2) / 2
    
    # Ensure minimum of 2 kWp and maximum of 30 kWp
    recommended_kwp = max(2.0, min(30.0, recommended_kwp))
    max_capacity_from_roof = max(2.0, min(30.0, max_capacity_from_roof))
    
    return {
        "recommended_kwp": recommended_kwp,
        "max_from_roof_kwp": round(max_capacity_from_roof * 2) / 2,
        "usable_roof_area_m2": round(usable_area, 1),
        "efficiency_factor": round(efficiency_factor, 2),
        "orientation_factor": round(orientation_factor, 2),
        "inclination_factor": round(inclination_factor, 2),
        "estimated_annual_production_kwh": round(recommended_kwp * annual_yield_per_kwp, 0),
        "coverage_percent": round(
            (recommended_kwp * annual_yield_per_kwp / config.yearly_consumption_kwh) * 100, 0
        ),
    }


@dataclass
class PVSystem:
    """Solar PV system configuration."""
    capacity_kwp: float = 0.0
    enabled: bool = False
    # Extended configuration from sizing
    orientation: Orientation = Orientation.SOUTH
    roof_inclination: int = 30
    efficiency_factor: float = 1.0


@dataclass
class Battery:
    """Battery storage configuration."""
    capacity_kwh: float = 0.0
    enabled: bool = False
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    max_charge_rate: float = 0.5  # Fraction of capacity per hour
    max_discharge_rate: float = 0.5


@dataclass
class EV:
    """Electric vehicle configuration."""
    battery_capacity_kwh: float = 60.0  # Typical EV battery size
    enabled: bool = False
    charging_power_kw: float = 4.0  # Home charger power (typical single-phase)
    charging_start_hour: int = 18
    charging_end_hour: int = 7  # Next day
    starting_soc_pct: float = 0.40  # Assume EV arrives home at 40% SOC
    target_soc_pct: float = 0.80  # Charge to 80% (better for battery longevity)


# Default solar generation profile (fraction of peak by hour)
DEFAULT_PV_PROFILE = np.array([
    0.00, 0.00, 0.00, 0.00, 0.00, 0.00,  # 00-05
    0.05, 0.15, 0.35, 0.55, 0.75, 0.90,  # 06-11
    1.00, 0.95, 0.85, 0.70, 0.50, 0.30,  # 12-17
    0.15, 0.05, 0.00, 0.00, 0.00, 0.00   # 18-23
])

# Monthly seasonal factors for solar production
SEASONAL_FACTORS = {
    1: 0.30,   # January
    2: 0.40,   # February
    3: 0.60,   # March
    4: 0.80,   # April
    5: 0.95,   # May
    6: 1.00,   # June
    7: 1.00,   # July
    8: 0.95,   # August
    9: 0.75,   # September
    10: 0.50,  # October
    11: 0.35,  # November
    12: 0.25   # December
}

# Annual yield per kWp for Luxembourg region
ANNUAL_YIELD_PER_KWP = 950  # kWh


def simulate_pv_generation(
    df: pd.DataFrame,
    pv: PVSystem,
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Simulate PV generation based on consumption data timestamps.
    
    Args:
        df: DataFrame with timestamp index
        pv: PV system configuration
        config: Optional tariff config with PV parameters
    
    Returns:
        DataFrame with additional pv_generation_kwh column
    """
    result = df.copy()
    
    if not pv.enabled or pv.capacity_kwp <= 0:
        result["pv_generation_kwh"] = 0.0
        return result
    
    # Get hourly profile
    hours = result.index.hour
    months = result.index.month
    
    # Calculate base generation for each 15-min interval
    hourly_fraction = np.array([DEFAULT_PV_PROFILE[h] for h in hours])
    seasonal_fraction = np.array([SEASONAL_FACTORS[m] for m in months])
    
    # Apply efficiency factor from orientation and inclination
    efficiency = pv.efficiency_factor
    
    # Total annual generation expectation (adjusted by efficiency)
    total_annual_kwh = pv.capacity_kwp * ANNUAL_YIELD_PER_KWP * efficiency
    
    # Number of 15-min intervals in a year
    intervals_per_year = 365.25 * 24 * 4
    
    # Base generation per interval (before profile adjustments)
    # We scale so the integral over the year equals expected production
    # The profile sum (average over year considering seasonality)
    avg_hourly_profile = DEFAULT_PV_PROFILE.mean()
    avg_seasonal = np.mean(list(SEASONAL_FACTORS.values()))
    
    # Scale factor to achieve correct annual production
    # Each 15-min interval = 0.25 hours
    base_per_interval = total_annual_kwh / (intervals_per_year * avg_hourly_profile * avg_seasonal)
    
    # Calculate generation
    generation = base_per_interval * hourly_fraction * seasonal_fraction * 0.25
    
    # Add some random variation (cloud cover simulation, +/- 20%)
    np.random.seed(42)  # Reproducible
    variation = 1 + (np.random.random(len(generation)) - 0.5) * 0.4
    generation = generation * variation
    
    # Ensure non-negative
    generation = np.maximum(generation, 0)
    
    result["pv_generation_kwh"] = generation
    
    return result


def simulate_ev_consumption(
    df: pd.DataFrame,
    ev: EV,
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Simulate EV charging based on battery capacity and charging schedule.
    
    The EV arrives home each day at the charging start hour with a depleted
    battery (starting_soc_pct) and charges until reaching target_soc_pct
    or until the charging window ends.
    
    Args:
        df: DataFrame with timestamp index
        ev: EV configuration with battery capacity and charging schedule
        config: Optional tariff config with EV parameters
    
    Returns:
        DataFrame with ev_consumption_kwh and ev_soc columns
    """
    result = df.copy()
    
    if not ev.enabled or ev.battery_capacity_kwh <= 0:
        result["ev_consumption_kwh"] = 0.0
        result["ev_soc"] = 0.0
        return result
    
    hours = result.index.hour
    n = len(result)
    
    # Energy needed per charging session (from starting SOC to target SOC)
    energy_needed_per_session = ev.battery_capacity_kwh * (ev.target_soc_pct - ev.starting_soc_pct)
    
    # Maximum energy per 15-min interval based on charging power
    max_energy_per_interval = ev.charging_power_kw * 0.25  # kWh per 15-min
    
    # Initialize arrays
    ev_consumption = np.zeros(n)
    ev_soc = np.zeros(n)
    
    # Track current EV SOC within a charging session
    current_ev_soc = 0.0  # Not at home initially
    is_charging_session_active = False
    
    for i in range(n):
        hour = hours[i]
        
        # Check if we're in the charging window
        if ev.charging_start_hour > ev.charging_end_hour:
            # Overnight charging (e.g., 18:00 to 07:00)
            in_charging_window = (hour >= ev.charging_start_hour) or (hour < ev.charging_end_hour)
        else:
            in_charging_window = (ev.charging_start_hour <= hour < ev.charging_end_hour)
        
        # Detect start of new charging session (EV arrives home)
        if in_charging_window:
            # Check if this is the first interval of a new session
            if not is_charging_session_active:
                # New day's charging session starts - EV arrives at starting_soc_pct
                current_ev_soc = ev.battery_capacity_kwh * ev.starting_soc_pct
                is_charging_session_active = True
            
            # Calculate how much more we need to charge
            target_energy = ev.battery_capacity_kwh * ev.target_soc_pct
            energy_to_target = target_energy - current_ev_soc
            
            if energy_to_target > 0:
                # Charge the EV (limited by charging power and remaining need)
                charge_amount = min(max_energy_per_interval, energy_to_target)
                ev_consumption[i] = charge_amount
                current_ev_soc += charge_amount
            
            ev_soc[i] = current_ev_soc
        else:
            # Outside charging window - EV is away or not charging
            is_charging_session_active = False
            ev_soc[i] = 0.0  # EV not at home / not connected
    
    result["ev_consumption_kwh"] = ev_consumption
    result["ev_soc"] = ev_soc
    
    return result


def simulate_battery_operation(
    df: pd.DataFrame,
    battery: Battery,
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Simulate battery charge/discharge to maximize self-consumption.
    
    Strategy: Charge when PV > consumption, discharge when consumption > PV.
    
    Args:
        df: DataFrame with consumption and PV generation columns
        battery: Battery configuration
        config: Optional tariff config
    
    Returns:
        DataFrame with battery_charge_kwh, battery_discharge_kwh, and soc columns
    """
    result = df.copy()
    
    if not battery.enabled or battery.capacity_kwh <= 0:
        result["battery_charge_kwh"] = 0.0
        result["battery_discharge_kwh"] = 0.0
        result["battery_soc"] = 0.0
        return result
    
    # Ensure PV column exists
    if "pv_generation_kwh" not in result.columns:
        result["pv_generation_kwh"] = 0.0
    
    # Ensure EV column exists  
    if "ev_consumption_kwh" not in result.columns:
        result["ev_consumption_kwh"] = 0.0
    
    # Calculate net load (positive = need power, negative = excess PV)
    total_consumption = result["consumption_kwh"] + result["ev_consumption_kwh"]
    net_load = total_consumption - result["pv_generation_kwh"]
    
    # Maximum charge/discharge per 15-min interval
    max_charge = battery.capacity_kwh * battery.max_charge_rate * 0.25
    max_discharge = battery.capacity_kwh * battery.max_discharge_rate * 0.25
    
    # Initialize arrays
    n = len(result)
    charge = np.zeros(n)
    discharge = np.zeros(n)
    soc = np.zeros(n)
    
    # Start at 50% SOC
    current_soc = battery.capacity_kwh * 0.5
    
    for i in range(n):
        if net_load.iloc[i] < 0:
            # Excess PV - charge battery
            excess = -net_load.iloc[i]
            available_capacity = battery.capacity_kwh - current_soc
            charge_amount = min(excess, max_charge, available_capacity / battery.charge_efficiency)
            charge[i] = charge_amount
            current_soc += charge_amount * battery.charge_efficiency
        else:
            # Need power - discharge battery
            needed = net_load.iloc[i]
            available_energy = current_soc * battery.discharge_efficiency
            discharge_amount = min(needed, max_discharge, available_energy)
            discharge[i] = discharge_amount
            current_soc -= discharge_amount / battery.discharge_efficiency
        
        soc[i] = current_soc
    
    result["battery_charge_kwh"] = charge
    result["battery_discharge_kwh"] = discharge
    result["battery_soc"] = soc
    
    return result


def calculate_grid_exchange(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate grid import and export after all assets.
    
    The battery stores EXCESS PV (reduces export) and provides power when 
    needed (reduces import). Grid exchange is calculated as:
    
    - Grid Import = What we still need after PV and battery discharge
    - Grid Export = Excess PV that couldn't be stored in battery
    
    Args:
        df: DataFrame with all consumption and generation columns
    
    Returns:
        DataFrame with grid_import_kwh and grid_export_kwh columns
    """
    result = df.copy()
    
    # Ensure all columns exist with defaults
    for col in ["pv_generation_kwh", "ev_consumption_kwh", 
                "battery_charge_kwh", "battery_discharge_kwh"]:
        if col not in result.columns:
            result[col] = 0.0
    
    # Total load (what the house + EV needs)
    total_load = result["consumption_kwh"] + result["ev_consumption_kwh"]
    
    # Net load after PV (positive = need more, negative = excess PV)
    net_after_pv = total_load - result["pv_generation_kwh"]
    
    # Battery helps by:
    # - Discharging when we need power (reduces import)
    # - Charging from excess PV (reduces export)
    
    # Final grid position:
    # - We import when: net_after_pv > battery_discharge (still need more)
    # - We export when: excess_pv > battery_charge (couldn't store it all)
    
    # Grid import = load - pv - battery_discharge (if positive)
    grid_import = net_after_pv - result["battery_discharge_kwh"]
    result["grid_import_kwh"] = np.maximum(grid_import, 0)
    
    # Grid export = pv - load - battery_charge (if positive)  
    # This is the excess PV that didn't go to load or battery
    excess_pv = -net_after_pv  # Positive when PV > load
    grid_export = excess_pv - result["battery_charge_kwh"]
    result["grid_export_kwh"] = np.maximum(grid_export, 0)
    
    return result


def simulate_all_assets(
    consumption_df: pd.DataFrame,
    pv: PVSystem,
    battery: Battery,
    ev: EV,
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Run full simulation with all assets.
    
    Args:
        consumption_df: Base consumption DataFrame
        pv: PV system configuration
        battery: Battery configuration
        ev: EV configuration
        config: Optional tariff/asset config
    
    Returns:
        DataFrame with all simulated columns
    """
    # Start with consumption data
    result = consumption_df.copy()
    
    # Add PV generation
    result = simulate_pv_generation(result, pv, config)
    
    # Add EV consumption
    result = simulate_ev_consumption(result, ev, config)
    
    # Add battery operation (needs PV and consumption data)
    result = simulate_battery_operation(result, battery, config)
    
    # Calculate final grid exchange
    result = calculate_grid_exchange(result)
    
    return result


def get_self_sufficiency_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate self-sufficiency and self-consumption metrics.
    
    Args:
        df: DataFrame with simulation results
    
    Returns:
        Dictionary with metrics
    """
    total_consumption = df["consumption_kwh"].sum()
    ev_consumption = df.get("ev_consumption_kwh", pd.Series([0])).sum()
    total_load = total_consumption + ev_consumption
    
    pv_generation = df.get("pv_generation_kwh", pd.Series([0])).sum()
    grid_import = df.get("grid_import_kwh", pd.Series([total_load])).sum()
    grid_export = df.get("grid_export_kwh", pd.Series([0])).sum()
    
    # Battery metrics
    battery_charge = df.get("battery_charge_kwh", pd.Series([0])).sum()
    battery_discharge = df.get("battery_discharge_kwh", pd.Series([0])).sum()
    
    # Self-sufficiency: % of consumption covered by own generation
    if total_load > 0:
        self_sufficiency = (1 - grid_import / total_load) * 100
    else:
        self_sufficiency = 0
    
    # Self-consumption: % of PV used directly (not exported)
    if pv_generation > 0:
        self_consumption = ((pv_generation - grid_export) / pv_generation) * 100
    else:
        self_consumption = 0
    
    return {
        "self_sufficiency_pct": round(max(0, min(100, self_sufficiency)), 1),
        "self_consumption_pct": round(max(0, min(100, self_consumption)), 1),
        "total_pv_generation_kwh": round(pv_generation, 1),
        "grid_import_kwh": round(grid_import, 1),
        "grid_export_kwh": round(grid_export, 1),
        "total_consumption_kwh": round(total_load, 1),
        "battery_charged_kwh": round(battery_charge, 1),
        "battery_discharged_kwh": round(battery_discharge, 1),
    }

