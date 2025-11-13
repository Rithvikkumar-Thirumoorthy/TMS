"""
Clarke-Wright Savings Algorithm for VRP
"""
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import copy
from .base_solver import BaseSolver
from ..models import Store, Vehicle, Route, Solution, RouteStop
from ..constraints import ConstraintValidator


class ClarkeWrightSolver(BaseSolver):
    """
    Clarke-Wright Savings Algorithm
    A classic heuristic for VRP that builds routes by merging based on savings
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = ConstraintValidator()

    def solve(self, day: str, start_time: datetime = None, **kwargs) -> Solution:
        """
        Solve VRP using Clarke-Wright Savings Algorithm

        Algorithm:
        1. Start with each customer in its own route
        2. Calculate savings for merging routes
        3. Merge routes in order of savings (highest first)
        4. Continue until no more feasible merges
        """
        if start_time is None:
            start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Filter stores that can be served on this day
        available_stores = [s for s in self.stores if s.is_day_allowed(day)]

        if not available_stores:
            return Solution(routes=[], day=day, unserved_stores=[s.id for s in self.stores])

        # Step 1: Create initial routes (each store in separate route)
        routes = self._create_initial_routes(available_stores, day, start_time)

        # Step 2: Calculate savings for all route pairs
        savings = self._calculate_savings(routes)

        # Step 3: Merge routes based on savings
        routes = self._merge_routes(routes, savings, day)

        # Step 4: Improve routes with 2-opt
        for route in routes:
            self._two_opt_improve(route)

        # Create solution
        solution = self._create_solution(routes, day)

        # Validate
        for route in routes:
            is_valid, violations = self.validator.validate_route(route, self.distance_matrix, self.time_matrix)
            if not is_valid:
                solution.is_feasible = False
                solution.constraint_violations.extend(violations)

        return solution

    def _create_initial_routes(self, stores: List[Store], day: str, start_time: datetime) -> List[Route]:
        """Create initial routes with one store per route"""
        routes = []

        for store in stores:
            # Find a compatible vehicle
            vehicle = self._find_compatible_vehicle(store, day)
            if vehicle is None:
                continue

            route = Route(vehicle=vehicle, day=day)
            route.depot_departure = start_time
            route.add_stop(store)

            # Update metrics
            self._update_route_metrics(route)

            routes.append(route)

        return routes

    def _find_compatible_vehicle(self, store: Store, day: str) -> Vehicle:
        """Find first compatible vehicle for store"""
        for vehicle in self.vehicles:
            if vehicle.can_serve_store(store.id) and vehicle.can_fit_demand(store.demand_cbm):
                return vehicle
        return None

    def _calculate_savings(self, routes: List[Route]) -> List[Tuple[int, int, float]]:
        """
        Calculate savings for all route pairs
        Savings(i,j) = dist(depot,i) + dist(depot,j) - dist(i,j)

        Returns: List of (route1_idx, route2_idx, savings) sorted by savings (descending)
        """
        savings_list = []

        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                route_i = routes[i]
                route_j = routes[j]

                # Can only merge if using same vehicle type and have capacity
                if route_i.vehicle.id != route_j.vehicle.id:
                    continue

                # Get last store of route i and first store of route j
                if not route_i.stops or not route_j.stops:
                    continue

                last_i = route_i.stops[-1].store.id
                first_j = route_j.stops[0].store.id

                # Calculate savings
                dist_depot_i = self.distance_matrix.get(self.depot_id, {}).get(last_i, 0)
                dist_depot_j = self.distance_matrix.get(self.depot_id, {}).get(first_j, 0)
                dist_i_j = self.distance_matrix.get(last_i, {}).get(first_j, 0)

                savings = dist_depot_i + dist_depot_j - dist_i_j

                if savings > 0:
                    savings_list.append((i, j, savings))

        # Sort by savings (descending)
        savings_list.sort(key=lambda x: x[2], reverse=True)

        return savings_list

    def _merge_routes(self, routes: List[Route], savings: List[Tuple[int, int, float]], day: str) -> List[Route]:
        """
        Merge routes based on savings
        """
        # Track which routes have been merged
        active_routes = {i: route for i, route in enumerate(routes)}

        for i, j, saving in savings:
            # Check if both routes still exist
            if i not in active_routes or j not in active_routes:
                continue

            route_i = active_routes[i]
            route_j = active_routes[j]

            # Check if merge is feasible
            if self._can_merge_routes(route_i, route_j, day):
                # Merge j into i
                merged_route = self._merge_two_routes(route_i, route_j)

                # Update active routes
                active_routes[i] = merged_route
                del active_routes[j]

        return list(active_routes.values())

    def _can_merge_routes(self, route1: Route, route2: Route, day: str) -> bool:
        """Check if two routes can be merged"""
        # 1. Must use same vehicle
        if route1.vehicle.id != route2.vehicle.id:
            return False

        # 2. Check capacity
        total_load = route1.total_load_cbm + route2.total_load_cbm
        if total_load > route1.vehicle.capacity_cbm:
            return False

        # 3. Create temporary merged route and check constraints
        temp_route = self._merge_two_routes(route1, route2)

        # Validate constraints
        is_valid, _ = self.validator.validate_route(temp_route, self.distance_matrix, self.time_matrix)

        return is_valid

    def _merge_two_routes(self, route1: Route, route2: Route) -> Route:
        """Merge two routes into one"""
        merged = Route(vehicle=route1.vehicle, day=route1.day)
        merged.depot_departure = route1.depot_departure

        # Add all stops from route1
        for stop in route1.stops:
            merged.add_stop(stop.store)

        # Add all stops from route2
        for stop in route2.stops:
            merged.add_stop(stop.store)

        # Update metrics
        self._update_route_metrics(merged)

        return merged

    def _two_opt_improve(self, route: Route):
        """
        Apply 2-opt local search to improve route
        Reverses segments to reduce distance
        """
        if len(route.stops) < 4:
            return

        improved = True
        max_iterations = 100
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(1, len(route.stops) - 2):
                for j in range(i + 1, len(route.stops)):
                    # Try reversing segment [i:j]
                    new_stops = route.stops[:i] + route.stops[i : j + 1][::-1] + route.stops[j + 1 :]

                    # Calculate new distance
                    new_route = Route(vehicle=route.vehicle, day=route.day)
                    new_route.depot_departure = route.depot_departure

                    for stop in new_stops:
                        new_route.add_stop(stop.store)

                    self._update_route_metrics(new_route)

                    # If better, accept
                    if new_route.total_distance_km < route.total_distance_km:
                        # Validate constraints
                        is_valid, _ = self.validator.validate_route(new_route, self.distance_matrix, self.time_matrix)

                        if is_valid:
                            route.stops = new_route.stops
                            route.total_distance_km = new_route.total_distance_km
                            route.total_duration_minutes = new_route.total_duration_minutes
                            improved = True
                            break

                if improved:
                    break
