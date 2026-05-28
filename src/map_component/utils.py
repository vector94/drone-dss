from __future__ import annotations

import math

import requests
import streamlit as st

_FALLBACK_LAT = 56.1800  # Karlskrona, SE (BTH campus)
_FALLBACK_LON = 15.5900


def _ip_location() -> tuple[float, float]:
    """Best-effort IP geolocation; returns Karlskrona fallback on any failure."""
    try:
        r = requests.get("https://ipapi.co/json/", timeout=2)
        r.raise_for_status()
        d = r.json()
        return float(d["latitude"]), float(d["longitude"])
    except Exception:
        return _FALLBACK_LAT, _FALLBACK_LON


def init_pin() -> None:
    """Initialise pin + view state once per browser session."""
    if st.session_state.get("map_lat") is None:
        lat, lon = _ip_location()
        st.session_state["map_lat"] = lat
        st.session_state["map_lon"] = lon
    if st.session_state.get("map_view_lat") is None:
        st.session_state["map_view_lat"] = st.session_state["map_lat"]
        st.session_state["map_view_lon"] = st.session_state["map_lon"]
    if st.session_state.get("map_zoom") is None:
        st.session_state["map_zoom"] = 8
    if "map_last_click" not in st.session_state:
        st.session_state["map_last_click"] = None


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)), 2)
