"""
Adaptive Large Neighborhood Search (ALNS) for VRP
Advanced metaheuristic for high-quality solutions
"""
import random
import math
import copy
from typing import List, Dict, Tuple, Callable
from datetime import datetime

from .base_solver import BaseSolver
from .clarke_wright import ClarkeWrightSolver
from ..models import Store, Vehicle, Route, Solution, RouteStop
from ..constraints import ConstraintValidator, RouteConstraintChecker


class ALNSSolver(BaseSolver):
    """
    Adaptive Large Neighborhood Search
    State-of-the-art metaheuristic for VRP
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = ConstraintValidator()
        self.checker = RouteConstraintChecker()

        # ALNS parameters
        self.destruction_rate = 0.3  # Remove 30% of customers
        self.temperature_start = 100.0
        self.temperature_end = 1.0
        self.cooling_rate = 0.99

        # Operator weights
        self.destroy_weights = {
            "random": 1.0,
            "worst": 1.0,
            "shaw": 1.0,
            "time_based": 1.0,
        }
        self.repair_weights = {
            "greedy": 1.0,
            "regret2": 1.0,
            "regret3": 1.0,
        }

        # Score parameters
        self.score_new_best = 10
        self.score_better = 5
        self.score_accepted = 1
        self.score_rejected = 0

    def solve(self, day: str, start_time: datetime = None, max_iterations: int = 5000, **kwargs) -> Solution:
        """
        Solve VRP using ALNS

        Args:
            day: Day of week
            start_time: Depot departure time
            max_iterations: Maximum iterations
        """
        if start_time is None:
            start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Filter available stores
        available_stores = [s for s in self.stores if s.is_day_allowed(day) and s.get_time_window_for_day(day) is not None]

        if not available_stores:
            return Solution(routes=[], day=day, unserved_stores=[s.id for s in self.stores])

        # Step 1: Generate initial solution using Clarke-Wright
        cw_solver = ClarkeWrightSolver(available_stores, self.vehicles, self.distance_matrix, self.time_matrix, self.depot_id)
        current_solution = cw_solver.solve(day, start_time)

        if not current_solution.routes:
            return current_solution

        best_solution = copy.deepcopy(current_solution)
        temperature = self.temperature_start

        # Tracking
        iteration_without_improvement = 0
        max_no_improvement = 500

        # ALNS main loop
        for iteration in range(max_iterations):
            # Select destroy and repair operators
            destroy_op = self._select_operator(self.destroy_weights)
            repair_op = self._select_operator(self.repair_weights)

            # Apply destroy and repair
            destroyed = self._apply_destroy(current_solution, destroy_op, day)
            new_solution = self._apply_repair(destroyed, repair_op, day, start_time)

            # Calculate costs
            current_cost = self._calculate_cost(current_solution)
            new_cost = self._calculate_cost(new_solution)
            best_cost = self._calculate_cost(best_solution)

            # Acceptance decision
            accept = False
            score = 0

            if new_cost < best_cost:
                # New best solution
                best_solution = copy.deepcopy(new_solution)
                current_solution = new_solution
                accept = True
                score = self.score_new_best
                iteration_without_improvement = 0

            elif new_cost < current_cost:
                # Better than current
                current_solution = new_solution
                accept = True
                score = self.score_better
                iteration_without_improvement += 1

            else:
                # Worse solution - accept with probability
                delta = new_cost - current_cost
                probability = math.exp(-delta / temperature)

                if random.random() < probability:
                    current_solution = new_solution
                    accept = True
                    score = self.score_accepted
                else:
                    score = self.score_rejected

                iteration_without_improvement += 1

            # Update operator weights
            if accept:
                self.destroy_weights[destroy_op] += score
                self.repair_weights[repair_op] += score

            # Cool down temperature
            temperature = max(self.temperature_end, temperature * self.cooling_rate)

            # Early termination if no improvement
            if iteration_without_improvement > max_no_improvement:
                break

        return best_solution

    def _select_operator(self, weights: Dict[str, float]) -> str:
        """Select operator based on weights (roulette wheel)"""
        total = sum(weights.values())
        r = random.uniform(0, total)

        cumulative = 0
        for op, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return op

        return list(weights.keys())[0]

    def _apply_destroy(self, solution: Solution, operator: str, day: str) -> Tuple[List[Route], List[Store]]:
        """Apply destruction operator"""
        routes = copy.deepcopy(solution.routes)
        removed_stores = []

        num_to_remove = max(1, int(sum(len(r.stops) for r in routes) * self.destruction_rate))

        if operator == "random":
            removed_stores = self._random_removal(routes, num_to_remove)

        elif operator == "worst":
            removed_stores = self._worst_removal(routes, num_to_remove)

        elif operator == "shaw":
            removed_stores = self._shaw_removal(routes, num_to_remove)

        elif operator == "time_based":
            removed_stores = self._time_based_removal(routes, num_to_remove, day)

        return routes, removed_stores

    def _random_removal(self, routes: List[Route], num_to_remove: int) -> List[Store]:
        """Randomly remove stores"""
        removed = []
        all_stops = [(route, stop) for route in routes for stop in route.stops]

        if not all_stops:
            return removed

        random.shuffle(all_stops)

        for i in range(min(num_to_remove, len(all_stops))):
            route, stop = all_stops[i]
            route.remove_stop(stop.store.id)
            removed.append(stop.store)

        return removed

    def _worst_removal(self, routes: List[Route], num_to_remove: int) -> List[Store]:
        """Remove stores with highest cost impact"""
        removed = []

        for _ in range(num_to_remove):
            worst_saving = -float("inf")
            worst_route = None
            worst_store = None

            for route in routes:
                if not route.stops:
                    continue

                for stop in route.stops:
                    # Calculate saving if this store is removed
                    saving = self._calculate_removal_saving(route, stop.store.id)

                    if saving > worst_saving:
                        worst_saving = saving
                        worst_route = route
                        worst_store = stop.store

            if worst_route and worst_store:
                worst_route.remove_stop(worst_store.id)
                removed.append(worst_store)
            else:
                break

        return removed

    def _shaw_removal(self, routes: List[Route], num_to_remove: int) -> List[Store]:
        """Remove similar stores (based on location and demand)"""
        removed = []
        all_stops = [(route, stop) for route in routes for stop in route.stops]

        if not all_stops:
            return removed

        # Pick random seed store
        seed_route, seed_stop = random.choice(all_stops)
        seed_store = seed_stop.store

        # Calculate similarity scores
        similarities = []
        for route, stop in all_stops:
            store = stop.store

            # Distance similarity
            dist = self.distance_matrix.get(seed_store.id, {}).get(store.id, 0)

            # Demand similarity
            demand_diff = abs(seed_store.demand_cbm - store.demand_cbm)

            # Combined similarity (lower is more similar)
            similarity = dist + demand_diff * 10

            similarities.append((route, stop, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[2])

        # Remove most similar stores
        for i in range(min(num_to_remove, len(similarities))):
            route, stop, _ = similarities[i]
            if stop.store.id in route.get_store_ids():
                route.remove_stop(stop.store.id)
                removed.append(stop.store)

        return removed

    def _time_based_removal(self, routes: List[Route], num_to_remove: int, day: str) -> List[Store]:
        """Remove stores with similar time windows"""
        removed = []
        all_stops = [(route, stop) for route in routes for stop in route.stops]

        if not all_stops:
            return removed

        # Group by time window
        random.shuffle(all_stops)

        for i in range(min(num_to_remove, len(all_stops))):
            route, stop = all_stops[i]
            route.remove_stop(stop.store.id)
            removed.append(stop.store)

        return removed

    def _apply_repair(self, destroyed: Tuple[List[Route], List[Store]], operator: str, day: str, start_time: datetime) -> Solution:
        """Apply repair operator"""
        routes, removed_stores = destroyed

        # Remove empty routes
        routes = [r for r in routes if r.stops]

        if operator == "greedy":
            routes = self._greedy_insertion(routes, removed_stores, day)

        elif operator == "regret2":
            routes = self._regret_insertion(routes, removed_stores, day, k=2)

        elif operator == "regret3":
            routes = self._regret_insertion(routes, removed_stores, day, k=3)

        # Update metrics
        for route in routes:
            route.depot_departure = start_time
            self._update_route_metrics(route)

        solution = Solution(routes=routes, day=day)
        solution.compute_metrics()

        return solution

    def _greedy_insertion(self, routes: List[Route], stores: List[Store], day: str) -> List[Route]:
        """Greedy insertion: insert each store at best position"""
        for store in stores:
            best_cost = float("inf")
            best_route = None
            best_position = None

            # Try existing routes
            for route in routes:
                can_add, _ = self.checker.can_add_store_to_route(route, store, day)

                if can_add:
                    # Try all positions
                    for pos in range(len(route.stops) + 1):
                        cost = self.checker.calculate_insertion_cost(route, store, pos, self.distance_matrix)

                        if cost < best_cost:
                            best_cost = cost
                            best_route = route
                            best_position = pos

            # Try new route
            compatible_vehicle = self._find_compatible_vehicle(store, day)
            if compatible_vehicle:
                cost = self.checker.calculate_insertion_cost(Route(vehicle=compatible_vehicle), store, 0, self.distance_matrix)

                if cost < best_cost or best_route is None:
                    # Create new route
                    new_route = Route(vehicle=compatible_vehicle, day=day)
                    new_route.add_stop(store)
                    routes.append(new_route)
                    continue

            # Insert at best position
            if best_route and best_position is not None:
                best_route.add_stop(store, best_position)

        return routes

    def _regret_insertion(self, routes: List[Route], stores: List[Store], day: str, k: int = 2) -> List[Route]:
        """Regret-k insertion: prioritize stores with high regret"""
        uninserted = stores.copy()

        while uninserted:
            max_regret = -float("inf")
            best_store = None
            best_route = None
            best_position = None

            # Calculate regret for each store
            for store in uninserted:
                costs = []

                # Find k best insertion positions
                for route in routes:
                    can_add, _ = self.checker.can_add_store_to_route(route, store, day)

                    if can_add:
                        for pos in range(len(route.stops) + 1):
                            cost = self.checker.calculate_insertion_cost(route, store, pos, self.distance_matrix)
                            costs.append((cost, route, pos))

                if len(costs) >= k:
                    # Sort by cost
                    costs.sort(key=lambda x: x[0])

                    # Regret = difference between best and k-th best
                    regret = costs[k - 1][0] - costs[0][0]

                    if regret > max_regret:
                        max_regret = regret
                        best_store = store
                        best_route = costs[0][1]
                        best_position = costs[0][2]

            # Insert store with max regret
            if best_store and best_route:
                best_route.add_stop(best_store, best_position)
                uninserted.remove(best_store)
            else:
                # Try creating new route for remaining stores
                if uninserted:
                    store = uninserted[0]
                    vehicle = self._find_compatible_vehicle(store, day)
                    if vehicle:
                        new_route = Route(vehicle=vehicle, day=day)
                        new_route.add_stop(store)
                        routes.append(new_route)
                        uninserted.remove(store)
                    else:
                        uninserted.remove(store)

        return routes

    def _find_compatible_vehicle(self, store: Store, day: str) -> Vehicle:
        """Find compatible vehicle for store"""
        for vehicle in self.vehicles:
            if vehicle.can_serve_store(store.id) and vehicle.can_fit_demand(store.demand_cbm):
                return vehicle
        return None

    def _calculate_removal_saving(self, route: Route, store_id: str) -> float:
        """Calculate cost saving if store is removed"""
        # Simplified: use distance saving
        stops = route.get_store_ids()
        if store_id not in stops:
            return 0

        idx = stops.index(store_id)
        depot = self.depot_id

        if len(stops) == 1:
            # Only store in route
            return self.distance_matrix.get(depot, {}).get(store_id, 0) * 2

        elif idx == 0:
            # First store
            old_dist = self.distance_matrix.get(depot, {}).get(store_id, 0) + self.distance_matrix.get(store_id, {}).get(stops[1], 0)
            new_dist = self.distance_matrix.get(depot, {}).get(stops[1], 0)
            return old_dist - new_dist

        elif idx == len(stops) - 1:
            # Last store
            old_dist = self.distance_matrix.get(stops[-2], {}).get(store_id, 0) + self.distance_matrix.get(store_id, {}).get(depot, 0)
            new_dist = self.distance_matrix.get(stops[-2], {}).get(depot, 0)
            return old_dist - new_dist

        else:
            # Middle store
            prev = stops[idx - 1]
            next_store = stops[idx + 1]
            old_dist = self.distance_matrix.get(prev, {}).get(store_id, 0) + self.distance_matrix.get(store_id, {}).get(next_store, 0)
            new_dist = self.distance_matrix.get(prev, {}).get(next_store, 0)
            return old_dist - new_dist

    def _calculate_cost(self, solution: Solution) -> float:
        """Calculate total solution cost"""
        # Multi-objective: distance + vehicle count + utilization penalty
        alpha = 1.0  # Distance weight
        beta = 1000.0  # Vehicle count weight
        gamma = 500.0  # Utilization penalty weight

        distance_cost = solution.total_distance_km * alpha
        vehicle_cost = solution.num_vehicles_used * beta

        # Utilization penalty (target 85%)
        util_penalty = 0
        for route in solution.routes:
            util = route.get_load_utilization()
            deviation = abs(util - 85.0)
            util_penalty += deviation

        total_cost = distance_cost + vehicle_cost + (util_penalty * gamma)

        return total_cost
