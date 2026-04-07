from xp.xp_bar import XPBar
from strategies.engine import AllocationEngine
from points.policy import PointPolicy
from tasks.execution import TaskExecution
from tasks.task import Task
from datetime import datetime

class Session:
    def __init__(self, allocation_engine: AllocationEngine, point_policy: PointPolicy):
        self.xp_bar = XPBar()
        self.allocation_engine = allocation_engine
        self.point_policy = point_policy
        self.executed_tasks = set()
        self.minimum_xp = 30
        self.start_time = datetime.now()


    def log_execution(self, execution: TaskExecution):
        xp = execution.calculate_xp()
        self.xp_bar.add_xp(xp)
        self.executed_tasks.add(id(execution.task))


    def allocate(self, wishlist: list):
        if self.xp_bar.current_xp < self.minimum_xp:
            raise ValueError("Daily minimum XP not reached")

        points = self.point_policy.to_points(self.xp_bar.current_xp, self)
        self.allocation_engine.run(points, wishlist)

    def validate_mandatory_tasks(self, tasks: list):
        for task in tasks:
            if task.mandatory and id(task) not in self.executed_tasks:
                raise ValueError(f"Mandatory task {task} is not executed")


