import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
from datetime import datetime, timedelta

# =============================================================================
# Weather Data and Water Need Estimation Module
# =============================================================================
def fetch_weather_data(lat, lon, start_date, end_date):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "windspeed_10m_max",
            "relative_humidity_2m_max",
            "shortwave_radiation_sum"
        ],
        "timezone": "auto"
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()  # Raises HTTPError for bad responses
    data = response.json()

    if "daily" not in data or not data["daily"]:
        raise ValueError(
            f"Weather data is unavailable for the selected date range and location. Response: {data}"
        )

    df = pd.DataFrame({
        "date": pd.date_range(start=start_date, end=end_date).date,
        "tavg": (np.array(data["daily"]["temperature_2m_max"]) + np.array(data["daily"]["temperature_2m_min"])) / 2,
        "wspd": data["daily"]["windspeed_10m_max"],
        "rhum": data["daily"]["relative_humidity_2m_max"],
        "rad": data["daily"]["shortwave_radiation_sum"]
    })
    return df

def compute_penman_monteith(temp, wind, rh, rad, elevation=0):
    """
    Computes the reference evapotranspiration (ET0) using the Penman–Monteith equation.

    Parameters:
      - temp: Average temperature (°C)
      - wind: Wind speed at 10 m (m/s)
      - rh: Relative humidity (%)
      - rad: Shortwave radiation sum (MJ/m²/day)
      - elevation: Elevation in meters (default=0)

    Returns:
      - ET0 in mm/day
    """
    temp_k = temp + 273.15
    delta = (4098 * (0.6108 * np.exp((17.27 * temp) / (temp + 237.3)))) / ((temp + 237.3) ** 2)

    # Adjust atmospheric pressure based on elevation.
    # Standard sea-level pressure is ~101.3 kPa.
    P = 101.3 * ((293 - 0.0065 * elevation) / 293) ** 5.26  # in kPa
    gamma = 0.665 * 0.001 * P  # Psychrometric constant in kPa/°C

    e_s = 0.6108 * np.exp((17.27 * temp) / (temp + 237.3))
    e_a = (rh / 100) * e_s
    # rad is assumed to be in MJ/m²/day (no conversion needed)
    rad_mj = rad

    et_0 = (0.408 * delta * rad_mj + gamma * (900 / temp_k) * wind * (e_s - e_a)) / (delta + gamma * (1 + 0.34 * wind))
    return max(et_0, 0)

def estimate_water_needs(lat, lon, start_date, end_date, park_area, kc=0.8, elevation=0):
    """
    Estimates the water needs for a given park area over a specified date range.

    Parameters:
      - lat: Latitude of the location
      - lon: Longitude of the location
      - start_date: Start date (datetime object)
      - end_date: End date (datetime object)
      - park_area: Area of the park in m²
      - kc: Crop coefficient (default=0.8)
      - elevation: Elevation in meters (default=0)

    Returns:
      - DataFrame with columns: date, ET0, ETc, and Water_Need_m3
    """
    weather_data = fetch_weather_data(lat, lon, start_date, end_date)

    weather_data['ET0'] = weather_data.apply(
        lambda row: compute_penman_monteith(row['tavg'], row['wspd'], row['rhum'], row['rad'], elevation),
        axis=1
    )
    weather_data['ETc'] = weather_data['ET0'] * kc
    weather_data['water_need_m3'] = (weather_data['ETc'] * park_area / 1000).round(decimals=4)
    return weather_data[['date', 'ET0', 'ETc', 'water_need_m3']]

if __name__ == "__main__":
    lat, lon = 39.9, 32.85  # Ankara, Turkey
    start_date = datetime(2024, 8, 1)
    end_date = datetime(2024, 8, 30)
    park_area = 1000  # m²
    elevation = 938  # Approximate elevation for Ankara in meters (optional)

    water_needs = estimate_water_needs(lat, lon, start_date, end_date, park_area, kc=1, elevation=elevation)
    total_water_need = water_needs['water_need_m3'].sum()
    average_et0 = water_needs['ET0'].mean()
    average_etc = water_needs['ETc'].mean()
    average_water_need = water_needs['water_need_m3'].mean()

    # Display the detailed water needs per day
    print(water_needs.to_string(index=False))

    # Display total water need
    print(f"\nTotal Water Need for the period: {total_water_need} m³")

    # Display average values
    print(f"Average ET0 (mm/day): {average_et0:.2f}")
    print(f"Average ETc (mm/day): {average_etc:.2f}")
    print(f"Average Daily Water Need: {average_water_need:.2f} m³/day")