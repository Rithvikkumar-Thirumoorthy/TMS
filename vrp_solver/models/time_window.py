"""
Time Window and Forbidden Interval Models
"""
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class TimeWindow:
    """Represents an allowed delivery time window"""

    earliest: time  # Earliest delivery time
    latest: time    # Latest delivery time
    day: Optional[str] = None  # Day of week (Mon-Fri) or None for all days

    def __post_init__(self):
        if isinstance(self.earliest, str):
            self.earliest = datetime.strptime(self.earliest, "%H:%M").time()
        if isinstance(self.latest, str):
            self.latest = datetime.strptime(self.latest, "%H:%M").time()

    def contains(self, t: time) -> bool:
        """Check if a given time falls within this window"""
        return self.earliest <= t <= self.latest

    def duration_minutes(self) -> int:
        """Calculate window duration in minutes"""
        earliest_mins = self.earliest.hour * 60 + self.earliest.minute
        latest_mins = self.latest.hour * 60 + self.latest.minute
        return latest_mins - earliest_mins

    def __str__(self):
        day_str = f"{self.day} " if self.day else ""
        return f"{day_str}{self.earliest.strftime('%H:%M')}-{self.latest.strftime('%H:%M')}"


@dataclass
class ForbiddenInterval:
    """Represents a blackout period where deliveries are not allowed"""

    start: time
    end: time
    reason: str = "Blackout period"

    def __post_init__(self):
        if isinstance(self.start, str):
            self.start = datetime.strptime(self.start, "%H:%M").time()
        if isinstance(self.end, str):
            self.end = datetime.strptime(self.end, "%H:%M").time()

    def conflicts_with(self, t: time) -> bool:
        """Check if a given time falls within this forbidden interval"""
        return self.start <= t <= self.end

    def overlaps_with_window(self, window: TimeWindow) -> bool:
        """Check if this forbidden interval overlaps with a time window"""
        # Check if forbidden interval overlaps with time window
        return not (self.end < window.earliest or self.start > window.latest)

    def __str__(self):
        return f"Forbidden: {self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')} ({self.reason})"
