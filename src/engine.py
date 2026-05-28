# ── REFERENCE MAXIMUMS for 0-100 normalisation ─────────────────────────────────
# These represent "excellent" performance ceilings, not hard limits.
_MAX_BATTERY  = 120    # min  — endurance benchmark
_MAX_RANGE    = 80     # km   — long-range benchmark
_MAX_WIND     = 25     # m/s  — high wind resistance benchmark
_MAX_PAYLOAD  = 20     # kg   — heavy-lift benchmark
_MAX_ALTITUDE = 8_000  # m    — high-altitude benchmark
_MAX_SPEED    = 200    # km/h — fast fixed-wing benchmark

# km of flight needed to survey 1 km² (assumes ~167 m camera/sensor swath width)
_KM_PER_KM2 = 6.0

# Fallback wind speed (m/s) when no live weather data is available
_WIND_FALLBACK = {"Clear": 2.0, "Windy": 8.0, "Storm": 14.0, "Blizzard": 12.0}

# Fallback temperature (°C) when no live weather data is available
_TEMP_FALLBACK = {"Clear": 15.0, "Windy": 10.0, "Storm": 5.0, "Blizzard": -10.0}


# ── FILTERING ───────────────────────────────────────────────────────────────────

def apply_rules(drones: list[dict], scenario: dict) -> tuple[list, list]:
    """
    Apply expert elimination rules (Rules 2-8 from the DSS model).
    Rule 1 (available / not in mission) is enforced at CSV load time in drones.py.

    Returns (passed, eliminated) where eliminated entries carry a 'reasons' list.
    """
    wind_speed  = scenario.get("wind_speed")  or _WIND_FALLBACK[scenario["weather"]]
    temperature = scenario.get("temperature") or _TEMP_FALLBACK[scenario["weather"]]
    is_night    = scenario["time_of_day"] == "Night"

    passed, eliminated = [], []

    for drone in drones:
        reasons = []

        # Rule 2 — Wind resistance
        if drone["wind_resistance"] < wind_speed:
            reasons.append(
                f"Wind resistance too low "
                f"({drone['wind_resistance']} m/s available, {wind_speed} m/s required)"
            )

        # Rule 3 — Temperature tolerance
        if temperature < drone["temp_min"] or temperature > drone["temp_max"]:
            reasons.append(
                f"Temperature out of tolerance "
                f"({temperature}°C at location, tolerance {drone['temp_min']}…{drone['temp_max']}°C)"
            )

        # Rule 4 — Altitude ceiling
        if scenario["altitude"] > drone["max_altitude"]:
            reasons.append(
                f"Cannot reach mission altitude "
                f"({drone['max_altitude']:,} m ceiling, {scenario['altitude']:,} m required)"
            )

        # Rule 5 — Communication / travel range
        if scenario["distance"] > drone["max_range"]:
            reasons.append(
                f"Range too short "
                f"({drone['max_range']} km max, {scenario['distance']} km required)"
            )

        # Rule 6 — Battery vs estimated mission time
        est_time = _estimate_mission_time(drone["speed"], scenario["area"], scenario["distance"])
        if drone["battery_life"] < est_time:
            reasons.append(
                f"Battery insufficient "
                f"({drone['battery_life']} min, ~{est_time:.0f} min mission estimated)"
            )

        # Rule 7 — Payload capacity
        if scenario["supply_weight"] > 0 and drone["payload"] < scenario["supply_weight"]:
            reasons.append(
                f"Payload too low "
                f"({drone['payload']} kg max, {scenario['supply_weight']} kg required)"
            )

        # Rule 8 — Camera for night operations
        if is_night and not drone["thermal"] and not drone["night_vision"]:
            reasons.append("No thermal or night-vision camera for night operations")

        # Budget hard cap
        if drone["cost"] > scenario["budget"]:
            reasons.append(f"Over budget (€{drone['cost']}, limit €{scenario['budget']})")

        if reasons:
            eliminated.append({**drone, "reasons": reasons})
        else:
            passed.append(drone)

    return passed, eliminated


def _estimate_mission_time(speed_kmh: float, area_km2: float, distance_km: float) -> float:
    """
    Estimate minimum mission time (minutes) for a single drone.

    Survey leg  : area_km2 × _KM_PER_KM2 km of flight (systematic sweep)
    Transit leg : 2 × distance_km  (round trip to site)
    """
    survey_km = area_km2 * _KM_PER_KM2
    transit_km = 2.0 * distance_km
    return (survey_km + transit_km) / speed_kmh * 60.0


# ── SCORING ─────────────────────────────────────────────────────────────────────

def score_drones(drones: list[dict], scenario: dict) -> list[dict]:
    """
    Score all drones that passed filtering.

    Total score = Mission capability × 0.75
                + Swarm capability   × 0.15
                + Cost efficiency    × 0.10

    Returns drones sorted by total score descending, each with a 'score' key.
    """
    if not drones:
        return []

    num_drones = get_num_drones(scenario["area"])

    costs     = [d["cost"] for d in drones]
    max_cost  = max(costs)
    min_cost  = min(costs)

    result = []
    for drone in drones:
        mc    = _mission_capability_score(drone, scenario)
        swarm = _swarm_capability_score(drone, scenario, num_drones)
        cost  = _cost_efficiency_score(drone["cost"], max_cost, min_cost)

        total = round(mc * 0.75 + swarm * 0.15 + cost * 0.10, 1)
        result.append({**drone, "score": total})

    return sorted(result, key=lambda x: x["score"], reverse=True)


