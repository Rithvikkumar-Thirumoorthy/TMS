"""
Constraint Validation System
"""
from datetime import datetime, time, timedelta
from typing import List, Tuple, Optional
from ..models import Store, Vehicle, Route, RouteStop


class ConstraintValidator:
    """Validates all hard and soft constraints"""

    def __init__(self, service_time_minutes: int = 60):
        self.service_time_minutes = service_time_minutes

    def validate_route(self, route: Route, distance_matrix: dict = None, time_matrix: dict = None) -> Tuple[bool, List[str]]:
        """
        Validate all constraints for a route
        Returns: (is_valid, list_of_violations)
        """
        violations = []

        # 1. Capacity constraint
        if not self._check_capacity(route):
            violations.append(
                f"Capacity exceeded: {route.total_load_cbm:.2f} > {route.vehicle.capacity_cbm}"
            )

        # 2. Time windows
        time_violations = self._check_time_windows(route, time_matrix)
        violations.extend(time_violations)

        # 3. Forbidden intervals
        forbidden_violations = self._check_forbidden_intervals(route)
        violations.extend(forbidden_violations)

        # 4. Fleet restrictions
        fleet_violations = self._check_fleet_restrictions(route)
        violations.extend(fleet_violations)

        # 5. Day exclusions
        if route.day:
            day_violations = self._check_day_exclusions(route)
            violations.extend(day_violations)

        # 6. Max route duration
        if not self._check_max_duration(route):
            violations.append(
                f"Route duration {route.total_duration_minutes:.0f} min exceeds maximum {route.vehicle.max_route_duration_hours * 60:.0f} min"
            )

        return len(violations) == 0, violations

    def _check_capacity(self, route: Route) -> bool:
        """Check vehicle capacity constraint"""
        return route.total_load_cbm <= route.vehicle.capacity_cbm

    def _check_time_windows(self, route: Route, time_matrix: dict = None) -> List[str]:
        """Check time window constraints"""
        violations = []

        if not route.stops or not route.depot_departure:
            return violations

        current_time = route.depot_departure
        depot_id = "depot"

        for i, stop in enumerate(route.stops):
            prev_location = depot_id if i == 0 else route.stops[i - 1].store.id

            # Get travel time
            if time_matrix and prev_location in time_matrix and stop.store.id in time_matrix[prev_location]:
                travel_minutes = time_matrix[prev_location][stop.store.id]
            else:
                # Estimate: 5 minutes between stores
                travel_minutes = 5

            # Arrival time
            arrival_time = current_time + timedelta(minutes=travel_minutes)
            stop.arrival_time = arrival_time

            # Check time window for this day
            time_window = stop.store.get_time_window_for_day(route.day)

            if time_window:
                arrival_time_only = arrival_time.time()

                if not time_window.contains(arrival_time_only):
                    violations.append(
                        f"Store {stop.store.id} time window violation: "
                        f"arrival {arrival_time_only.strftime('%H:%M')} "
                        f"not in window {time_window}"
                    )

                # If arriving before window, wait
                if arrival_time_only < time_window.earliest:
                    # Adjust to earliest time
                    arrival_time = arrival_time.replace(
                        hour=time_window.earliest.hour,
                        minute=time_window.earliest.minute,
                    )
                    stop.arrival_time = arrival_time

            # Departure = arrival + service time
            departure_time = arrival_time + timedelta(minutes=self.service_time_minutes)
            stop.departure_time = departure_time

            current_time = departure_time

        # Update route total duration
        if route.stops:
            route.depot_return = current_time
            total_duration = (route.depot_return - route.depot_departure).total_seconds() / 60
            route.total_duration_minutes = total_duration

        return violations

    def _check_forbidden_intervals(self, route: Route) -> List[str]:
        """Check forbidden interval constraints"""
        violations = []

        for stop in route.stops:
            if stop.arrival_time:
                arrival_time_only = stop.arrival_time.time()

                for forbidden in stop.store.forbidden_intervals:
                    if forbidden.conflicts_with(arrival_time_only):
                        violations.append(
                            f"Store {stop.store.id} forbidden interval violation: "
                            f"arrival {arrival_time_only.strftime('%H:%M')} "
                            f"conflicts with {forbidden}"
                        )

        return violations

    def _check_fleet_restrictions(self, route: Route) -> List[str]:
        """Check vehicle-store compatibility"""
        violations = []

        for stop in route.stops:
            if not route.vehicle.can_serve_store(stop.store.id):
                violations.append(
                    f"Vehicle {route.vehicle.id} cannot serve store {stop.store.id} "
                    f"due to fleet restrictions"
                )

        return violations

    def _check_day_exclusions(self, route: Route) -> List[str]:
        """Check day exclusion constraints"""
        violations = []

        if not route.day:
            return violations

        for stop in route.stops:
            if not stop.store.is_day_allowed(route.day):
                violations.append(
                    f"Store {stop.store.id} cannot be served on {route.day} "
                    f"(excluded days: {stop.store.excluded_days})"
                )

        return violations

    def _check_max_duration(self, route: Route) -> bool:
        """Check maximum route duration"""
        max_minutes = route.vehicle.max_route_duration_hours * 60
        return route.total_duration_minutes <= max_minutes

    def calculate_capacity_utilization_penalty(self, route: Route, target: float = 85.0) -> float:
        """
        Calculate penalty for deviating from target capacity utilization
        Returns penalty value (0 = at target)
        """
        utilization = route.get_load_utilization()
        deviation = abs(utilization - target)
        return deviation

    def calculate_load_balance_penalty(self, routes: List[Route]) -> float:
        """
        Calculate penalty for unbalanced load across routes
        Returns standard deviation of utilizations
        """
        if not routes:
            return 0.0

        import numpy as np

        utilizations = [r.get_load_utilization() for r in routes]
        return float(np.std(utilizations))
