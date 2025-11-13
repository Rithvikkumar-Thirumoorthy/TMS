"""
Custom Data Loader for TMS Input Data
Loads the specific data format from Input/ folder
"""
import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import List, Dict, Tuple
from vrp_solver.models import Store, Vehicle, TimeWindow, ForbiddenInterval


class TMSDataLoader:
    """Load TMS-specific data format from Input/ folder"""

    def __init__(self, input_dir="Input"):
        self.input_dir = input_dir
        self.weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.weekday_short = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri"}

    def load_all_data(self, target_dc="NDC"):
        """
        Load all data files and prepare for optimization

        Args:
            target_dc: Filter stores by DC (e.g., 'NDC', 'EDC', 'DC_KLANG'). Defaults to 'NDC'.

        Returns: stores, vehicles, depot_info, distance_matrix, time_matrix
        """
        print("\n" + "=" * 70)
        print("📂 LOADING TMS DATA")
        print("=" * 70)

        # Load master store data
        print("\n📦 Loading store data...")
        master_df = pd.read_csv(f"{self.input_dir}/master_store_data.csv")

        # Filter by DC
        master_df = master_df[master_df['fulfilment_dc_standard'] == target_dc]
        print(f"   Filtered to DC: {target_dc}")

        # Filter stores with orders
        master_df = master_df[master_df['has_orders'] == True]
        master_df = master_df[master_df['data_complete'] == True]

        print(f"   Found {len(master_df)} stores with complete data")

        # Load time windows
        print("\n⏰ Loading time windows...")
        time_windows_df = pd.read_csv(f"{self.input_dir}/store_time_windows.csv")

        # Load constraints
        print("\n🚫 Loading constraints...")
        constraints_df = pd.read_csv(f"{self.input_dir}/store_constraints_cleaned.csv")

        # Create stores
        stores = self._create_stores(master_df, time_windows_df, constraints_df)
        print(f"   ✓ Created {len(stores)} store objects")

        # Load fleet
        print("\n🚛 Loading fleet...")
        fleet_df = pd.read_csv(f"{self.input_dir}/fleet_cleaned.csv")

        # Find corresponding DC code for the target_dc
        dc_df = pd.read_csv(f"{self.input_dir}/dc_locations_cleaned.csv")
        dc_mapping = dict(zip(dc_df['dc_name_standard'], dc_df['dc_code']))

        # Map DC names
        dc_code_variants = []
        if target_dc in dc_mapping:
            dc_code_variants.append(dc_mapping[target_dc])
        dc_code_variants.extend(['EDC', 'NDC', 'SDC'])  # Common DC codes

        # Filter fleet by DC
        fleet_df = fleet_df[fleet_df['owning_dc'].isin(dc_code_variants)]

        if len(fleet_df) == 0:
            print(f"   ⚠️  No vehicles found for {target_dc}, using all vehicles")
            fleet_df = pd.read_csv(f"{self.input_dir}/fleet_cleaned.csv")

        vehicles = self._create_vehicles(fleet_df)
        print(f"   ✓ Created {len(vehicles)} vehicle objects")

        # Load depot location
        print("\n📍 Loading depot location...")
        depot_info = self._load_depot(target_dc)
        print(f"   ✓ Depot: {depot_info['name']} at ({depot_info['latitude']:.4f}, {depot_info['longitude']:.4f})")

        # Load distance and time matrices
        print("\n📐 Loading pre-calculated matrices...")
        distance_matrix = self._load_distance_matrix(stores, depot_info['id'])
        time_matrix = self._load_time_matrix(stores, depot_info['id'])
        print(f"   ✓ Distance matrix loaded")
        print(f"   ✓ Time matrix loaded")

        print("\n" + "=" * 70)
        print("✅ DATA LOADED SUCCESSFULLY")
        print("=" * 70)
        print(f"   DC: {target_dc}")
        print(f"   Stores: {len(stores)}")
        print(f"   Vehicles: {len(vehicles)}")
        print(f"   Depot: {depot_info['name']}")
        print("=" * 70 + "\n")

        return stores, vehicles, depot_info, distance_matrix, time_matrix

    def _create_stores(self, master_df, time_windows_df, constraints_df) -> List[Store]:
        """Create Store objects from dataframes"""
        stores = []

        for _, row in master_df.iterrows():
            store_id = row['store_id']

            # Get time windows for this store
            store_tw_df = time_windows_df[time_windows_df['store_id'] == store_id]
            time_windows = []

            for _, tw_row in store_tw_df.iterrows():
                day = tw_row['day_of_week']
                day_short = self.weekday_short.get(day, day)

                # Parse forbidden intervals if present
                forbidden_intervals = []
                if pd.notna(tw_row.get('forbidden_intervals')) and tw_row['forbidden_intervals']:
                    # Parse forbidden intervals format (if provided)
                    pass

                tw = TimeWindow(
                    earliest=tw_row['allowed_start_time'],
                    latest=tw_row['allowed_end_time'],
                    day=day_short
                )
                time_windows.append(tw)

            # Get excluded days
            excluded_days = []
            if pd.notna(row.get('excluded_days_str')) and row['excluded_days_str']:
                excluded_days = [self.weekday_short.get(d.strip(), d.strip()) for d in str(row['excluded_days_str']).split(',')]

            # Create store (use weekly demand for now)
            store = Store(
                id=store_id,
                name=store_id,
                latitude=row['latitude'],
                longitude=row['longitude'],
                demand_cbm=row['weekly_order_cbm'],  # Total weekly demand
                time_windows=time_windows if time_windows else [TimeWindow(earliest="08:00", latest="17:00")],
                excluded_days=excluded_days,
                service_time_minutes=60,
                priority=1
            )

            # Store daily demands as metadata for multi-day optimization
            store.daily_demands = {
                'Mon': row.get('monday_cbm', 0.0),
                'Tue': row.get('tuesday_cbm', 0.0),
                'Wed': row.get('wednesday_cbm', 0.0),
                'Thu': row.get('thursday_cbm', 0.0),
                'Fri': row.get('friday_cbm', 0.0),
            }

            stores.append(store)

        return stores

    def _create_vehicles(self, fleet_df) -> List[Vehicle]:
        """Create Vehicle objects from fleet dataframe"""
        vehicles = []

        for _, row in fleet_df.iterrows():
            vehicle = Vehicle(
                id=row['vehicle_id'],
                name=f"{row['vehicle_id']} ({row['vehicle_type']})",
                capacity_cbm=row['cbm'],
                max_route_duration_hours=12.0,
                start_time="08:00",
                fixed_cost=1000.0,
                cost_per_km=2.5,
                vehicle_type=row['vehicle_type']
            )
            vehicles.append(vehicle)

        # Limit to reasonable fleet size for optimization
        if len(vehicles) > 50:
            print(f"   ℹ️  Using top 50 vehicles by capacity (total available: {len(vehicles)})")
            vehicles = sorted(vehicles, key=lambda v: v.capacity_cbm, reverse=True)[:50]

        return vehicles

    def _load_depot(self, target_dc) -> Dict:
        """Load depot information"""
        dc_df = pd.read_csv(f"{self.input_dir}/dc_locations_cleaned.csv")

        # Find matching DC
        dc_row = dc_df[dc_df['dc_name_standard'] == target_dc]

        if len(dc_row) == 0:
            # Use first DC
            dc_row = dc_df.iloc[0]
        else:
            dc_row = dc_row.iloc[0]

        return {
            'id': 'depot',  # Use generic 'depot' as ID
            'name': dc_row['dc_name'],
            'latitude': dc_row['latitude'],
            'longitude': dc_row['longitude']
        }

    def _load_distance_matrix(self, stores, depot_id) -> Dict[str, Dict[str, float]]:
        """Load pre-calculated distance matrix"""
        print("   Loading distance matrix from CSV...")
        dist_df = pd.read_csv(f"{self.input_dir}/store_distance_matrix_km.csv", index_col=0)

        # Convert to dict format
        distance_matrix = {}
        distance_matrix[depot_id] = {}

        store_ids = [s.id for s in stores]
        stores_in_matrix = 0

        # Extract submatrix for our stores
        for store1 in stores:
            if store1.id not in dist_df.index:
                print(f"   ⚠️  Store {store1.id} not in distance matrix, skipping")
                continue

            stores_in_matrix += 1
            distance_matrix[store1.id] = {}

            for store2 in stores:
                if store2.id not in dist_df.columns:
                    continue

                dist = dist_df.loc[store1.id, store2.id]
                distance_matrix[store1.id][store2.id] = float(dist) if not pd.isna(dist) else 0.0

            # Depot distances (use reasonable estimates)
            distance_matrix[store1.id][depot_id] = 20.0  # 20km default to depot
            distance_matrix[depot_id][store1.id] = 20.0

        distance_matrix[depot_id][depot_id] = 0.0

        print(f"   Loaded distances for {stores_in_matrix}/{len(stores)} stores")
        return distance_matrix

    def _load_time_matrix(self, stores, depot_id) -> Dict[str, Dict[str, float]]:
        """Load pre-calculated time matrix"""
        print("   Loading time matrix from CSV...")
        time_df = pd.read_csv(f"{self.input_dir}/store_duration_matrix_min.csv", index_col=0)

        # Convert to dict format
        time_matrix = {}
        time_matrix[depot_id] = {}

        stores_in_matrix = 0

        for store1 in stores:
            if store1.id not in time_df.index:
                continue

            stores_in_matrix += 1
            time_matrix[store1.id] = {}

            for store2 in stores:
                if store2.id not in time_df.columns:
                    continue

                duration = time_df.loc[store1.id, store2.id]
                time_matrix[store1.id][store2.id] = float(duration) if not pd.isna(duration) else 0.0

            # Depot times (30 min default to/from depot)
            time_matrix[store1.id][depot_id] = 30.0
            time_matrix[depot_id][store1.id] = 30.0

        time_matrix[depot_id][depot_id] = 0.0

        print(f"   Loaded times for {stores_in_matrix}/{len(stores)} stores")
        return time_matrix

    def get_available_dcs(self) -> List[str]:
        """Get list of available DCs"""
        master_df = pd.read_csv(f"{self.input_dir}/master_store_data.csv")
        dcs = master_df['fulfilment_dc_standard'].unique().tolist()
        return [dc for dc in dcs if pd.notna(dc)]


if __name__ == "__main__":
    loader = TMSDataLoader()

    print("\n📋 Available DCs:")
    dcs = loader.get_available_dcs()
    for i, dc in enumerate(dcs, 1):
        print(f"   {i}. {dc}")

    print("\n💡 To load data, use:")
    print("   loader.load_all_data(target_dc='DC_KLANG')")
