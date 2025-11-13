"""
Example: Multi-Day Consolidation Optimization
Demonstrates weekly optimization with smart consolidation
"""
import json
from datetime import datetime

from vrp_solver.models import Store, Vehicle
from vrp_solver.solvers import ORToolsSolver
from vrp_solver.consolidation import MultiDayOptimizer
from vrp_solver.utils import DistanceCalculator, DataLoader


def main():
    print("=" * 60)
    print("Multi-Day Consolidation Optimization Example")
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

    locations = {depot_data["id"]: (depot_data["latitude"], depot_data["longitude"])}

    for store in stores:
        locations[store.id] = (store.latitude, store.longitude)

    distance_matrix = DistanceCalculator.build_distance_matrix(locations, method="haversine")
    time_matrix = DistanceCalculator.build_time_matrix(distance_matrix, avg_speed_kmh=40.0)

    print("   ✓ Matrices built")

    # Step 3: Create solver and optimizer
    print("\n3. Setting up multi-day optimizer...")

    # Use OR-Tools as the daily solver
    ortools_solver = ORToolsSolver(stores, vehicles, distance_matrix, time_matrix, depot_id="depot")

    # Create multi-day optimizer
    multiday_optimizer = MultiDayOptimizer(
        stores=stores,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
        time_matrix=time_matrix,
        solver=ortools_solver,
        consolidation_threshold=70.0,  # 70% of vehicle capacity
    )

    # Step 4: Optimize entire week
    print("\n4. Optimizing weekly schedule...")
    print("=" * 60)

    start_date = datetime(2024, 1, 1, 8, 0, 0)  # Monday
    weekly_solution = multiday_optimizer.optimize_week(start_date=start_date)

    # Step 5: Display results
    print("\n📊 WEEKLY OPTIMIZATION RESULTS")
    print("=" * 60)

    # Consolidation stats
    stats = weekly_solution.consolidation_stats
    print("\n🎯 Consolidation Statistics:")
    print(f"   Total stores: {stats['total_stores']}")
    print(f"   Stores assigned: {stats['stores_assigned']}")
    print(f"   Consolidation rate: {stats['consolidation_rate_percent']:.1f}%")
    print(f"   Baseline trips: {stats['baseline_trips']}")
    print(f"   Optimized trips: {stats['optimized_trips']}")
    print(f"   Trip reduction: {stats['trip_reduction_percent']:.1f}%")

    print("\n📅 Stores per Day:")
    for day, count in stats["stores_per_day"].items():
        print(f"   {day}: {count} stores")

    # Daily breakdown
    print("\n" + "=" * 60)
    print("📦 DAILY BREAKDOWN")
    print("=" * 60)

    total_distance = 0
    total_cost = 0
    total_vehicles = 0

    for day, solution in weekly_solution.daily_solutions.items():
        print(f"\n{day}:")
        print(f"  Vehicles used: {solution.num_vehicles_used}")
        print(f"  Stores served: {solution.get_total_stores_served()}")
        print(f"  Total distance: {solution.total_distance_km:.2f} km")
        print(f"  Total cost: ${solution.total_cost:.2f}")
        print(f"  Average utilization: {solution.get_average_utilization():.1f}%")

        # Route details
        for i, route in enumerate(solution.routes):
            print(f"\n    Route {i+1} ({route.vehicle.name}):")
            print(f"      Stops: {' → '.join([s.store.id for s in route.stops])}")
            print(f"      Distance: {route.total_distance_km:.2f} km")
            print(f"      Load: {route.total_load_cbm:.1f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

            # Time schedule
            for stop in route.stops:
                if stop.arrival_time:
                    print(f"        {stop.store.name}: {stop.arrival_time.strftime('%H:%M')} - {stop.departure_time.strftime('%H:%M')}")

        total_distance += solution.total_distance_km
        total_cost += solution.total_cost
        total_vehicles += solution.num_vehicles_used

    # Weekly summary
    print("\n" + "=" * 60)
    print("📈 WEEKLY SUMMARY")
    print("=" * 60)
    print(f"  Total vehicles used (across week): {total_vehicles}")
    print(f"  Total distance traveled: {total_distance:.2f} km")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Average distance per day: {total_distance / 5:.2f} km")
    print(f"  Average vehicles per day: {total_vehicles / 5:.1f}")

    # Step 6: Save results
    print("\n" + "=" * 60)
    print("5. Saving results...")

    # Save weekly summary
    with open("examples/output/weekly_solution.json", "w") as f:
        json.dump(weekly_solution.to_dict(), f, indent=2)

    # Save each day
    for day, solution in weekly_solution.daily_solutions.items():
        DataLoader.save_solution_to_json(solution, f"examples/output/solution_{day}.json")
        DataLoader.save_solution_to_csv(solution, f"examples/output/solution_{day}.csv")

    print("   ✓ Weekly solution saved to examples/output/weekly_solution.json")
    print("   ✓ Daily solutions saved to examples/output/solution_*.json")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    import os

    os.makedirs("examples/output", exist_ok=True)

    main()
