"""
Run VRP Optimization with Your Custom Data
This script loads your input data and runs the optimization
"""
import os
from datetime import datetime
from load_custom_data import CustomDataLoader
from vrp_solver.solvers import ORToolsSolver, ALNSSolver, ClarkeWrightSolver
from vrp_solver.consolidation import MultiDayOptimizer
from vrp_solver.utils import DataLoader


def run_single_day_optimization(day="Mon", algorithm="ortools", time_limit=120):
    """Run single-day VRP optimization with your data"""
    # Load data
    loader = CustomDataLoader(input_dir="input")
    stores, vehicles, depot_info, distance_matrix, time_matrix = loader.load_all_data()

    if stores is None:
        print("❌ Failed to load data. Exiting.")
        return None

    # Create solver
    print(f"\n🚀 Running {algorithm.upper()} optimization for {day}...")
    print("=" * 60)

    start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    if algorithm.lower() == "ortools":
        solver = ORToolsSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])
        solution = solver.solve(day=day, start_time=start_time, time_limit_seconds=time_limit)

    elif algorithm.lower() == "alns":
        solver = ALNSSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])
        solution = solver.solve(day=day, start_time=start_time, max_iterations=5000)

    elif algorithm.lower() == "clarke-wright" or algorithm.lower() == "cw":
        solver = ClarkeWrightSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])
        solution = solver.solve(day=day, start_time=start_time)

    else:
        print(f"❌ Unknown algorithm: {algorithm}")
        print("   Available: ortools, alns, clarke-wright")
        return None

    # Display results
    print("\n📊 RESULTS")
    print("=" * 60)
    print(f"✓ Feasible: {solution.is_feasible}")
    print(f"✓ Vehicles used: {solution.num_vehicles_used}")
    print(f"✓ Stores served: {solution.get_total_stores_served()}")
    print(f"✓ Total distance: {solution.total_distance_km:.2f} km")
    print(f"✓ Total duration: {solution.total_duration_hours:.2f} hours")
    print(f"✓ Total cost: ${solution.total_cost:.2f}")
    print(f"✓ Average utilization: {solution.get_average_utilization():.1f}%")

    if not solution.is_feasible:
        print(f"\n⚠️  Constraint violations:")
        for violation in solution.constraint_violations:
            print(f"   - {violation}")

    # Print routes
    print("\n📦 ROUTES")
    print("=" * 60)
    for i, route in enumerate(solution.routes):
        print(f"\nRoute {i+1} - {route.vehicle.name}:")
        print(f"  Stops: {' → '.join([stop.store.id for stop in route.stops])}")
        print(f"  Distance: {route.total_distance_km:.2f} km")
        print(f"  Duration: {route.total_duration_minutes:.0f} min")
        print(f"  Load: {route.total_load_cbm:.1f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

        # Show detailed schedule
        for stop in route.stops:
            if stop.arrival_time:
                print(f"    • {stop.store.name}: {stop.arrival_time.strftime('%H:%M')} - {stop.departure_time.strftime('%H:%M')}")

    # Save results
    os.makedirs("output", exist_ok=True)
    output_json = f"output/solution_{day}_{algorithm}.json"
    output_csv = f"output/solution_{day}_{algorithm}.csv"

    DataLoader.save_solution_to_json(solution, output_json)
    DataLoader.save_solution_to_csv(solution, output_csv)

    print(f"\n💾 Results saved:")
    print(f"   - {output_json}")
    print(f"   - {output_csv}")

    return solution


def run_multiday_optimization(algorithm="ortools"):
    """Run multi-day weekly optimization with your data"""
    # Load data
    loader = CustomDataLoader(input_dir="input")
    stores, vehicles, depot_info, distance_matrix, time_matrix = loader.load_all_data()

    if stores is None:
        print("❌ Failed to load data. Exiting.")
        return None

    # Create solver
    print(f"\n🚀 Running Multi-Day Optimization (using {algorithm.upper()})...")
    print("=" * 60)

    if algorithm.lower() == "ortools":
        solver = ORToolsSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])
    elif algorithm.lower() == "alns":
        solver = ALNSSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])
    else:
        solver = ClarkeWrightSolver(stores, vehicles, distance_matrix, time_matrix, depot_id=depot_info["id"])

    # Create multi-day optimizer
    multiday_optimizer = MultiDayOptimizer(
        stores=stores,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
        time_matrix=time_matrix,
        solver=solver,
        consolidation_threshold=70.0,
    )

    # Optimize week
    start_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    weekly_solution = multiday_optimizer.optimize_week(start_date=start_date)

    # Display results
    print("\n📊 WEEKLY OPTIMIZATION RESULTS")
    print("=" * 60)

    stats = weekly_solution.consolidation_stats
    print("\n🎯 Consolidation Statistics:")
    print(f"   Total stores: {stats['total_stores']}")
    print(f"   Consolidation rate: {stats['consolidation_rate_percent']:.1f}%")
    print(f"   Trip reduction: {stats['trip_reduction_percent']:.1f}%")

    print("\n📅 Daily Summary:")
    total_distance = 0
    total_cost = 0

    for day, solution in weekly_solution.daily_solutions.items():
        print(f"\n{day}:")
        print(f"  Vehicles: {solution.num_vehicles_used}")
        print(f"  Stores: {solution.get_total_stores_served()}")
        print(f"  Distance: {solution.total_distance_km:.2f} km")
        print(f"  Cost: ${solution.total_cost:.2f}")
        print(f"  Avg utilization: {solution.get_average_utilization():.1f}%")

        total_distance += solution.total_distance_km
        total_cost += solution.total_cost

    print("\n📈 Weekly Totals:")
    print(f"   Total distance: {total_distance:.2f} km")
    print(f"   Total cost: ${total_cost:.2f}")

    # Save results
    os.makedirs("output", exist_ok=True)
    import json

    with open("output/weekly_solution.json", "w") as f:
        json.dump(weekly_solution.to_dict(), f, indent=2)

    print(f"\n💾 Results saved to: output/weekly_solution.json")

    return weekly_solution


