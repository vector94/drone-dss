from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

from .layers import FocusMap, build_overlay
from .utils import init_pin


def render_map(
    dark: bool = True,
    mode: str = "Mission Pin",
    hq_lat: float | None = None,
    hq_lon: float | None = None,
    area_km2: float = 5.0,
) -> dict | None:
    """
    Render the SAR mission map.

    Returns {"lat", "lon"} on a new click, None otherwise.
    """
    init_pin()

    pin_lat  = st.session_state["map_lat"]
    pin_lon  = st.session_state["map_lon"]
    view_lat = st.session_state["map_view_lat"]
    view_lon = st.session_state["map_view_lon"]
    zoom     = st.session_state["map_zoom"]

    m = folium.Map(
        location=[view_lat, view_lon],
        zoom_start=zoom,
        tiles="CartoDB dark_matter" if dark else "CartoDB positron",
        doubleClickZoom=False,
    )
    FocusMap().add_to(m)

    fg = build_overlay(pin_lat, pin_lon, hq_lat, hq_lon, area_km2, mode)

    out = st_folium(
        m,
        feature_group_to_add=fg,
        use_container_width=True,
        height=400,
        returned_objects=["last_clicked"],
        key="mission_map",
    )

    if out and out.get("last_clicked"):
        c = out["last_clicked"]
        new_lat = round(c["lat"], 5)
        new_lon = round(c["lng"], 5)
        if st.session_state["map_last_click"] != (new_lat, new_lon):
            st.session_state["map_last_click"] = (new_lat, new_lon)
            return {"lat": new_lat, "lon": new_lon}

    return None
