import requests

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo WMO weather code groups
_SNOW_CODES = {71, 73, 75, 77, 85, 86}
_STORM_CODES = {95, 96, 99}


def fetch_weather(city: str) -> dict:
    """Fetch current weather for a city and map it to DSS condition categories.

    Returns:
        dict with keys: condition, time_of_day, wind_speed, location, elevation
    Raises:
        ValueError: city not found
        requests.HTTPError: API error
    """
    lat, lon, display_name, elevation = _geocode(city)

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
        "condition":   _map_condition(wind_speed, weather_code),
        "time_of_day": "Day" if is_day else "Night",
        "wind_speed":  wind_speed,
        "location":    display_name,
        "elevation":   elevation,
    }


def _geocode(city: str) -> tuple[float, float, str, int]:
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
    elevation = int(round(float(r.get("elevation") or 0)))
    return r["latitude"], r["longitude"], name, elevation


def _map_condition(wind_speed: float, weather_code: int) -> str:
    """Map wind speed (m/s) + WMO weather code to one of the four DSS categories."""
    if weather_code in _SNOW_CODES and wind_speed >= 10:
        return "Blizzard"
    if weather_code in _STORM_CODES or wind_speed >= 13:
        return "Storm"
    if wind_speed >= 5:
        return "Windy"
    return "Clear"
