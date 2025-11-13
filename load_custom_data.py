"""
Custom Data Loader for Your Input Files
This script helps load and process your custom input data
"""
import os
import json
import pandas as pd
from datetime import datetime
from vrp_solver.models import Store, Vehicle, TimeWindow, ForbiddenInterval
from vrp_solver.utils import DistanceCalculator, DataLoader


class CustomDataLoader:
    """Load and process custom input data"""

    def __init__(self, input_dir="input"):
        self.input_dir = input_dir

    def load_stores_from_csv(self, filename="stores.csv"):
        """
        Load stores from CSV file
        Expected columns: id, name, latitude, longitude, demand_cbm
        Optional: time_window_start, time_window_end, excluded_days, service_time_minutes
        """
        filepath = os.path.join(self.input_dir, filename)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return []

        df = pd.read_csv(filepath)
        stores = []

        print(f"📦 Loading stores from {filename}...")
        print(f"   Found {len(df)} stores")

        for _, row in df.iterrows():
            # Parse time windows
            time_windows = []
            if "time_window_start" in df.columns and "time_window_end" in df.columns:
                if pd.notna(row.get("time_window_start")) and pd.notna(row.get("time_window_end")):
                    tw = TimeWindow(
                        earliest=str(row["time_window_start"]),
                        latest=str(row["time_window_end"]),
                        day=row.get("day", None),
                    )
                    time_windows.append(tw)

            # If no time windows, use default
            if not time_windows:
                time_windows.append(TimeWindow(earliest="08:00", latest="17:00", day=None))

            # Parse excluded days
            excluded_days = []
            if "excluded_days" in df.columns and pd.notna(row.get("excluded_days")):
                excluded_days = [d.strip() for d in str(row["excluded_days"]).split(",")]

            # Create store
            store = Store(
                id=str(row["id"]),
                name=str(row["name"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                demand_cbm=float(row["demand_cbm"]),
                time_windows=time_windows,
                excluded_days=excluded_days,
                service_time_minutes=int(row.get("service_time_minutes", 60)),
                priority=int(row.get("priority", 1)),
            )
            stores.append(store)

        print(f"   ✓ Loaded {len(stores)} stores successfully")
        return stores

    def load_vehicles_from_csv(self, filename="vehicles.csv"):
        """
        Load vehicles from CSV
        Expected columns: id, name, capacity_cbm
        Optional: max_route_duration_hours, start_time, fixed_cost, cost_per_km
        """
        filepath = os.path.join(self.input_dir, filename)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return []

        df = pd.read_csv(filepath)
        vehicles = []

        print(f"🚛 Loading vehicles from {filename}...")
        print(f"   Found {len(df)} vehicles")

        for _, row in df.iterrows():
            vehicle = Vehicle(
                id=str(row["id"]),
                name=str(row["name"]),
                capacity_cbm=float(row["capacity_cbm"]),
                max_route_duration_hours=float(row.get("max_route_duration_hours", 12.0)),
                start_time=str(row.get("start_time", "08:00")),
                fixed_cost=float(row.get("fixed_cost", 1000.0)),
                cost_per_km=float(row.get("cost_per_km", 2.0)),
                vehicle_type=str(row.get("vehicle_type", "Standard")),
            )
            vehicles.append(vehicle)

        print(f"   ✓ Loaded {len(vehicles)} vehicles successfully")
        return vehicles

    def load_depot_location(self, filename="depot.csv"):
        """
        Load depot location
        Expected columns: id, name, latitude, longitude
        """
        filepath = os.path.join(self.input_dir, filename)

        if not os.path.exists(filepath):
            print(f"⚠️  Depot file not found, using default location")
            return "depot", 40.7580, -73.9855

        df = pd.read_csv(filepath)
        if len(df) > 0:
            row = df.iloc[0]
            depot_id = str(row.get("id", "depot"))
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            print(f"📍 Loaded depot: {depot_id} at ({lat}, {lon})")
            return depot_id, lat, lon

        return "depot", 40.7580, -73.9855

    def load_all_data(self):
        """
        Load all data files and prepare for optimization
        Returns: stores, vehicles, depot_info, distance_matrix, time_matrix
        """
        print("\n" + "=" * 60)
        print("📂 LOADING CUSTOM INPUT DATA")
        print("=" * 60 + "\n")

        # Load stores
        stores = self.load_stores_from_csv("stores.csv")
        if not stores:
            print("\n❌ No stores loaded. Please check your stores.csv file.")
            return None, None, None, None, None

        # Load vehicles
        vehicles = self.load_vehicles_from_csv("vehicles.csv")
        if not vehicles:
            print("\n❌ No vehicles loaded. Please check your vehicles.csv file.")
            return None, None, None, None, None

        # Load depot
        depot_id, depot_lat, depot_lon = self.load_depot_location("depot.csv")

        # Build distance matrix
        print("\n📐 Building distance and time matrices...")
        locations = {depot_id: (depot_lat, depot_lon)}
        for store in stores:
            locations[store.id] = (store.latitude, store.longitude)

        distance_matrix = DistanceCalculator.build_distance_matrix(locations, method="haversine")
        time_matrix = DistanceCalculator.build_time_matrix(distance_matrix, avg_speed_kmh=40.0)

        print("   ✓ Distance matrix built")
        print("   ✓ Time matrix built")

        depot_info = {"id": depot_id, "latitude": depot_lat, "longitude": depot_lon}

        print("\n" + "=" * 60)
        print("✅ DATA LOADED SUCCESSFULLY")
        print("=" * 60)
        print(f"   Stores: {len(stores)}")
        print(f"   Vehicles: {len(vehicles)}")
        print(f"   Depot: {depot_id}")
        print("=" * 60 + "\n")

        return stores, vehicles, depot_info, distance_matrix, time_matrix

    def detect_and_load(self):
        """
        Auto-detect data files and load them
        Supports CSV, JSON, and Excel formats
        """
        print("🔍 Detecting input files...")

        # Check for CSV files
        csv_files = [f for f in os.listdir(self.input_dir) if f.endswith(".csv")]
        json_files = [f for f in os.listdir(self.input_dir) if f.endswith(".json")]
        excel_files = [f for f in os.listdir(self.input_dir) if f.endswith((".xlsx", ".xls"))]

        print(f"   Found {len(csv_files)} CSV files")
        print(f"   Found {len(json_files)} JSON files")
        print(f"   Found {len(excel_files)} Excel files")

        # Try to load based on what's available
        if csv_files:
            return self.load_all_data()
        elif json_files:
            # Check for JSON format
            stores = None
            vehicles = None
            if "stores.json" in json_files:
                stores = DataLoader.load_stores_from_json(os.path.join(self.input_dir, "stores.json"))
            if "vehicles.json" in json_files:
                vehicles = DataLoader.load_vehicles_from_json(os.path.join(self.input_dir, "vehicles.json"))

            if stores and vehicles:
                # Build matrices
                depot_id = "depot"
                locations = {depot_id: (40.7580, -73.9855)}
                for store in stores:
                    locations[store.id] = (store.latitude, store.longitude)

                distance_matrix = DistanceCalculator.build_distance_matrix(locations)
                time_matrix = DistanceCalculator.build_time_matrix(distance_matrix)

                depot_info = {"id": depot_id, "latitude": 40.7580, "longitude": -73.9855}
                return stores, vehicles, depot_info, distance_matrix, time_matrix

        print("\n⚠️  Could not auto-detect data format.")
        print("   Please ensure you have one of:")
        print("   - stores.csv and vehicles.csv")
        print("   - stores.json and vehicles.json")

        return None, None, None, None, None


def print_data_format_guide():
    """Print expected data format"""
    print("\n" + "=" * 60)
    print("📋 EXPECTED DATA FORMAT")
    print("=" * 60)

    print("\n1. stores.csv (Required columns):")
    print("   - id: Unique store identifier (e.g., S001)")
    print("   - name: Store name")
    print("   - latitude: Latitude coordinate")
    print("   - longitude: Longitude coordinate")
    print("   - demand_cbm: Demand in cubic meters")
    print("\n   Optional columns:")
    print("   - time_window_start: e.g., 09:00")
    print("   - time_window_end: e.g., 17:00")
    print("   - excluded_days: e.g., Mon,Wed (comma-separated)")
    print("   - service_time_minutes: e.g., 60")
    print("   - priority: e.g., 1")

    print("\n2. vehicles.csv (Required columns):")
    print("   - id: Unique vehicle identifier (e.g., V001)")
    print("   - name: Vehicle name")
    print("   - capacity_cbm: Capacity in cubic meters")
    print("\n   Optional columns:")
    print("   - max_route_duration_hours: e.g., 12.0")
    print("   - start_time: e.g., 08:00")
    print("   - fixed_cost: e.g., 1000.0")
    print("   - cost_per_km: e.g., 2.5")

    print("\n3. depot.csv (Optional):")
    print("   - id: Depot identifier")
    print("   - name: Depot name")
    print("   - latitude: Latitude coordinate")
    print("   - longitude: Longitude coordinate")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Show format guide
    print_data_format_guide()

    # Try to load data
    loader = CustomDataLoader(input_dir="input")
    result = loader.detect_and_load()

    if result[0] is None:
        print("\n💡 TIP: Place your data files in the 'input/' directory")
        print("   See format guide above for expected columns")
