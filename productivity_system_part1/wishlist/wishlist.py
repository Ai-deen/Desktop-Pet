from datetime import datetime
from wishlist.item import WishlistItem
from wishlist.record import AllocationRecord
class WishList:
    def __init__(self):
        self.items : list[WishlistItem]  = []
        self.history : list[AllocationRecord] = []

    def add_item(self, new_item: WishlistItem):
        for item in self.items:
            if item.name == new_item.name:
                # update static fields if you want them mutable
                item.price = new_item.price
                item.time = new_item.time
                item.priority = new_item.priority
                return
        self.items.append(new_item)

    def apply_allocation(self,item: WishlistItem,permanent:int,flexible:int):
        item.permanent_points += permanent
        item.flexible_points += flexible

        record = AllocationRecord(
            item_name = item.name,
            permanent = permanent,
            flexible = flexible,
            timestamp=datetime.now()
        )

        self.history.append(record)