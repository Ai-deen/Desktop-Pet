class XPBar:
    def __init__(self, daily_cap=1000):
        self.daily_cap = daily_cap
        self.current_xp = 0

    def add_xp(self, xp):
        self.current_xp = min(self.daily_cap, self.current_xp + xp)

    def to_points(self):
        return self.current_xp

    def is_full(self):
        return self.current_xp >= self.daily_cap
