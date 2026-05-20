WIND_THRESHOLDS = {
    "Clear": 5,
    "Windy": 10,
    "Storm": 13,
    "Blizzard": 15,
}


def apply_rules(drones, scenario):
    required_wind = WIND_THRESHOLDS[scenario["weather"]]
    passed, eliminated = [], []

    for drone in drones:
        reasons = []

        if drone["wind_resistance"] < required_wind:
            reasons.append(
                f"Wind resistance too low ({drone['wind_resistance']} m/s, need {required_wind} m/s)"
            )

        if scenario["time_of_day"] == "Night" and not drone["thermal"] and not drone["night_vision"]:
            reasons.append("No thermal or night vision camera for night operation")

        if scenario["altitude"] > drone["max_altitude"]:
            reasons.append(
                f"Cannot reach altitude ({drone['max_altitude']:,} m max, need {scenario['altitude']:,} m)"
            )

        if scenario["distance"] > drone["max_range"]:
            reasons.append(
                f"Range too short ({drone['max_range']} km max, need {scenario['distance']} km)"
            )

        if scenario["supply_weight"] > 0 and drone["payload"] < scenario["supply_weight"]:
            reasons.append(
                f"Payload too low ({drone['payload']} kg max, need {scenario['supply_weight']} kg)"
            )

        if drone["cost"] > scenario["budget"]:
            reasons.append(f"Over budget (€{drone['cost']}, limit €{scenario['budget']})")

        if reasons:
            eliminated.append({**drone, "reasons": reasons})
        else:
            passed.append(drone)

    return passed, eliminated


def get_weights(scenario):
    w = {
        "wind_resistance": 1.0,
        "altitude": 1.0,
        "battery": 1.0,
        "range": 1.0,
        "payload": 0.5,
        "speed": 1.0,
        "camera": 1.0,
        "cost": 1.0,
    }

    if scenario["weather"] == "Blizzard":
        w["wind_resistance"] = 4.0
    elif scenario["weather"] == "Storm":
        w["wind_resistance"] = 3.0
    elif scenario["weather"] == "Windy":
        w["wind_resistance"] = 2.0

    if scenario["time_of_day"] == "Night":
        w["camera"] = 3.5

    if scenario["altitude"] > 3000:
        w["altitude"] = 3.0
    elif scenario["altitude"] > 1500:
        w["altitude"] = 2.0

    if scenario["area"] > 15:
        w["battery"] = 3.0
        w["range"] = 3.0
        w["speed"] = 2.0
    elif scenario["area"] > 5:
        w["battery"] = 2.0
        w["range"] = 2.0

    if scenario["supply_weight"] > 0:
        w["payload"] = 4.0
        w["speed"] = 2.0

    return w


def score_drone(drone, weights):
    s = {
        "wind_resistance": min(10, (drone["wind_resistance"] / 15) * 10),
        "altitude": min(10, (drone["max_altitude"] / 5000) * 10),
        "battery": min(10, (drone["battery_life"] / 90) * 10),
        "range": min(10, (drone["max_range"] / 25) * 10),
        "payload": min(10, (drone["payload"] / 40) * 10) if drone["payload"] > 0 else 2.0,
        "speed": min(10, (drone["speed"] / 110) * 10),
        "camera": 10 if (drone["thermal"] and drone["night_vision"]) else 7 if (drone["thermal"] or drone["night_vision"]) else 3,
        "cost": max(0, 10 - (drone["cost"] / 500) * 10),
    }

    total = sum(s[k] * weights[k] for k in s)
    max_possible = sum(10 * weights[k] for k in weights)
    return round((total / max_possible) * 100, 1)


def score_drones(drones, scenario):
    weights = get_weights(scenario)
    result = [{**d, "score": score_drone(d, weights)} for d in drones]
    return sorted(result, key=lambda x: x["score"], reverse=True)


def get_num_drones(area):
    if area > 15:
        return 3
    if area > 5:
        return 2
    return 1
