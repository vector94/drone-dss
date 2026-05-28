from __future__ import annotations

import math

import folium
from branca.element import MacroElement
from jinja2 import Template

from .utils import haversine


class FocusMap(MacroElement):
    """Focuses the Leaflet container on map ready so the first click registers."""
    _template = Template("""
        {% macro script(this, kwargs) %}
        {{ this._parent.get_name() }}.whenReady(function () {
            var el = document.querySelector('.leaflet-container');
            if (el) {
                el.setAttribute('tabindex', '0');
                el.focus({ preventScroll: true });
            }
        });
        {% endmacro %}
    """)


def build_overlay(
    pin_lat: float,
    pin_lon: float,
    hq_lat: float | None,
    hq_lon: float | None,
    area_km2: float,
    mode: str,
) -> folium.FeatureGroup:
    """
    Build the dynamic FeatureGroup containing all SAR map elements:
    search-area circle, flight-path line, HQ marker, and mission pin.
    Passed to st_folium via feature_group_to_add so the base map is never
    reinitialised and zoom/pan are preserved across reruns.
    """
    fg = folium.FeatureGroup(name="sar_overlay")

    # Search area circle
    if area_km2 > 0:
        radius_m = math.sqrt(area_km2 / math.pi) * 1000
        folium.Circle(
            location=[pin_lat, pin_lon],
            radius=radius_m,
            color="#3B82F6",
            fill=True,
            fill_color="#3B82F6",
            fill_opacity=0.10,
            weight=2,
            dash_array="6 4",
            tooltip=f"Search area · {area_km2} km²  ·  radius ≈ {radius_m / 1000:.2f} km",
        ).add_to(fg)

    # Flight path line + HQ marker
    if hq_lat is not None and hq_lon is not None:
        dist_km = haversine(hq_lat, hq_lon, pin_lat, pin_lon)
        folium.PolyLine(
            locations=[[hq_lat, hq_lon], [pin_lat, pin_lon]],
            color="#3B82F6",
            weight=2,
            dash_array="8 6",
            opacity=0.75,
            tooltip=f"Flight distance · {dist_km} km",
        ).add_to(fg)

        folium.Marker(
            location=[hq_lat, hq_lon],
            tooltip="HQ — Drone base",
            icon=folium.DivIcon(
                html=(
                    '<div style="width:14px;height:14px;box-sizing:border-box;'
                    "background:#3B82F6;border:2.5px solid #ffffff;"
                    "border-radius:3px;"
                    "box-shadow:0 0 10px rgba(59,130,246,0.85),"
                    "0 0 20px rgba(59,130,246,0.4);"
                    'pointer-events:none;"></div>'
                ),
                icon_size=(14, 14),
                icon_anchor=(7, 7),
            ),
        ).add_to(fg)

    # Mission pin
    _tip = (
        "Click to place HQ base"
        if mode == "HQ Base"
        else "Mission location — click anywhere to reposition"
    )
    folium.Marker(
        location=[pin_lat, pin_lon],
        tooltip=_tip,
        icon=folium.DivIcon(
            html=(
                '<div style="width:14px;height:14px;box-sizing:border-box;'
                "background:#ff4b4b;border:2.5px solid #ffffff;"
                "border-radius:50%;"
                "box-shadow:0 0 10px rgba(255,75,75,0.85),"
                "0 0 20px rgba(255,75,75,0.4);"
                'pointer-events:none;"></div>'
            ),
            icon_size=(14, 14),
            icon_anchor=(7, 7),
        ),
    ).add_to(fg)

    return fg
