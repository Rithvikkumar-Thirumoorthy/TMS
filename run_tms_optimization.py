"""
Run VRP Optimization on TMS Data
Optimizes delivery routes for your store network
"""
import os
from datetime import datetime
from load_tms_data import TMSDataLoader
from vrp_solver.solvers import ORToolsSolver, ALNSSolver, ClarkeWrightSolver
from vrp_solver.utils import DataLoader
import json


def run_single_day_optimization(target_dc="NDC", day="Mon", algorithm="ortools", time_limit=120):
    """
    Run single-day VRP optimization

    Args:
        target_dc: DC to optimize for (e.g., 'NDC', 'EDC', 'DC_KLANG'). Defaults to 'NDC'.
        day: Day of week (Mon/Tue/Wed/Thu/Fri)
        algorithm: Solver to use (ortools/alns/clarke-wright)
        time_limit: Time limit in seconds for OR-Tools
    """
    # Load data
    loader = TMSDataLoader()
    stores, vehicles, depot_info, distance_matrix, time_matrix = loader.load_all_data(target_dc=target_dc)

    if stores is None or len(stores) == 0:
        print("❌ No stores loaded. Exiting.")
        return None

    # Update store demands for the specific day
    print(f"\n🔄 Setting demands for {day}...")
    total_demand = 0
    stores_with_orders = 0

    for store in stores:
        if hasattr(store, 'daily_demands') and day in store.daily_demands:
            daily_demand = store.daily_demands[day]
            if daily_demand > 0:
                store.demand_cbm = daily_demand
                total_demand += daily_demand
                stores_with_orders += 1
            else:
                store.demand_cbm = 0

    print(f"   Stores with orders on {day}: {stores_with_orders}/{len(stores)}")
    print(f"   Total demand: {total_demand:.2f} CBM")

    # Filter out stores with no demand on this day
    stores = [s for s in stores if s.demand_cbm > 0]

    if len(stores) == 0:
        print(f"❌ No stores have orders on {day}. Exiting.")
        return None

    print(f"   Active stores: {len(stores)}")

    # Create solver
    print(f"\n🚀 Running {algorithm.upper()} optimization for {day}...")
    print("=" * 70)

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
        return None

    # Display results
    print("\n📊 OPTIMIZATION RESULTS")
    print("=" * 70)
    print(f"DC: {target_dc or 'Default'}")
    print(f"Day: {day}")
    print(f"Algorithm: {algorithm.upper()}")
    print("-" * 70)
    print(f"✓ Feasible: {solution.is_feasible}")
    print(f"✓ Vehicles used: {solution.num_vehicles_used}/{len(vehicles)}")
    print(f"✓ Stores served: {solution.get_total_stores_served()}/{len(stores)}")
    print(f"✓ Total distance: {solution.total_distance_km:.2f} km")
    print(f"✓ Total duration: {solution.total_duration_hours:.2f} hours")
    print(f"✓ Total cost: ${solution.total_cost:,.2f}")
    print(f"✓ Average utilization: {solution.get_average_utilization():.1f}%")

    # Utilization stats
    util_stats = solution.get_utilization_stats()
    print(f"\n📈 Utilization Statistics:")
    print(f"   Min: {util_stats['min']:.1f}%")
    print(f"   Max: {util_stats['max']:.1f}%")
    print(f"   Avg: {util_stats['avg']:.1f}%")
    print(f"   Std Dev: {util_stats['std']:.1f}%")

    if not solution.is_feasible:
        print(f"\n⚠️  Constraint Violations:")
        for violation in solution.constraint_violations[:10]:  # Show first 10
            print(f"   - {violation}")

    if solution.unserved_stores:
        print(f"\n⚠️  Unserved Stores: {len(solution.unserved_stores)}")
        for store_id in solution.unserved_stores[:5]:
            print(f"   - {store_id}")

    # Print routes summary
    print("\n📦 ROUTES SUMMARY")
    print("=" * 70)
    for i, route in enumerate(solution.routes, 1):
        print(f"\nRoute {i} - {route.vehicle.name}")
        print(f"  Vehicle: {route.vehicle.id} (Capacity: {route.vehicle.capacity_cbm} CBM)")
        print(f"  Stops: {len(route.stops)}")
        print(f"  Sequence: {' → '.join([stop.store.id for stop in route.stops])}")
        print(f"  Distance: {route.total_distance_km:.2f} km")
        print(f"  Duration: {route.total_duration_minutes:.0f} min ({route.total_duration_minutes/60:.1f} hrs)")
        print(f"  Load: {route.total_load_cbm:.2f}/{route.vehicle.capacity_cbm} CBM ({route.get_load_utilization():.1f}%)")

        # Show schedule for first route
        if i == 1:
            print(f"\n  Detailed Schedule:")
            for stop in route.stops:
                if stop.arrival_time:
                    print(f"    {stop.arrival_time.strftime('%H:%M')} - {stop.departure_time.strftime('%H:%M')}: "
                          f"{stop.store.id} ({stop.store.demand_cbm:.1f} CBM)")

    # Save results
    os.makedirs("output", exist_ok=True)
    dc_name = (target_dc or "default").replace("_", "-")
    output_json = f"output/solution_{dc_name}_{day}_{algorithm}.json"
    output_csv = f"output/solution_{dc_name}_{day}_{algorithm}.csv"

    DataLoader.save_solution_to_json(solution, output_json)
    DataLoader.save_solution_to_csv(solution, output_csv)

    print(f"\n💾 Results saved:")
    print(f"   📄 {output_json}")
    print(f"   📊 {output_csv}")

    return solution


