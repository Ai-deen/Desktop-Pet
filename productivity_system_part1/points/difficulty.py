from points.policy import PointPolicy

class DifficultyPolicy(PointPolicy):
    MULTIPLIERS = {
        "easy": 0.5,
        "medium": 1,
        "hard": 1.5
    }

    def __init__(self, difficulty: str):
        if difficulty not in self.MULTIPLIERS:
            raise ValueError(f"Invalid difficulty: {difficulty}")
        self.difficulty = difficulty

    def to_points(self,xp: int) -> int:
        multiplier = self.MULTIPLIERS[self.difficulty]
        return int(xp*multiplier//100)
    