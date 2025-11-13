"""
Google OR-Tools VRP Solver
Production-ready solver with native constraint support
"""
from typing import List, Dict
from datetime import datetime, timedelta
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from .base_solver import BaseSolver
from ..models import Store, Vehicle, Route, Solution, RouteStop
from ..constraints import ConstraintValidator


class ORToolsSolver(BaseSolver):
    """
    Google OR-Tools based VRP solver
    Handles all constraints natively with excellent performance
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = ConstraintValidator()

    def solve(self, day: str, start_time: datetime = None, time_limit_seconds: int = 120, **kwargs) -> Solution:
        """
        Solve VRP using Google OR-Tools

        Args:
            day: Day of week to solve for
            start_time: Depot departure time
            time_limit_seconds: Maximum solving time
        """
        if start_time is None:
            start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Filter stores available on this day
        available_stores = [s for s in self.stores if s.is_day_allowed(day) and s.get_time_window_for_day(day) is not None]

        if not available_stores:
            return Solution(routes=[], day=day, unserved_stores=[s.id for s in self.stores])

        # Build OR-Tools model
        manager, routing, data = self._create_model(available_stores, day, start_time)

        if routing is None:
            # No feasible solution possible
            return Solution(routes=[], day=day, unserved_stores=[s.id for s in available_stores], is_feasible=False)

        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_parameters.time_limit.seconds = time_limit_seconds
        search_parameters.log_search = False

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            # Extract routes from solution
            routes = self._extract_routes(manager, routing, solution, data, available_stores, day, start_time)
            return self._create_solution(routes, day)
        else:
            # No solution found
            return Solution(
                routes=[],
                day=day,
                unserved_stores=[s.id for s in available_stores],
                is_feasible=False,
                constraint_violations=["OR-Tools could not find a feasible solution"],
            )

    def _create_model(self, stores: List[Store], day: str, start_time: datetime):
        """Create OR-Tools routing model"""
        # Prepare data
        data = {}
        data["num_vehicles"] = len(self.vehicles)
        data["depot"] = 0
        data["stores"] = stores
        data["day"] = day
        data["start_time"] = start_time

        # Build location list: [depot] + [stores]
        locations = [self.depot_id] + [s.id for s in stores]
        data["locations"] = locations
        data["num_locations"] = len(locations)

        # Build distance matrix (indices)
        distance_matrix = []
        for i, loc1 in enumerate(locations):
            row = []
            for j, loc2 in enumerate(locations):
                dist = self.distance_matrix.get(loc1, {}).get(loc2, 0)
                # Convert to integer (meters)
                row.append(int(dist * 1000))
            distance_matrix.append(row)
        data["distance_matrix"] = distance_matrix

        # Build time matrix (minutes)
        time_matrix = []
        for i, loc1 in enumerate(locations):
            row = []
            for j, loc2 in enumerate(locations):
                if self.time_matrix:
                    travel_time = self.time_matrix.get(loc1, {}).get(loc2, 0)
                else:
                    # Estimate from distance
                    dist_km = self.distance_matrix.get(loc1, {}).get(loc2, 0)
                    travel_time = (dist_km / 40.0) * 60  # 40 km/h average

                # Add service time for non-depot locations
                if j > 0:  # Not depot
                    service_time = stores[j - 1].service_time_minutes
                else:
                    service_time = 0

                total_time = int(travel_time + service_time)
                row.append(total_time)
            time_matrix.append(row)
        data["time_matrix"] = time_matrix

        # Demands (in CBM * 100 to keep precision as integer)
        demands = [0]  # Depot has 0 demand
        for store in stores:
            demands.append(int(store.demand_cbm * 100))
        data["demands"] = demands

        # Vehicle capacities
        vehicle_capacities = [int(v.capacity_cbm * 100) for v in self.vehicles]
        data["vehicle_capacities"] = vehicle_capacities

        # Time windows (in minutes from start_time)
        time_windows = [(0, 0)]  # Depot
        for store in stores:
            tw = store.get_time_window_for_day(day)
            if tw:
                # Convert to minutes from start
                earliest_minutes = tw.earliest.hour * 60 + tw.earliest.minute
                latest_minutes = tw.latest.hour * 60 + tw.latest.minute
                time_windows.append((earliest_minutes, latest_minutes))
            else:
                # Wide window if not specified
                time_windows.append((0, 12 * 60))  # 12 hours
        data["time_windows"] = time_windows

        # Create routing index manager
        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), data["num_vehicles"], data["depot"])

        # Create routing model
        routing = pywrapcp.RoutingModel(manager)

        # Distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Capacity constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["demands"][from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Time window constraint
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["time_matrix"][from_node][to_node]

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time (30 minutes slack)
            12 * 60,  # maximum time per vehicle (12 hours)
            False,  # Don't force start cumul to zero
            "Time",
        )

        time_dimension = routing.GetDimensionOrDie("Time")

        # Add time window constraints for each location
        for location_idx, time_window in enumerate(time_windows):
            if location_idx == 0:  # Skip depot
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # Add time window constraints for depot (end time)
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.End(vehicle_id)
            time_dimension.CumulVar(index).SetRange(0, 12 * 60)

        # Minimize time
        time_dimension.SetGlobalSpanCostCoefficient(100)

        # Allow dropping nodes (optional deliveries) with high penalty
        penalty = 100000
        for node in range(1, len(distance_matrix)):
            routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

        return manager, routing, data

    def _extract_routes(self, manager, routing, solution, data, stores: List[Store], day: str, start_time: datetime) -> List[Route]:
        """Extract routes from OR-Tools solution"""
        routes = []

        time_dimension = routing.GetDimensionOrDie("Time")
        capacity_dimension = routing.GetDimensionOrDie("Capacity")

        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            route_stops = []
            route_load = 0

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)

                if node_index > 0:  # Not depot
                    store = stores[node_index - 1]

                    # Get time and capacity
                    time_var = time_dimension.CumulVar(index)
                    arrival_minutes = solution.Value(time_var)

                    capacity_var = capacity_dimension.CumulVar(index)
                    cumul_load = solution.Value(capacity_var)

                    # Create stop
                    arrival_time = start_time + timedelta(minutes=arrival_minutes)
                    departure_time = arrival_time + timedelta(minutes=store.service_time_minutes)

                    stop = RouteStop(
                        store=store,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        load_before=route_load,
                        load_after=route_load + store.demand_cbm,
                        sequence=len(route_stops),
                    )

                    route_stops.append(stop)
                    route_load += store.demand_cbm

                index = solution.Value(routing.NextVar(index))

            # Create route if not empty
            if route_stops:
                vehicle = self.vehicles[vehicle_id]
                route = Route(vehicle=vehicle, stops=route_stops, day=day)
                route.depot_departure = start_time
                route.total_load_cbm = route_load

                # Calculate return time
                last_time_var = time_dimension.CumulVar(index)
                return_minutes = solution.Value(last_time_var)
                route.depot_return = start_time + timedelta(minutes=return_minutes)

                self._update_route_metrics(route)
                routes.append(route)

        return routes
