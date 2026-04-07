class WishlistItem:
    def __init__(self, name: str, time:int, price: int, priority: str):
        self.name = name
        self.price = price
        self.time = time
        self.permanent_points= 0
        self.flexible_points= 0
        self.priority = priority

    @property
    def allocated_points(self):
        return self.permanent_points + self.flexible_points

    def to_dict(self):
        return {
            "name": self.name,
            "price": self.price,
            "time": self.time,
            "priority":self.priority,
            "permanent_points": self.permanent_points,
            "flexible_points": self.flexible_points
        }
