from abc import ABC, abstractmethod

class PointAllocationStrategy(ABC):
    @abstractmethod
    def allocate(self, points, wishlist):
        pass