def run_weekly_optimization(target_dc="NDC", algorithm="ortools"):
    """
    Run optimization for entire week (Mon-Fri)

    Args:
        target_dc: DC to optimize for
        algorithm: Solver to use
    """
    loader = TMSDataLoader()

    print("\n🗓️  WEEKLY OPTIMIZATION")
    print("=" * 70)

    weekly_results = {}
    total_distance = 0
    total_cost = 0
    total_vehicles = 0
    total_stores = 0

    for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        print(f"\n{'='*70}")
        print(f"📅 Optimizing {day}")
        print("=" * 70)

        solution = run_single_day_optimization(
            target_dc=target_dc,
            day=day,
            algorithm=algorithm,
            time_limit=60  # Faster for weekly
        )

        if solution:
            weekly_results[day] = solution
            total_distance += solution.total_distance_km
            total_cost += solution.total_cost
            total_vehicles += solution.num_vehicles_used
            total_stores += solution.get_total_stores_served()

    # Weekly summary
    print("\n" + "=" * 70)
    print("📈 WEEKLY SUMMARY")
    print("=" * 70)
    print(f"Total Distance: {total_distance:.2f} km")
    print(f"Total Cost: ${total_cost:,.2f}")
    print(f"Total Vehicle-Days: {total_vehicles}")
    print(f"Total Deliveries: {total_stores}")
    print(f"Avg Distance/Day: {total_distance/5:.2f} km")
    print(f"Avg Vehicles/Day: {total_vehicles/5:.1f}")

    # Save weekly summary
    os.makedirs("output", exist_ok=True)
    dc_name = (target_dc or "default").replace("_", "-")

    weekly_summary = {
        "dc": target_dc,
        "algorithm": algorithm,
        "total_distance_km": round(total_distance, 2),
        "total_cost": round(total_cost, 2),
        "total_vehicle_days": total_vehicles,
        "total_deliveries": total_stores,
        "daily_results": {}
    }

    for day, solution in weekly_results.items():
        weekly_summary["daily_results"][day] = solution.to_dict()

    output_file = f"output/weekly_summary_{dc_name}_{algorithm}.json"
    with open(output_file, 'w') as f:
        json.dump(weekly_summary, f, indent=2)

    print(f"\n💾 Weekly summary saved: {output_file}")

    return weekly_results


def main():
    """Interactive menu"""
    print("\n" + "=" * 70)
    print("🚛 TMS VRP OPTIMIZATION")
    print("=" * 70)

    # Get available DCs
    loader = TMSDataLoader()
    dcs = loader.get_available_dcs()

    print(f"\n📍 Available Distribution Centers ({len(dcs)}):")
    for i, dc in enumerate(dcs, 1):
        print(f"   {i}. {dc}")

    # Menu
    print("\n" + "=" * 70)
    print("SELECT OPTIMIZATION TYPE:")
    print("=" * 70)
    print("1. Single Day Optimization")
    print("2. Weekly Optimization (Mon-Fri)")
    print("3. Compare Algorithms (single day)")
    print("4. Exit")
    print("=" * 70)

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        # Single day
        dc_choice = input(f"\nSelect DC (1-{len(dcs)}) or press Enter for first DC: ").strip()
        target_dc = dcs[int(dc_choice)-1] if dc_choice.isdigit() and 1 <= int(dc_choice) <= len(dcs) else dcs[0]

        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"
        algo = input("Algorithm (ortools/alns/clarke-wright) [ortools]: ").strip() or "ortools"

        run_single_day_optimization(target_dc=target_dc, day=day, algorithm=algo)

    elif choice == "2":
        # Weekly
        dc_choice = input(f"\nSelect DC (1-{len(dcs)}) or press Enter for first DC: ").strip()
        target_dc = dcs[int(dc_choice)-1] if dc_choice.isdigit() and 1 <= int(dc_choice) <= len(dcs) else dcs[0]

        algo = input("Algorithm (ortools/alns/clarke-wright) [ortools]: ").strip() or "ortools"

        run_weekly_optimization(target_dc=target_dc, algorithm=algo)

    elif choice == "3":
        # Compare
        dc_choice = input(f"\nSelect DC (1-{len(dcs)}) or press Enter for first DC: ").strip()
        target_dc = dcs[int(dc_choice)-1] if dc_choice.isdigit() and 1 <= int(dc_choice) <= len(dcs) else dcs[0]

        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"

        for algo in ["clarke-wright", "ortools"]:  # Skip ALNS for speed
            print(f"\n{'='*70}")
            print(f"Algorithm: {algo.upper()}")
            print("=" * 70)
            run_single_day_optimization(target_dc=target_dc, day=day, algorithm=algo, time_limit=60)

    elif choice == "4":
        print("\n👋 Goodbye!")
        return

    else:
        print("\n❌ Invalid choice")


if __name__ == "__main__":
    main()
