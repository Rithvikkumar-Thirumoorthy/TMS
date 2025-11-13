"""
Store (Customer) Model
"""
from dataclasses import dataclass, field
from typing import List, Optional
from .time_window import TimeWindow, ForbiddenInterval


@dataclass
class Store:
    """Represents a delivery location (customer/store)"""

    id: str
    name: str
    latitude: float
    longitude: float
    demand_cbm: float  # Demand in cubic meters

    # Time constraints
    time_windows: List[TimeWindow] = field(default_factory=list)
    forbidden_intervals: List[ForbiddenInterval] = field(default_factory=list)

    # Day constraints
    excluded_days: List[str] = field(default_factory=list)  # ['Mon', 'Wed'] means cannot deliver on Monday or Wednesday
    preferred_days: List[str] = field(default_factory=list)  # Preferred delivery days

    # Service time
    service_time_minutes: int = 60  # Default: 60 minutes for unloading

    # Additional metadata
    notes: str = ""
    priority: int = 1  # Higher = more important

    def is_day_allowed(self, day: str) -> bool:
        """Check if delivery is allowed on a specific day"""
        return day not in self.excluded_days

    def get_time_window_for_day(self, day: str) -> Optional[TimeWindow]:
        """Get the time window for a specific day"""
        # First try to find day-specific window
        for tw in self.time_windows:
            if tw.day == day:
                return tw

        # Fall back to general window (no day specified)
        for tw in self.time_windows:
            if tw.day is None:
                return tw

        return None

    def has_forbidden_conflict(self, delivery_time) -> bool:
        """Check if a delivery time conflicts with forbidden intervals"""
        from datetime import time as time_type

        if isinstance(delivery_time, time_type):
            t = delivery_time
        else:
            # Assume it's datetime
            t = delivery_time.time()

        for forbidden in self.forbidden_intervals:
            if forbidden.conflicts_with(t):
                return True
        return False

    def __str__(self):
        return f"Store({self.id}, {self.name}, demand={self.demand_cbm}CBM)"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.id)
