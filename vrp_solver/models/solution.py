"""
Solution Model - Represents complete VRP solution
"""
from dataclasses import dataclass, field
from typing import List, Dict
from .route import Route


@dataclass
class Solution:
    """Represents a complete solution for VRP"""

    routes: List[Route] = field(default_factory=list)
    day: str = ""  # Day this solution is for (or "Multi-Day")
    unserved_stores: List[str] = field(default_factory=list)

    # Solution metrics
    total_distance_km: float = 0.0
    total_duration_hours: float = 0.0
    total_cost: float = 0.0
    num_vehicles_used: int = 0

    # Constraint satisfaction
    is_feasible: bool = True
    constraint_violations: List[str] = field(default_factory=list)

    def compute_metrics(self):
        """Compute all solution metrics"""
        self.num_vehicles_used = len(self.routes)
        self.total_distance_km = sum(r.total_distance_km for r in self.routes)
        self.total_duration_hours = sum(r.total_duration_minutes for r in self.routes) / 60
        self.total_cost = sum(r.calculate_cost() for r in self.routes)

    def get_average_utilization(self) -> float:
        """Get average capacity utilization across all routes"""
        if not self.routes:
            return 0.0
        return sum(r.get_load_utilization() for r in self.routes) / len(self.routes)

    def get_total_stores_served(self) -> int:
        """Get total number of stores served"""
        return sum(len(r.stops) for r in self.routes)

    def get_utilization_stats(self) -> Dict[str, float]:
        """Get detailed utilization statistics"""
        if not self.routes:
            return {"min": 0, "max": 0, "avg": 0, "std": 0}

        utils = [r.get_load_utilization() for r in self.routes]
        import numpy as np

        return {
            "min": min(utils),
            "max": max(utils),
            "avg": np.mean(utils),
            "std": np.std(utils),
        }

    def to_dict(self) -> dict:
        """Convert solution to dictionary for export"""
        return {
            "day": self.day,
            "is_feasible": self.is_feasible,
            "num_vehicles_used": self.num_vehicles_used,
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_hours": round(self.total_duration_hours, 2),
            "total_cost": round(self.total_cost, 2),
            "average_utilization": round(self.get_average_utilization(), 2),
            "stores_served": self.get_total_stores_served(),
            "unserved_stores": self.unserved_stores,
            "constraint_violations": self.constraint_violations,
            "routes": [
                {
                    "vehicle_id": route.vehicle.id,
                    "vehicle_name": route.vehicle.name,
                    "stops": [stop.store.id for stop in route.stops],
                    "distance_km": round(route.total_distance_km, 2),
                    "duration_minutes": round(route.total_duration_minutes, 2),
                    "load_cbm": round(route.total_load_cbm, 2),
                    "capacity_cbm": route.vehicle.capacity_cbm,
                    "utilization": round(route.get_load_utilization(), 2),
                }
                for route in self.routes
            ],
        }

    def __str__(self):
        return f"Solution({self.day}, {self.num_vehicles_used} vehicles, {self.get_total_stores_served()} stores, {self.total_distance_km:.1f}km)"


@dataclass
class MultiDaySolution:
    """Represents a multi-day solution"""

    daily_solutions: Dict[str, Solution] = field(default_factory=dict)
    consolidation_stats: Dict = field(default_factory=dict)

    def add_day_solution(self, day: str, solution: Solution):
        """Add a single day solution"""
        self.daily_solutions[day] = solution

    def compute_weekly_metrics(self) -> dict:
        """Compute aggregated weekly metrics"""
        total_distance = sum(sol.total_distance_km for sol in self.daily_solutions.values())
        total_vehicles = sum(sol.num_vehicles_used for sol in self.daily_solutions.values())
        total_cost = sum(sol.total_cost for sol in self.daily_solutions.values())
        total_stores = sum(sol.get_total_stores_served() for sol in self.daily_solutions.values())

        return {
            "total_distance_km": round(total_distance, 2),
            "total_vehicles_used": total_vehicles,
            "total_cost": round(total_cost, 2),
            "total_stores_served": total_stores,
            "daily_breakdown": {day: sol.to_dict() for day, sol in self.daily_solutions.items()},
            "consolidation_stats": self.consolidation_stats,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.compute_weekly_metrics()
