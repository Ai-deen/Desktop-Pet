from abc import ABC, abstractmethod

class TaskComponent(ABC):

    @abstractmethod
    def complete(self):
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        pass
