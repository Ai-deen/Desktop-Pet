class TaskExecution:
    def __init__(self, task, minutes: int):
        self.task = task
        self.minutes = minutes

    def calculate_xp(self) -> int:
        base_xp_per_minute = 2
        difficulty_weight = self.task.get_difficulty_weight()
        xp = self.minutes * base_xp_per_minute * difficulty_weight
        return int(xp)
