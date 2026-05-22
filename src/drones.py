import os
import pandas as pd

_CSV_PATH = os.path.join(os.path.dirname(__file__), "sar_drones.csv")


def _infer_airframe(row) -> str:
    """Infer airframe category from drone_id and notes so app.py icon logic works."""
    text = f"{row['drone_name']} {row.get('notes', '')}".lower()
    drone_id = str(row["drone_id"]).lower()

    if "helicopter" in text:
        return "Helicopter"
    if "vtol" in drone_id or "vtol fixed-wing" in text:
        return "VTOL Fixed-wing"
    if "fixed-wing" in text or "fixed wing" in text:
        return "Fixed-wing"
    return "Multirotor"


def _load_drones(path: str) -> list[dict]:
    df = pd.read_csv(path)
    df = df[df["available"].astype(str).str.lower() == "true"].reset_index(drop=True)

    records = []
    for _, row in df.iterrows():
        notes = row.get("notes", "")
        description = (
            str(notes).strip()
            if pd.notna(notes) and str(notes).strip()
            else str(row.get("best_use", ""))
        )

        records.append({
            # Core fields used by engine.py and app.py
            "name":            row["drone_name"],
            "type":            _infer_airframe(row),
            "wind_resistance": float(row["wind_resistance_ms"]),
            "max_altitude":    int(row["altitude_capability_m"]),
            "battery_life":    int(row["battery_life_min"]),
            "max_range":       float(row["communication_range_km"]),
            "payload":         float(row["payload_capacity_kg"]),
            "speed":           float(row["speed_kmh"]),
            "thermal":         str(row["has_thermal"]).lower() == "true",
            "night_vision":    str(row["has_night_vision"]).lower() == "true",
            "cost":            int(row["operational_cost_eur_per_mission"]),
            "description":     description,
            # Extra fields available for display
            "manufacturer":    str(row["manufacturer"]),
            "archetype":       str(row["drone_archetype"]),
            "camera_type":     str(row["camera_type"]),
            "country":         str(row.get("country_of_origin", "")),
            "ndaa_compliant":  str(row.get("ndaa_compliant", "false")).lower() == "true",
            "ip_rating":       str(row.get("ip_rating", "")),
        })
    return records


DRONES = _load_drones(_CSV_PATH)
