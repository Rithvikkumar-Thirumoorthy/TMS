"""
Route Model
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, time, timedelta
from .store import Store
from .vehicle import Vehicle


@dataclass
class RouteStop:
    """Represents a stop in a route"""

    store: Store
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    load_before: float = 0.0  # Load before this delivery
    load_after: float = 0.0   # Load after this delivery
    sequence: int = 0

    def __str__(self):
        time_str = f" @ {self.arrival_time.strftime('%H:%M')}" if self.arrival_time else ""
        return f"{self.store.id}{time_str}"


@dataclass
class Route:
    """Represents a complete vehicle route"""

    vehicle: Vehicle
    stops: List[RouteStop] = field(default_factory=list)
    day: Optional[str] = None  # Day of week (Mon, Tue, etc.)

    # Computed metrics
    total_distance_km: float = 0.0
    total_duration_minutes: float = 0.0
    total_load_cbm: float = 0.0

    # Depot information
    depot_departure: Optional[datetime] = None
    depot_return: Optional[datetime] = None

    def add_stop(self, store: Store, position: Optional[int] = None):
        """Add a store to the route"""
        stop = RouteStop(store=store, sequence=len(self.stops))

        if position is None:
            self.stops.append(stop)
        else:
            self.stops.insert(position, stop)
            # Resequence
            for i, s in enumerate(self.stops):
                s.sequence = i

        self.total_load_cbm += store.demand_cbm

    def remove_stop(self, store_id: str) -> bool:
        """Remove a store from the route"""
        for i, stop in enumerate(self.stops):
            if stop.store.id == store_id:
                self.total_load_cbm -= stop.store.demand_cbm
                self.stops.pop(i)
                # Resequence
                for j, s in enumerate(self.stops):
                    s.sequence = j
                return True
        return False

    def get_load_utilization(self) -> float:
        """Get capacity utilization percentage"""
        if self.vehicle.capacity_cbm == 0:
            return 0.0
        return (self.total_load_cbm / self.vehicle.capacity_cbm) * 100

    def is_valid_capacity(self) -> bool:
        """Check if route respects vehicle capacity"""
        return self.total_load_cbm <= self.vehicle.capacity_cbm

    def is_valid_duration(self) -> bool:
        """Check if route respects maximum duration"""
        max_duration = self.vehicle.max_route_duration_hours * 60  # Convert to minutes
        return self.total_duration_minutes <= max_duration

    def get_store_ids(self) -> List[str]:
        """Get list of store IDs in this route"""
        return [stop.store.id for stop in self.stops]

    def calculate_cost(self) -> float:
        """Calculate total route cost"""
        # Fixed cost for using vehicle
        cost = self.vehicle.fixed_cost

        # Distance-based cost
        cost += self.total_distance_km * self.vehicle.cost_per_km

        return cost

    def __len__(self):
        return len(self.stops)

    def __str__(self):
        stops_str = " -> ".join([stop.store.id for stop in self.stops])
        return f"Route({self.vehicle.id}: Depot -> {stops_str} -> Depot, {self.total_load_cbm:.1f}/{self.vehicle.capacity_cbm}CBM, {self.total_distance_km:.1f}km)"

    def __repr__(self):
        return self.__str__()
