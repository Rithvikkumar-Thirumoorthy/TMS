"""
Example: Single Day VRP Optimization
Demonstrates how to solve VRP for a single day using different algorithms
"""
import json
from datetime import datetime

from vrp_solver.models import Store, Vehicle
from vrp_solver.solvers import ClarkeWrightSolver, ORToolsSolver, ALNSSolver
from vrp_solver.utils import DistanceCalculator, DataLoader


def main():
    print("=" * 60)
    print("Single Day VRP Optimization Example")
    print("=" * 60)

    # Step 1: Load data
    print("\n1. Loading data...")
    stores = DataLoader.load_stores_from_json("examples/sample_data/stores.json")
    vehicles = DataLoader.load_vehicles_from_json("examples/sample_data/vehicles.json")

    with open("examples/sample_data/depot.json", "r") as f:
        depot_data = json.load(f)

    print(f"   Loaded {len(stores)} stores")
    print(f"   Loaded {len(vehicles)} vehicles")

    # Step 2: Build distance and time matrices
    print("\n2. Building distance and time matrices...")

    # Create location dictionary
    locations = {depot_data["id"]: (depot_data["latitude"], depot_data["longitude"])}

    for store in stores:
        locations[store.id] = (store.latitude, store.longitude)

    # Calculate matrices
    distance_matrix = DistanceCalculator.build_distance_matrix(locations, method="haversine")
    time_matrix = DistanceCalculator.build_time_matrix(distance_matrix, avg_speed_kmh=40.0)

    print("   Distance matrix built")
    print("   Time matrix built")

    # Step 3: Solve using different algorithms
    day = "Mon"
    start_time = datetime(2024, 1, 1, 8, 0, 0)

    print(f"\n3. Solving VRP for {day}...")
    print("=" * 60)

    # Algorithm 1: Clarke-Wright (Fast baseline)
    print("\nAlgorithm 1: Clarke-Wright Savings")
    print("-" * 60)

    cw_solver = ClarkeWrightSolver(stores, vehicles, distance_matrix, time_matrix, depot_id="depot")
    cw_solution = cw_solver.solve(day=day, start_time=start_time)

    print(f"✓ Solution found: {len(cw_solution.routes)} routes")
    print(f"  Total distance: {cw_solution.total_distance_km:.2f} km")
    print(f"  Total cost: ${cw_solution.total_cost:.2f}")
    print(f"  Average utilization: {cw_solution.get_average_utilization():.1f}%")
    print(f"  Feasible: {cw_solution.is_feasible}")

    if not cw_solution.is_feasible:
        print(f"  Violations: {cw_solution.constraint_violations}")

    # Print routes
    for i, route in enumerate(cw_solution.routes):
        print(f"\n  Route {i+1} ({route.vehicle.name}):")
        print(f"    Stops: {' → '.join([s.store.id for s in route.stops])}")
        print(f"    Distance: {route.total_distance_km:.2f} km")
        print(f"    Duration: {route.total_duration_minutes:.0f} min")
        print(f"    Load: {route.total_load_cbm:.1f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

    # Algorithm 2: OR-Tools (Production quality)
    print("\n\nAlgorithm 2: Google OR-Tools")
    print("-" * 60)

    ortools_solver = ORToolsSolver(stores, vehicles, distance_matrix, time_matrix, depot_id="depot")
    ortools_solution = ortools_solver.solve(day=day, start_time=start_time, time_limit_seconds=30)

    print(f"✓ Solution found: {len(ortools_solution.routes)} routes")
    print(f"  Total distance: {ortools_solution.total_distance_km:.2f} km")
    print(f"  Total cost: ${ortools_solution.total_cost:.2f}")
    print(f"  Average utilization: {ortools_solution.get_average_utilization():.1f}%")
    print(f"  Feasible: {ortools_solution.is_feasible}")

    # Print routes
    for i, route in enumerate(ortools_solution.routes):
        print(f"\n  Route {i+1} ({route.vehicle.name}):")
        print(f"    Stops: {' → '.join([s.store.id for s in route.stops])}")
        print(f"    Distance: {route.total_distance_km:.2f} km")
        print(f"    Duration: {route.total_duration_minutes:.0f} min")
        print(f"    Load: {route.total_load_cbm:.1f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

        # Show time windows
        for stop in route.stops:
            if stop.arrival_time:
                print(f"      {stop.store.id}: arrive {stop.arrival_time.strftime('%H:%M')}, depart {stop.departure_time.strftime('%H:%M')}")

    # Algorithm 3: ALNS (Advanced metaheuristic)
    print("\n\nAlgorithm 3: ALNS (Adaptive Large Neighborhood Search)")
    print("-" * 60)

    alns_solver = ALNSSolver(stores, vehicles, distance_matrix, time_matrix, depot_id="depot")
    alns_solution = alns_solver.solve(day=day, start_time=start_time, max_iterations=1000)

    print(f"✓ Solution found: {len(alns_solution.routes)} routes")
    print(f"  Total distance: {alns_solution.total_distance_km:.2f} km")
    print(f"  Total cost: ${alns_solution.total_cost:.2f}")
    print(f"  Average utilization: {alns_solution.get_average_utilization():.1f}%")
    print(f"  Feasible: {alns_solution.is_feasible}")

    # Print routes
    for i, route in enumerate(alns_solution.routes):
        print(f"\n  Route {i+1} ({route.vehicle.name}):")
        print(f"    Stops: {' → '.join([s.store.id for s in route.stops])}")
        print(f"    Distance: {route.total_distance_km:.2f} km")
        print(f"    Duration: {route.total_duration_minutes:.0f} min")
        print(f"    Load: {route.total_load_cbm:.1f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

    # Step 4: Save best solution
    print("\n" + "=" * 60)
    print("4. Saving solution...")

    # Choose OR-Tools solution (usually best)
    best_solution = ortools_solution

    DataLoader.save_solution_to_json(best_solution, "examples/output/solution.json")
    DataLoader.save_solution_to_csv(best_solution, "examples/output/solution.csv")

    print("   ✓ Solution saved to examples/output/solution.json")
    print("   ✓ Solution saved to examples/output/solution.csv")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    # Create output directory
    import os

    os.makedirs("examples/output", exist_ok=True)

    main()
