from __future__ import annotations

import requests

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo WMO weather code groups
_SNOW_CODES = {71, 73, 75, 77, 85, 86}
_STORM_CODES = {95, 96, 99}


def fetch_weather(city: str) -> dict:
    """Fetch current weather for a city and map it to DSS condition categories.

    Returns:
        dict with keys: condition, time_of_day, wind_speed, location
    Raises:
        ValueError: city not found
        requests.HTTPError: API error
    """
    lat, lon, display_name = _geocode(city)

    resp = requests.get(
        _FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "wind_speed_10m,weather_code,is_day",
            "wind_speed_unit": "ms",
        },
        timeout=8,
    )
    resp.raise_for_status()
    current = resp.json()["current"]

    wind_speed = round(float(current["wind_speed_10m"]), 1)
    weather_code = int(current["weather_code"])
    is_day = bool(current["is_day"])

    return {
        "condition": _map_condition(wind_speed, weather_code),
        "time_of_day": "Day" if is_day else "Night",
        "wind_speed": wind_speed,
        "location": display_name,
        "lat": lat,
        "lon": lon,
    }


def _geocode(city: str) -> tuple[float, float, str]:
    resp = requests.get(
        _GEOCODE_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=8,
    )
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"Location '{city}' not found.")
    r = results[0]
    name = f"{r['name']}, {r.get('country_code', '')}"
    return r["latitude"], r["longitude"], name


def fetch_weather_by_coords(lat: float, lon: float) -> dict:
    """Fetch weather for explicit coordinates (skips city geocoding).

    Returns:
        dict with keys: condition, time_of_day, wind_speed, location, lat, lon
    Raises:
        requests.HTTPError: API error
    """
    resp = requests.get(
        _FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "wind_speed_10m,weather_code,is_day",
            "wind_speed_unit": "ms",
        },
        timeout=8,
    )
    resp.raise_for_status()
    current = resp.json()["current"]

    wind_speed = round(float(current["wind_speed_10m"]), 1)
    weather_code = int(current["weather_code"])
    is_day = bool(current["is_day"])

    return {
        "condition": _map_condition(wind_speed, weather_code),
        "time_of_day": "Day" if is_day else "Night",
        "wind_speed": wind_speed,
        "location": _reverse_geocode(lat, lon),
        "lat": lat,
        "lon": lon,
    }


def _reverse_geocode(lat: float, lon: float) -> str:
    """Resolve coordinates to a human-readable place name via Nominatim."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "SAR-Drone-DSS/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        address = resp.json().get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county", "")
        )
        country = address.get("country_code", "").upper()
        return f"{city}, {country}" if city else f"{lat:.4f}°, {lon:.4f}°"
    except Exception:
        return f"{lat:.4f}°N, {lon:.4f}°E"


def _map_condition(wind_speed: float, weather_code: int) -> str:
    """Map wind speed (m/s) + WMO weather code to one of the four DSS categories."""
    if weather_code in _SNOW_CODES and wind_speed >= 10:
        return "Blizzard"
    if weather_code in _STORM_CODES or wind_speed >= 13:
        return "Storm"
    if wind_speed >= 5:
        return "Windy"
    return "Clear"
