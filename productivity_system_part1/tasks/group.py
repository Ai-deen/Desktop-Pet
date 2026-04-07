from tasks.base import TaskComponent

class TaskGroup(TaskComponent):
    def __init__(self,name: str):
        self.name = name
        self.children: list[TaskComponent] = []


    def add(self, task: TaskComponent):
        self.children.append(task)

    def complete(self):
        for task in self.children:
            task.complete()

    def is_complete(self) -> bool:
        return all(task.is_complete() for task in self.children)
     
    def has_incomplete_mandatory(self)->bool:
        for task in self.children:
            if hasattr(task,"mandatory"):
                if task.mandatory and not task.is_complete():
                    return True
            if hasattr(task, "has_incomplete_mandatory"):
                if task.has_incomplete_mandatory():
                    return True
        
        return False
    
                