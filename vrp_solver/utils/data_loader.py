"""
Data Loading Utilities
"""
import json
import csv
from typing import List, Dict, Tuple
from datetime import datetime, time
from ..models import Store, Vehicle, TimeWindow, ForbiddenInterval


class DataLoader:
    """Load data from various formats"""

    @staticmethod
    def load_stores_from_json(file_path: str) -> List[Store]:
        """Load stores from JSON file"""
        with open(file_path, "r") as f:
            data = json.load(f)

        stores = []
        for item in data:
            # Parse time windows
            time_windows = []
            if "time_windows" in item:
                for tw_data in item["time_windows"]:
                    tw = TimeWindow(
                        earliest=tw_data["earliest"],
                        latest=tw_data["latest"],
                        day=tw_data.get("day"),
                    )
                    time_windows.append(tw)

            # Parse forbidden intervals
            forbidden_intervals = []
            if "forbidden_intervals" in item:
                for fi_data in item["forbidden_intervals"]:
                    fi = ForbiddenInterval(
                        start=fi_data["start"],
                        end=fi_data["end"],
                        reason=fi_data.get("reason", "Blackout"),
                    )
                    forbidden_intervals.append(fi)

            store = Store(
                id=item["id"],
                name=item["name"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                demand_cbm=item["demand_cbm"],
                time_windows=time_windows,
                forbidden_intervals=forbidden_intervals,
                excluded_days=item.get("excluded_days", []),
                preferred_days=item.get("preferred_days", []),
                service_time_minutes=item.get("service_time_minutes", 60),
                notes=item.get("notes", ""),
                priority=item.get("priority", 1),
            )
            stores.append(store)

        return stores

    @staticmethod
    def load_stores_from_csv(file_path: str) -> List[Store]:
        """Load stores from CSV file"""
        stores = []

        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Basic fields
                store = Store(
                    id=row["id"],
                    name=row["name"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    demand_cbm=float(row["demand_cbm"]),
                    service_time_minutes=int(row.get("service_time_minutes", 60)),
                    priority=int(row.get("priority", 1)),
                )

                # Parse time windows (format: "08:00-17:00" or "Mon:08:00-17:00")
                if "time_window" in row and row["time_window"]:
                    tw_str = row["time_window"]
                    day = None

                    if ":" in tw_str and tw_str.count(":") > 2:
                        # Has day prefix
                        parts = tw_str.split(":", 1)
                        day = parts[0]
                        tw_str = parts[1]

                    times = tw_str.split("-")
                    if len(times) == 2:
                        tw = TimeWindow(earliest=times[0], latest=times[1], day=day)
                        store.time_windows.append(tw)

                # Parse excluded days (format: "Mon,Wed,Fri")
                if "excluded_days" in row and row["excluded_days"]:
                    store.excluded_days = [d.strip() for d in row["excluded_days"].split(",")]

                stores.append(store)

        return stores

    @staticmethod
    def load_vehicles_from_json(file_path: str) -> List[Vehicle]:
        """Load vehicles from JSON file"""
        with open(file_path, "r") as f:
            data = json.load(f)

        vehicles = []
        for item in data:
            vehicle = Vehicle(
                id=item["id"],
                name=item["name"],
                capacity_cbm=item["capacity_cbm"],
                allowed_store_ids=set(item.get("allowed_store_ids", [])),
                forbidden_store_ids=set(item.get("forbidden_store_ids", [])),
                max_route_duration_hours=item.get("max_route_duration_hours", 12.0),
                start_time=item.get("start_time", "08:00"),
                fixed_cost=item.get("fixed_cost", 1000.0),
                cost_per_km=item.get("cost_per_km", 2.0),
                vehicle_type=item.get("vehicle_type", "Standard"),
                driver_name=item.get("driver_name", ""),
            )
            vehicles.append(vehicle)

        return vehicles

    @staticmethod
    def load_vehicles_from_csv(file_path: str) -> List[Vehicle]:
        """Load vehicles from CSV file"""
        vehicles = []

        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehicle = Vehicle(
                    id=row["id"],
                    name=row["name"],
                    capacity_cbm=float(row["capacity_cbm"]),
                    max_route_duration_hours=float(row.get("max_route_duration_hours", 12.0)),
                    start_time=row.get("start_time", "08:00"),
                    fixed_cost=float(row.get("fixed_cost", 1000.0)),
                    cost_per_km=float(row.get("cost_per_km", 2.0)),
                    vehicle_type=row.get("vehicle_type", "Standard"),
                    driver_name=row.get("driver_name", ""),
                )
                vehicles.append(vehicle)

        return vehicles

    @staticmethod
    def save_solution_to_json(solution, file_path: str):
        """Save solution to JSON file"""
        with open(file_path, "w") as f:
            json.dump(solution.to_dict(), f, indent=2)

    @staticmethod
    def save_solution_to_csv(solution, file_path: str):
        """Save solution to CSV file (route details)"""
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "route_id",
                    "vehicle_id",
                    "vehicle_name",
                    "stop_sequence",
                    "store_id",
                    "store_name",
                    "arrival_time",
                    "departure_time",
                    "load_cbm",
                    "distance_km",
                    "utilization_%",
                ]
            )

            for route_idx, route in enumerate(solution.routes):
                for stop in route.stops:
                    arrival_str = stop.arrival_time.strftime("%H:%M") if stop.arrival_time else ""
                    departure_str = stop.departure_time.strftime("%H:%M") if stop.departure_time else ""

                    writer.writerow(
                        [
                            f"R{route_idx + 1}",
                            route.vehicle.id,
                            route.vehicle.name,
                            stop.sequence + 1,
                            stop.store.id,
                            stop.store.name,
                            arrival_str,
                            departure_str,
                            round(route.total_load_cbm, 2),
                            round(route.total_distance_km, 2),
                            round(route.get_load_utilization(), 2),
                        ]
                    )