# ── MISSION CAPABILITY SCORE ────────────────────────────────────────────────────

def _mission_capability_score(drone: dict, scenario: dict) -> float:
    """
    Mission Capability Score (0-100).

    Base weights (model spec):
        Camera 0.25 · Battery 0.20 · Range 0.15 · Wind 0.15
        Payload 0.10 · Altitude 0.10 · Speed 0.05

    Scenario multipliers shift weights for extreme conditions, then
    the full weight vector is re-normalised to sum to 1.
    """
    scores = {
        "camera":   _camera_score(drone, scenario),
        "battery":  min(100.0, drone["battery_life"] / _MAX_BATTERY  * 100),
        "range":    min(100.0, drone["max_range"]    / _MAX_RANGE     * 100),
        "wind":     min(100.0, drone["wind_resistance"] / _MAX_WIND   * 100),
        "payload":  min(100.0, drone["payload"]      / _MAX_PAYLOAD   * 100),
        "altitude": min(100.0, drone["max_altitude"] / _MAX_ALTITUDE  * 100),
        "speed":    min(100.0, drone["speed"]        / _MAX_SPEED     * 100),
    }

    # Base weights from model specification
    w = {
        "camera":   0.25,
        "battery":  0.20,
        "range":    0.15,
        "wind":     0.15,
        "payload":  0.10,
        "altitude": 0.10,
        "speed":    0.05,
    }

    # Scenario multipliers
    weather = scenario["weather"]
    if weather == "Blizzard":
        w["wind"] *= 1.5
    elif weather == "Storm":
        w["wind"] *= 1.3

    if scenario["time_of_day"] == "Night":
        w["camera"] *= 1.5

    altitude = scenario["altitude"]
    if altitude > 3000:
        w["altitude"] *= 1.5
    elif altitude > 1500:
        w["altitude"] *= 1.2

    if scenario["supply_weight"] > 0:
        w["payload"] *= 1.5
        w["speed"]   *= 1.2

    area = scenario["area"]
    if area > 15:
        w["battery"] *= 1.3
        w["range"]   *= 1.3
        w["speed"]   *= 1.2
    elif area > 5:
        w["battery"] *= 1.15
        w["range"]   *= 1.15

    # Normalise so weights still sum to 1
    total_w = sum(w.values())
    w = {k: v / total_w for k, v in w.items()}

    return round(sum(scores[k] * w[k] for k in scores), 1)


def _camera_score(drone: dict, scenario: dict) -> float:
    """
    Camera suitability score (0-100) based on mission conditions.

    Day missions value thermal/NV as an enhancement.
    Night missions penalise missing thermal or night-vision capability.
    Drones with neither thermal nor NV at night are already eliminated by Rule 8.
    """
    has_thermal = drone["thermal"]
    has_nv      = drone["night_vision"]
    is_night    = scenario["time_of_day"] == "Night"

    if has_thermal and has_nv:
        return 100.0
    if has_thermal:
        return 65.0 if is_night else 85.0   # thermal only: less ideal at night
    if has_nv:
        return 70.0 if is_night else 80.0   # NV only
    return 50.0                             # RGB only (only reaches here in day)


# ── SWARM CAPABILITY SCORE ──────────────────────────────────────────────────────

def _swarm_capability_score(drone: dict, scenario: dict, num_drones: int) -> float:
    """
    Swarm Capability Score (0-100).

    When num_drones == 1 a single drone suffices → perfect swarm score.

    Otherwise:
        Availability     × 0.40  — enough units in inventory?
        Coverage         × 0.40  — can the swarm survey the full area?
        Payload redundancy × 0.20 — can the swarm carry the supply weight?
    """
    if num_drones == 1:
        return 100.0

    # Availability: inventory vs drones needed
    avail_score = min(100.0, drone["units_inventory"] / num_drones * 100)

    # Coverage: total area the swarm can sweep within battery life
    # Each drone covers (battery_hours × speed × 1/KM_PER_KM2) km²
    drone_coverage_km2 = (drone["battery_life"] / 60.0) * drone["speed"] / _KM_PER_KM2
    swarm_coverage_km2 = num_drones * drone_coverage_km2
    coverage_score     = min(100.0, swarm_coverage_km2 / scenario["area"] * 100)

    # Payload redundancy: can the swarm collectively carry the supply?
    supply = scenario["supply_weight"]
    if supply > 0:
        total_capacity   = num_drones * drone["payload"]
        payload_red_score = min(100.0, total_capacity / supply * 100)
    else:
        payload_red_score = 100.0

    return round(avail_score * 0.40 + coverage_score * 0.40 + payload_red_score * 0.20, 1)


# ── COST EFFICIENCY SCORE ───────────────────────────────────────────────────────

def _cost_efficiency_score(drone_cost: int, max_cost: int, min_cost: int) -> float:
    """
    Cost Efficiency Score (0-100) per model formula:
        100 × (highest_feasible_cost - drone_cost)
            / (highest_feasible_cost - lowest_feasible_cost)

    When all feasible drones have the same cost, every drone scores 100.
    """
    if max_cost == min_cost:
        return 100.0
    return round(100.0 * (max_cost - drone_cost) / (max_cost - min_cost), 1)


# ── SWARM SIZE ──────────────────────────────────────────────────────────────────

def get_num_drones(area_km2: float) -> int:
    """Number of drones needed to cover the mission area."""
    if area_km2 > 15:
        return 3
    if area_km2 > 5:
        return 2
    return 1
