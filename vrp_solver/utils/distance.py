"""
Distance and Time Calculation Utilities
"""
import math
from typing import Dict, Tuple


class DistanceCalculator:
    """Calculate distances and times between locations"""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great circle distance between two points in kilometers
        Using Haversine formula
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in kilometers
        earth_radius_km = 6371.0

        return earth_radius_km * c

    @staticmethod
    def manhattan_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate Manhattan distance (approximation for city driving)
        """
        # Approximate degrees to km (rough estimate)
        km_per_degree_lat = 111.0
        km_per_degree_lon = 111.0 * math.cos(math.radians((lat1 + lat2) / 2))

        lat_diff = abs(lat2 - lat1) * km_per_degree_lat
        lon_diff = abs(lon2 - lon1) * km_per_degree_lon

        return lat_diff + lon_diff

    @staticmethod
    def build_distance_matrix(locations: Dict[str, Tuple[float, float]], method: str = "haversine") -> Dict[str, Dict[str, float]]:
        """
        Build a complete distance matrix for all locations
        locations: {location_id: (latitude, longitude)}
        Returns: {from_id: {to_id: distance_km}}
        """
        matrix = {}

        for loc1_id, (lat1, lon1) in locations.items():
            matrix[loc1_id] = {}
            for loc2_id, (lat2, lon2) in locations.items():
                if loc1_id == loc2_id:
                    matrix[loc1_id][loc2_id] = 0.0
                else:
                    if method == "haversine":
                        dist = DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)
                    elif method == "manhattan":
                        dist = DistanceCalculator.manhattan_distance(lat1, lon1, lat2, lon2)
                    else:
                        dist = DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)

                    matrix[loc1_id][loc2_id] = dist

        return matrix

    @staticmethod
    def build_time_matrix(distance_matrix: Dict[str, Dict[str, float]], avg_speed_kmh: float = 40.0) -> Dict[str, Dict[str, float]]:
        """
        Build time matrix from distance matrix
        Assumes average speed in km/h
        Returns: time in minutes
        """
        time_matrix = {}

        for from_id, destinations in distance_matrix.items():
            time_matrix[from_id] = {}
            for to_id, distance_km in destinations.items():
                time_minutes = (distance_km / avg_speed_kmh) * 60
                time_matrix[from_id][to_id] = time_minutes

        return time_matrix

    @staticmethod
    def calculate_route_distance(route_sequence: list, distance_matrix: Dict[str, Dict[str, float]], depot_id: str = "depot") -> float:
        """
        Calculate total distance for a route sequence
        route_sequence: list of location IDs (without depot)
        """
        if not route_sequence:
            return 0.0

        total_distance = 0.0

        # Depot to first location
        total_distance += distance_matrix.get(depot_id, {}).get(route_sequence[0], 0)

        # Between locations
        for i in range(len(route_sequence) - 1):
            from_loc = route_sequence[i]
            to_loc = route_sequence[i + 1]
            total_distance += distance_matrix.get(from_loc, {}).get(to_loc, 0)

        # Last location back to depot
        total_distance += distance_matrix.get(route_sequence[-1], {}).get(depot_id, 0)

        return total_distance
