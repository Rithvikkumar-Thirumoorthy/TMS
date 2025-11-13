"""
Base Solver Interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
from ..models import Store, Vehicle, Route, Solution


class BaseSolver(ABC):
    """Base class for all VRP solvers"""

    def __init__(
        self,
        stores: List[Store],
        vehicles: List[Vehicle],
        distance_matrix: Dict[str, Dict[str, float]],
        time_matrix: Dict[str, Dict[str, float]] = None,
        depot_id: str = "depot",
    ):
        self.stores = stores
        self.vehicles = vehicles
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix or {}
        self.depot_id = depot_id

        # Store lookup
        self.store_dict = {s.id: s for s in stores}
        self.vehicle_dict = {v.id: v for v in vehicles}

    @abstractmethod
    def solve(self, day: str, start_time: datetime = None, **kwargs) -> Solution:
        """
        Solve VRP for a single day
        Returns: Solution object
        """
        pass

    def _calculate_route_distance(self, route: Route) -> float:
        """Calculate total distance for a route"""
        if not route.stops:
            return 0.0

        total_distance = 0.0
        sequence = [stop.store.id for stop in route.stops]

        # Depot to first
        total_distance += self.distance_matrix.get(self.depot_id, {}).get(sequence[0], 0)

        # Between stops
        for i in range(len(sequence) - 1):
            total_distance += self.distance_matrix.get(sequence[i], {}).get(sequence[i + 1], 0)

        # Last to depot
        total_distance += self.distance_matrix.get(sequence[-1], {}).get(self.depot_id, 0)

        return total_distance

    def _update_route_metrics(self, route: Route):
        """Update distance and duration metrics for route"""
        route.total_distance_km = self._calculate_route_distance(route)

        # Calculate duration (travel + service time)
        if route.stops:
            total_service_time = sum(stop.store.service_time_minutes for stop in route.stops)

            # Estimate travel time based on distance (if no time matrix)
            if self.time_matrix:
                travel_time = self._calculate_route_time(route)
            else:
                # Estimate: 40 km/h average speed
                travel_time = (route.total_distance_km / 40.0) * 60

            route.total_duration_minutes = travel_time + total_service_time

    def _calculate_route_time(self, route: Route) -> float:
        """Calculate travel time for route (excluding service time)"""
        if not route.stops or not self.time_matrix:
            return 0.0

        total_time = 0.0
        sequence = [stop.store.id for stop in route.stops]

        # Depot to first
        total_time += self.time_matrix.get(self.depot_id, {}).get(sequence[0], 0)

        # Between stops
        for i in range(len(sequence) - 1):
            total_time += self.time_matrix.get(sequence[i], {}).get(sequence[i + 1], 0)

        # Last to depot
        total_time += self.time_matrix.get(sequence[-1], {}).get(self.depot_id, 0)

        return total_time

    def _create_solution(self, routes: List[Route], day: str) -> Solution:
        """Create solution object from routes"""
        solution = Solution(routes=routes, day=day)

        # Update metrics
        for route in routes:
            self._update_route_metrics(route)

        solution.compute_metrics()
        return solution
