def apply_rules(drones, scenario):
    passed, eliminated = [], []

    for drone in drones:
        reasons = []

        if not drone.get("available", True) or drone.get("in_mission", False):
            reasons.append("Drone is not available or busy in a mission")

        if drone["wind_resistance"] < scenario["wind_speed"]:
            reasons.append(
                f"Wind resistance too low ({drone['wind_resistance']} m/s, need {scenario['wind_speed']} m/s)"
            )

        temp_min = drone.get("temp_min", -20)
        temp_max = drone.get("temp_max", 50)
        if scenario["temperature"] < temp_min or scenario["temperature"] > temp_max:
            reasons.append(f"Temperature tolerance ({temp_min}°C to {temp_max}°C) does not cover mission temperature ({scenario['temperature']}°C)")

        if scenario["altitude"] > drone["max_altitude"]:
            reasons.append(
                f"Cannot reach altitude ({drone['max_altitude']:,} m max, need {scenario['altitude']:,} m)"
            )

        if scenario["distance"] > drone["max_range"]:
            reasons.append(
                f"Range too short ({drone['max_range']} km max, need {scenario['distance']} km)"
            )

        # Estimated mission time: (Area to cover / Drone speed in km/h) * 60 + (Distance / Drone speed) * 60 * 2 (Round trip)
        estimated_mission_time = (scenario["area"] / drone["speed"]) * 60 + (scenario["distance"] / drone["speed"]) * 60 * 2
        if drone["battery_life"] < estimated_mission_time:
            reasons.append(
                f"Battery life too short ({drone['battery_life']} min, estimated {estimated_mission_time:.1f} min)"
            )

        if scenario["supply_weight"] > 0 and drone["payload"] < scenario["supply_weight"]:
            reasons.append(
                f"Payload too low ({drone['payload']} kg max, need {scenario['supply_weight']} kg)"
            )

        if scenario["time_of_day"] == "Night":
            if scenario.get("dense_forest", False):
                if not drone["thermal"] or not drone["night_vision"]:
                    reasons.append("Dense forest at night requires BOTH thermal and night vision cameras")
            else:
                if not drone["thermal"] and not drone["night_vision"]:
                    reasons.append("Night operation requires at least thermal OR night vision camera")

        if reasons:
            eliminated.append({**drone, "reasons": reasons})
        else:
            passed.append(drone)

    return passed, eliminated


def get_num_drones(area):
    if area > 15:
        return 3
    if area > 5:
        return 2
    return 1


def score_drones(drones, scenario):
    if not drones:
        return []

    num_drones = get_num_drones(scenario["area"])
    
    # Calculate costs for Cost Efficiency Score
    drone_costs = [d["cost"] for d in drones]
    highest_cost = max(drone_costs)
    lowest_cost = min(drone_costs)
    
    result = []
    for drone in drones:
        # 1. Mission Capability Score
        s_camera = 100 if (drone["thermal"] and drone["night_vision"]) else 70 if (drone["thermal"] or drone["night_vision"]) else 30
        s_battery = min(100, (drone["battery_life"] / 90) * 100)
        s_range = min(100, (drone["max_range"] / 25) * 100)
        s_wind = min(100, (drone["wind_resistance"] / 15) * 100)
        s_payload = min(100, (drone["payload"] / 40) * 100) if drone["payload"] > 0 else 20.0
        s_altitude = min(100, (drone["max_altitude"] / 5000) * 100)
        s_speed = min(100, (drone["speed"] / 110) * 100)
        
        mission_score = (
            s_camera * 0.25 +
            s_battery * 0.20 +
            s_range * 0.15 +
            s_wind * 0.15 +
            s_payload * 0.10 +
            s_altitude * 0.10 +
            s_speed * 0.05
        )
        
        # 2. Swarm Capability Score
        availability = min(100.0, (drone.get("units_in_inventory", 0) / num_drones) * 100) if num_drones > 0 else 100.0
        
        mission_time_per_drone = (scenario["area"] / num_drones / drone["speed"]) * 60 + (scenario["distance"] / drone["speed"]) * 60 * 2
        coverage = min(100.0, (drone["battery_life"] / mission_time_per_drone) * 100) if mission_time_per_drone > 0 else 100.0
        
        if scenario["supply_weight"] > 0:
            payload_redundancy = min(100.0, (drone["payload"] * num_drones / scenario["supply_weight"]) * 100)
        else:
            payload_redundancy = 100.0
            
        swarm_score = availability * 0.40 + coverage * 0.40 + payload_redundancy * 0.20
        
        # 3. Cost Efficiency Score
        if highest_cost == lowest_cost:
            cost_score = 100.0
        else:
            cost_score = 100.0 * (highest_cost - drone["cost"]) / (highest_cost - lowest_cost)
            
        # Total Score
        total_score = mission_score * 0.75 + swarm_score * 0.15 + cost_score * 0.10
        
        result.append({
            **drone,
            "score": round(total_score, 1)
        })

    return sorted(result, key=lambda x: x["score"], reverse=True)
