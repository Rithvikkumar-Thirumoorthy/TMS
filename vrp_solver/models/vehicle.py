"""
Vehicle (Fleet) Model
"""
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class Vehicle:
    """Represents a delivery vehicle"""

    id: str
    name: str
    capacity_cbm: float  # Capacity in cubic meters

    # Fleet restrictions
    allowed_store_ids: Set[str] = field(default_factory=set)  # If empty, can serve all stores
    forbidden_store_ids: Set[str] = field(default_factory=set)

    # Operating constraints
    max_route_duration_hours: float = 12.0
    start_time: str = "08:00"  # Default start time

    # Cost factors
    fixed_cost: float = 1000.0  # Cost per vehicle used
    cost_per_km: float = 2.0

    # Additional metadata
    vehicle_type: str = "Standard"
    driver_name: str = ""

    def can_serve_store(self, store_id: str) -> bool:
        """Check if this vehicle can serve a specific store"""
        # If in forbidden list, cannot serve
        if store_id in self.forbidden_store_ids:
            return False

        # If allowed list is specified, must be in it
        if self.allowed_store_ids:
            return store_id in self.allowed_store_ids

        # Otherwise, can serve
        return True

    def can_fit_demand(self, demand_cbm: float, current_load: float = 0.0) -> bool:
        """Check if vehicle can fit additional demand"""
        return (current_load + demand_cbm) <= self.capacity_cbm

    def get_remaining_capacity(self, current_load: float) -> float:
        """Get remaining capacity"""
        return max(0, self.capacity_cbm - current_load)

    def __str__(self):
        return f"Vehicle({self.id}, {self.name}, capacity={self.capacity_cbm}CBM)"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.id)
