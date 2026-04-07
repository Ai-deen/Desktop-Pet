from tasks.base import TaskComponent

class Task(TaskComponent):
    def __init__(self, name: str, mandatory: bool = False, difficulty: str = "medium"):
        self.name = name
        self.mandatory = mandatory
        self._completed = False
        self._difficulty = difficulty

    def complete(self):
        self._completed = True

    def is_complete(self) -> bool:
        return self._completed

    def get_difficulty_weight(self) -> float:
        weights = {
            "easy": 0.8,
            "medium": 1.0,
            "hard": 1.3
        }

        if self._difficulty not in weights:
            raise ValueError(f"Invalid difficulty: {self._difficulty}")

        return weights[self._difficulty]
