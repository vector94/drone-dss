import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

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


def _init_pin() -> None:
    """Initialise pin + view state once per browser session."""
    if st.session_state.get("map_lat") is None:
        lat, lon = _ip_location()
        st.session_state["map_lat"] = lat
        st.session_state["map_lon"] = lon
    # View tracks where the user has panned/zoomed to; defaults to pin position
    if st.session_state.get("map_view_lat") is None:
        st.session_state["map_view_lat"] = st.session_state["map_lat"]
        st.session_state["map_view_lon"] = st.session_state["map_lon"]
    if st.session_state.get("map_zoom") is None:
        st.session_state["map_zoom"] = 8
    if "map_last_click" not in st.session_state:
        st.session_state["map_last_click"] = None


def render_map() -> dict | None:
    """
    Render an interactive Folium map for mission location selection.

    On first load the pin is placed at the user's approximate IP-geolocated
    position (fallback: Karlskrona, SE). Clicking anywhere repositions the pin
    and returns {"lat": float, "lon": float}. Panning and zooming are preserved
    across reruns. Returns None when nothing changed.
    """
    _init_pin()

    pin_lat  = st.session_state["map_lat"]
    pin_lon  = st.session_state["map_lon"]
    view_lat = st.session_state["map_view_lat"]
    view_lon = st.session_state["map_view_lon"]
    zoom     = st.session_state["map_zoom"]

    m = folium.Map(
        location=[view_lat, view_lon],
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
    )

    # Mission pin.
    # pointer-events:none on the div lets all clicks fall through to the map
    # background so that last_clicked fires on the very first click.
    folium.Marker(
        location=[pin_lat, pin_lon],
        tooltip="Mission location — click anywhere to reposition",
        icon=folium.DivIcon(
            html=(
                '<div style="width:14px;height:14px;'
                "background:#ff4b4b;border:2.5px solid #ffffff;"
                "border-radius:50%;"
                "box-shadow:0 0 10px rgba(255,75,75,0.85),"
                "0 0 20px rgba(255,75,75,0.4);"
                "pointer-events:none;"
                'margin:-7px 0 0 -7px;"></div>'
            ),
            icon_size=(14, 14),
            icon_anchor=(7, 7),
        ),
    ).add_to(m)

    out = st_folium(
        m,
        use_container_width=True,
        height=380,
        returned_objects=["last_clicked", "center", "zoom"],
        key="mission_map",
    )

    # Persist current view so panning/zooming survives reruns
    if out:
        if out.get("center"):
            st.session_state["map_view_lat"] = out["center"]["lat"]
            st.session_state["map_view_lon"] = out["center"]["lng"]
        if out.get("zoom") is not None:
            st.session_state["map_zoom"] = out["zoom"]

    # Detect a genuinely new click (deduplicate to stop rerun loops)
    if out and out.get("last_clicked"):
        c = out["last_clicked"]
        new_lat = round(c["lat"], 5)
        new_lon = round(c["lng"], 5)
        if st.session_state["map_last_click"] != (new_lat, new_lon):
            st.session_state["map_last_click"] = (new_lat, new_lon)
            return {"lat": new_lat, "lon": new_lon}

    return None
