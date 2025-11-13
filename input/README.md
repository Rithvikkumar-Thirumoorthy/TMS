# Expected Data Format for Input Files

Place your data files in the `input/` directory.

## Required Files

### 1. stores.csv

**Required columns:**
- `id` - Unique store identifier (e.g., S001, STORE_A)
- `name` - Store name
- `latitude` - Latitude coordinate
- `longitude` - Longitude coordinate
- `demand_cbm` - Demand in cubic meters (CBM)

**Optional columns:**
- `time_window_start` - Start time (e.g., 09:00)
- `time_window_end` - End time (e.g., 17:00)
- `excluded_days` - Days when store is closed (comma-separated: Mon,Wed)
- `service_time_minutes` - Time needed for unloading (default: 60)
- `priority` - Priority level (default: 1)

**Example:**
```csv
id,name,latitude,longitude,demand_cbm,time_window_start,time_window_end,excluded_days,service_time_minutes
S001,Downtown Store,40.7589,-73.9851,15.5,09:00,17:00,,60
S002,Uptown Store,40.7829,-73.9654,22.3,08:00,16:00,Wed,60
S003,Brooklyn Store,40.6782,-73.9442,8.7,10:00,18:00,,45
```

### 2. vehicles.csv

**Required columns:**
- `id` - Unique vehicle identifier (e.g., V001, TRUCK_A)
- `name` - Vehicle name
- `capacity_cbm` - Capacity in cubic meters

**Optional columns:**
- `max_route_duration_hours` - Maximum hours per route (default: 12.0)
- `start_time` - Departure time from depot (default: 08:00)
- `fixed_cost` - Fixed cost per vehicle (default: 1000.0)
- `cost_per_km` - Cost per kilometer (default: 2.0)
- `vehicle_type` - Type description (default: Standard)

**Example:**
```csv
id,name,capacity_cbm,max_route_duration_hours,start_time,fixed_cost,cost_per_km
V001,Truck A,30.0,12.0,08:00,1000.0,2.5
V002,Truck B,25.0,12.0,08:00,900.0,2.0
V003,Truck C,35.0,12.0,08:00,1200.0,3.0
```

### 3. depot.csv (Optional)

**Columns:**
- `id` - Depot identifier
- `name` - Depot name
- `latitude` - Latitude coordinate
- `longitude` - Longitude coordinate

**Example:**
```csv
id,name,latitude,longitude
depot,Main Depot,40.7580,-73.9855
```

If not provided, a default depot location will be used.

## Alternative: JSON Format

You can also use JSON format. Place these files in `input/`:

**stores.json:**
```json
[
  {
    "id": "S001",
    "name": "Downtown Store",
    "latitude": 40.7589,
    "longitude": -73.9851,
    "demand_cbm": 15.5,
    "time_windows": [
      {
        "earliest": "09:00",
        "latest": "17:00"
      }
    ],
    "excluded_days": [],
    "service_time_minutes": 60
  }
]
```

**vehicles.json:**
```json
[
  {
    "id": "V001",
    "name": "Truck A",
    "capacity_cbm": 30.0,
    "max_route_duration_hours": 12.0,
    "fixed_cost": 1000.0,
    "cost_per_km": 2.5
  }
]
```

## How to Use

1. **Place your files** in the `input/` directory
2. **Run the optimizer:**
   ```bash
   python run_optimization.py
   ```
3. **Results** will be saved in `output/` directory

## Quick Test

To see the expected format and test the loader:
```bash
python load_custom_data.py
```

This will show you the format guide and attempt to load your data.
