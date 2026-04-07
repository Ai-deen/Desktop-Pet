class AllocationEngine:
    def __init__(self, strategy):
        self.strategy = strategy

    def run(self, points, wishlist):
        self.strategy.allocate(points, wishlist)