from datetime import datetime
from points.policy import PointPolicy

class TimeBasedPolicy(PointPolicy):
    def to_points(self, xp: int,session) -> int:
        now = session.start_time
        hour = now.hour + now.minute/60
        weekday = now.weekday()

        if weekday >=5:
            multiplier = 1.3

        elif hour < 9:
            multiplier = 1.5

        elif 12.5<= hour <= 21:
            multiplier = 0.7

        else:
            multiplier = 1.0

        return int(xp*multiplier)