def main():
    """Main function with menu"""
    import sys

    print("\n" + "=" * 60)
    print("🚛 VRP OPTIMIZATION - CUSTOM DATA")
    print("=" * 60)

    # Check if input folder exists and has files
    if not os.path.exists("input"):
        print("\n❌ Input folder not found!")
        print("   Creating 'input/' directory...")
        os.makedirs("input", exist_ok=True)
        print("   Please add your data files to the 'input/' folder")
        print("\n   Run: python load_custom_data.py")
        print("   to see the expected data format")
        return

    input_files = os.listdir("input")
    if not input_files:
        print("\n⚠️  Input folder is empty!")
        print("   Please add your data files (stores.csv, vehicles.csv)")
        print("\n   Run: python load_custom_data.py")
        print("   to see the expected data format")
        return

    print(f"\n📂 Found {len(input_files)} file(s) in input/:")
    for f in input_files:
        print(f"   - {f}")

    # Menu
    print("\n" + "=" * 60)
    print("SELECT OPTIMIZATION TYPE:")
    print("=" * 60)
    print("1. Single Day Optimization (one day)")
    print("2. Multi-Day Weekly Optimization (Mon-Fri)")
    print("3. Compare All Algorithms (single day)")
    print("4. Show Data Format Guide")
    print("5. Exit")
    print("=" * 60)

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        # Single day
        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"
        algo = input("Algorithm (ortools/alns/clarke-wright) [ortools]: ").strip() or "ortools"
        run_single_day_optimization(day=day, algorithm=algo)

    elif choice == "2":
        # Multi-day
        algo = input("Algorithm for daily optimization (ortools/alns/clarke-wright) [ortools]: ").strip() or "ortools"
        run_multiday_optimization(algorithm=algo)

    elif choice == "3":
        # Compare algorithms
        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"
        print("\n" + "=" * 60)
        print("COMPARING ALL ALGORITHMS")
        print("=" * 60)

        for algo in ["clarke-wright", "ortools", "alns"]:
            print(f"\n{'='*60}")
            print(f"Algorithm: {algo.upper()}")
            print("=" * 60)
            run_single_day_optimization(day=day, algorithm=algo, time_limit=60)
            print("\n")

    elif choice == "4":
        # Show format guide
        from load_custom_data import print_data_format_guide

        print_data_format_guide()

    elif choice == "5":
        print("\n👋 Goodbye!")
        return

    else:
        print("\n❌ Invalid choice")


if __name__ == "__main__":
    main()
