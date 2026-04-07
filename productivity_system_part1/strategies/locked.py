from strategies.base import PointAllocationStrategy

class LockedAllocation(PointAllocationStrategy):
    def allocate(self, points, wishlist):
        per_item = points // len(wishlist)
        for item in wishlist:
            item.permanent_points += per_item