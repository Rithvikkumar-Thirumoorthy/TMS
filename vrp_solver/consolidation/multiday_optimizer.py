"""
Multi-Day Consolidation Optimizer
Intelligently consolidates deliveries across multiple days
"""
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import copy

from ..models import Store, Vehicle, Solution, MultiDaySolution
from ..solvers import BaseSolver


class MultiDayOptimizer:
    """
    Multi-Day Smart Consolidation
    Optimizes delivery scheduling across Mon-Fri
    """

    WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    def __init__(
        self,
        stores: List[Store],
        vehicles: List[Vehicle],
        distance_matrix: Dict,
        time_matrix: Dict,
        solver: BaseSolver,
        consolidation_threshold: float = 70.0,  # Percentage of vehicle capacity
    ):
        self.stores = stores
        self.vehicles = vehicles
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix
        self.solver = solver
        self.consolidation_threshold = consolidation_threshold

    def optimize_week(self, start_date: datetime = None) -> MultiDaySolution:
        """
        Optimize deliveries across the entire week

        Strategy:
        1. Analyze weekly demand per store
        2. Consolidate stores with multiple orders
        3. Assign to best day based on capacity and time windows
        4. Solve VRP for each day independently
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Step 1: Aggregate weekly demand per store
        weekly_demand = self._aggregate_weekly_demand()

        # Step 2: Assign stores to days using consolidation strategy
        day_assignments = self._assign_stores_to_days(weekly_demand)

        # Step 3: Solve VRP for each day
        multi_day_solution = MultiDaySolution()

        for day_idx, day in enumerate(self.WEEKDAYS):
            if day not in day_assignments or not day_assignments[day]:
                continue

            # Get stores for this day
            day_stores = day_assignments[day]

            # Solve for this day
            day_start = start_date + timedelta(days=day_idx)

            solution = self.solver.solve(day=day, start_time=day_start)

            multi_day_solution.add_day_solution(day, solution)

        # Step 4: Calculate consolidation statistics
        multi_day_solution.consolidation_stats = self._calculate_consolidation_stats(day_assignments, weekly_demand)

        return multi_day_solution

    def _aggregate_weekly_demand(self) -> Dict[str, Dict]:
        """
        Aggregate demand for each store across the week
        Returns: {store_id: {demand, available_days, time_windows, etc.}}
        """
        weekly_demand = {}

        for store in self.stores:
            # Calculate total weekly demand (assume each store wants one delivery per week for now)
            total_demand = store.demand_cbm

            # Get available days (exclude excluded days)
            available_days = [day for day in self.WEEKDAYS if store.is_day_allowed(day)]

            # Get time windows per day
            time_windows_by_day = {}
            for day in available_days:
                tw = store.get_time_window_for_day(day)
                if tw:
                    time_windows_by_day[day] = tw

            weekly_demand[store.id] = {
                "store": store,
                "total_demand": total_demand,
                "available_days": available_days,
                "time_windows": time_windows_by_day,
                "preferred_days": store.preferred_days,
            }

        return weekly_demand

    def _assign_stores_to_days(self, weekly_demand: Dict) -> Dict[str, List[Store]]:
        """
        Assign stores to optimal days using smart consolidation

        Strategy:
        - If demand >= threshold: assign to single best day
        - If demand < threshold: try to consolidate with others on same day
        - Consider: time windows, capacity, existing load
        """
        day_assignments = {day: [] for day in self.WEEKDAYS}
        day_loads = {day: 0.0 for day in self.WEEKDAYS}

        # Sort stores by demand (descending) - handle large orders first
        sorted_stores = sorted(weekly_demand.items(), key=lambda x: x[1]["total_demand"], reverse=True)

        for store_id, info in sorted_stores:
            store = info["store"]
            demand = info["total_demand"]
            available_days = info["available_days"]

            if not available_days:
                continue

            # Get max vehicle capacity for reference
            max_capacity = max(v.capacity_cbm for v in self.vehicles)

            # Threshold-based decision
            demand_percentage = (demand / max_capacity) * 100

            if demand_percentage >= self.consolidation_threshold:
                # Large order: assign to best single day
                best_day = self._find_best_single_day(store, info, day_loads)
                if best_day:
                    day_assignments[best_day].append(store)
                    day_loads[best_day] += demand

            else:
                # Small order: consolidate with others
                best_day = self._find_best_consolidation_day(store, info, day_loads, day_assignments)
                if best_day:
                    day_assignments[best_day].append(store)
                    day_loads[best_day] += demand

        return day_assignments

    def _find_best_single_day(self, store: Store, info: Dict, day_loads: Dict[str, float]) -> str:
        """Find best day for a large single delivery"""
        available_days = info["available_days"]
        preferred_days = info["preferred_days"]

        # Scoring system
        scores = {}

        for day in available_days:
            score = 0

            # Prefer days with less existing load (balance)
            load_score = 1000 - day_loads[day]
            score += load_score

            # Prefer preferred days
            if day in preferred_days:
                score += 500

            # Prefer days with longer time windows
            tw = info["time_windows"].get(day)
            if tw:
                window_duration = tw.duration_minutes()
                score += window_duration

            scores[day] = score

        # Return day with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return available_days[0] if available_days else None

    def _find_best_consolidation_day(self, store: Store, info: Dict, day_loads: Dict[str, float], day_assignments: Dict[str, List[Store]]) -> str:
        """Find best day to consolidate this store with others"""
        available_days = info["available_days"]
        preferred_days = info["preferred_days"]
        demand = info["total_demand"]

        max_capacity = max(v.capacity_cbm for v in self.vehicles)

        # Scoring system
        scores = {}

        for day in available_days:
            score = 0

            # Check if adding this store keeps us under reasonable capacity
            projected_load = day_loads[day] + demand
            if projected_load > max_capacity * len(self.vehicles):
                # Would need too many vehicles
                score -= 10000
                continue

            # Prefer days with some existing load (consolidation opportunity)
            if day_loads[day] > 0:
                score += 200

            # But not too much load
            utilization = day_loads[day] / (max_capacity * len(self.vehicles))
            if utilization < 0.7:  # Under 70% of total fleet capacity
                score += 300

            # Prefer preferred days
            if day in preferred_days:
                score += 500

            # Prefer days with compatible time windows (check proximity to other stores)
            same_day_stores = day_assignments.get(day, [])
            if same_day_stores:
                # Check if nearby any existing stores (clustering)
                min_dist = float("inf")
                for other_store in same_day_stores:
                    dist = self.distance_matrix.get(store.id, {}).get(other_store.id, float("inf"))
                    min_dist = min(min_dist, dist)

                if min_dist < 10:  # Within 10 km
                    score += 400  # Good clustering

            scores[day] = score

        # Return day with highest score
        if scores:
            best_day = max(scores.items(), key=lambda x: x[1])[0]
            return best_day

        return available_days[0] if available_days else None

    def _calculate_consolidation_stats(self, day_assignments: Dict[str, List[Store]], weekly_demand: Dict) -> Dict:
        """Calculate consolidation statistics"""
        total_stores = len(weekly_demand)
        assigned_stores = sum(len(stores) for stores in day_assignments.values())

        # Count stores that could have been split but were consolidated
        consolidated_count = 0
        for store_id, info in weekly_demand.items():
            if len(info["available_days"]) > 1:
                # Could have been on multiple days but consolidated to one
                consolidated_count += 1

        consolidation_rate = (consolidated_count / total_stores * 100) if total_stores > 0 else 0

        # Calculate baseline vs optimized trips
        baseline_trips = total_stores  # One trip per store per week
        optimized_trips = sum(len(stores) for stores in day_assignments.values())
        trip_reduction = ((baseline_trips - optimized_trips) / baseline_trips * 100) if baseline_trips > 0 else 0

        return {
            "total_stores": total_stores,
            "stores_assigned": assigned_stores,
            "consolidation_rate_percent": round(consolidation_rate, 2),
            "baseline_trips": baseline_trips,
            "optimized_trips": optimized_trips,
            "trip_reduction_percent": round(trip_reduction, 2),
            "stores_per_day": {day: len(stores) for day, stores in day_assignments.items()},
        }
