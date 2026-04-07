from strategies.base import PointAllocationStrategy
import random

class RandomAllocation(PointAllocationStrategy):
    def allocate(self, points, wishlist):
        remaining = points
        items = wishlist.items

        for item in items[:-1]:
            max_allowed = remaining // 2
            allocated = random.randint(0, max_allowed)
            permanent = random.randint(0,allocated)
            flexible = allocated - permanent
            wishlist.apply_allocation(item,permanent,flexible)
            remaining -= allocated

        # last item gets all remaining points
        last_permanent = random.randint(0,remaining)
        last_flexible = remaining - last_permanent
        wishlist.apply_allocation(items[-1],last_permanent,last_flexible)