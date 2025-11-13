"""
Route Constraint Checking Utilities
"""
from datetime import datetime, time, timedelta
from typing import Optional, Tuple
from ..models import Store, Vehicle, Route


class RouteConstraintChecker:
    """Quick constraint checks for route construction"""

    @staticmethod
    def can_add_store_to_route(route: Route, store: Store, day: str) -> Tuple[bool, str]:
        """
        Check if a store can be added to a route
        Returns: (can_add, reason_if_not)
        """
        # 1. Capacity check
        if route.total_load_cbm + store.demand_cbm > route.vehicle.capacity_cbm:
            return False, "Exceeds vehicle capacity"

        # 2. Fleet restriction check
        if not route.vehicle.can_serve_store(store.id):
            return False, "Vehicle cannot serve this store (fleet restriction)"

        # 3. Day exclusion check
        if not store.is_day_allowed(day):
            return False, f"Store not available on {day}"

        # 4. Time window compatibility (basic check)
        time_window = store.get_time_window_for_day(day)
        if time_window is None:
            return False, f"No time window available for {day}"

        return True, "OK"

    @staticmethod
    def is_time_feasible(arrival_time: time, store: Store, day: str) -> bool:
        """Check if arrival time is feasible for store"""
        # Check time window
        time_window = store.get_time_window_for_day(day)
        if time_window and not time_window.contains(arrival_time):
            # Check if we can wait until window opens
            if arrival_time < time_window.earliest:
                # Can wait
                return True
            else:
                # Too late
                return False

        # Check forbidden intervals
        if store.has_forbidden_conflict(arrival_time):
            return False

        return True

    @staticmethod
    def calculate_insertion_cost(
        route: Route,
        store: Store,
        position: int,
        distance_matrix: dict,
        time_matrix: dict = None,
    ) -> float:
        """
        Calculate cost of inserting store at specific position
        Returns: cost increase (distance based)
        """
        depot_id = "depot"

        if len(route.stops) == 0:
            # First store in route
            # Cost = depot -> store -> depot
            dist_to = distance_matrix.get(depot_id, {}).get(store.id, 0)
            dist_from = distance_matrix.get(store.id, {}).get(depot_id, 0)
            return dist_to + dist_from

        if position == 0:
            # Insert at beginning
            # Remove: depot -> first_store
            # Add: depot -> new_store -> first_store
            first_store = route.stops[0].store.id
            old_dist = distance_matrix.get(depot_id, {}).get(first_store, 0)
            new_dist = (
                distance_matrix.get(depot_id, {}).get(store.id, 0)
                + distance_matrix.get(store.id, {}).get(first_store, 0)
            )
            return new_dist - old_dist

        elif position >= len(route.stops):
            # Insert at end
            # Remove: last_store -> depot
            # Add: last_store -> new_store -> depot
            last_store = route.stops[-1].store.id
            old_dist = distance_matrix.get(last_store, {}).get(depot_id, 0)
            new_dist = (
                distance_matrix.get(last_store, {}).get(store.id, 0)
                + distance_matrix.get(store.id, {}).get(depot_id, 0)
            )
            return new_dist - old_dist

        else:
            # Insert in middle
            # Remove: prev_store -> next_store
            # Add: prev_store -> new_store -> next_store
            prev_store = route.stops[position - 1].store.id
            next_store = route.stops[position].store.id

            old_dist = distance_matrix.get(prev_store, {}).get(next_store, 0)
            new_dist = (
                distance_matrix.get(prev_store, {}).get(store.id, 0)
                + distance_matrix.get(store.id, {}).get(next_store, 0)
            )
            return new_dist - old_dist
