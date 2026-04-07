import json
from wishlist.wishlist import WishList
from wishlist.item import WishlistItem
from wishlist.record import AllocationRecord

class WishlistRepository:
    FILE_PATH = "wishlist.json"

    def save(self, wishlist: WishList):
        data = {
            "items": [item.to_dict() for item in wishlist.items],
            "history": [record.to_dict() for record in wishlist.history]
        }

        with open(self.FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> WishList:
        wishlist = WishList()

        try:
            with open(self.FILE_PATH, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return wishlist  # first run, nothing saved yet

        for item_data in data.get("items", []):
            item = WishlistItem(
                item_data["name"],
                item_data["time"],
                item_data["price"],
                item_data["priority"]
            )
            item.permanent_points = item_data["permanent_points"]
            item.flexible_points = item_data["flexible_points"]
            wishlist.add_item(item)

        for record_data in data.get("history", []):
            record = AllocationRecord.from_dict(record_data)
            wishlist.history.append(record)

        return wishlist
