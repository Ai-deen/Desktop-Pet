from datetime import datetime
class AllocationRecord:
    def __init__(self,item_name: str,permanent: int, flexible:int,timestamp:datetime):
        self.item_name = item_name
        self.permanent = permanent
        self.flexible = flexible
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "item_name": self.item_name,
            "permanent": self.permanent,
            "flexible": self.flexible,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            item_name=data["item_name"],
            permanent=data["permanent"],
            flexible=data["flexible"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )