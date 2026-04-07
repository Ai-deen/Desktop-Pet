from strategies.base import PointAllocationStrategy

class FlexibleAllocation(PointAllocationStrategy):
    def allocate(self, points, wishlist):
        per_item = points // len(wishlist)
        for item in wishlist:
            item.flexible_points += per_item