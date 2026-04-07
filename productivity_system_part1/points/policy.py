from abc import ABC, abstractmethod

class PointPolicy(ABC):
    @abstractmethod
    def to_points(self,xp: int,session) -> int:
        pass