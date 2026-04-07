from wishlist.item import WishlistItem
from wishlist.wishlist import WishList
from strategies.random import RandomAllocation
from strategies.engine import AllocationEngine
from points.time import TimeBasedPolicy
from core.session import Session
from tasks.task import Task
from tasks.execution import TaskExecution
from wishlist.repository import WishlistRepository

if __name__ == "__main__":
    # wishlist
    repo = WishlistRepository()
    wishlist = repo.load()
    wishlist.add_item(WishlistItem("Headphones", 100, 5000,"high"))
    wishlist.add_item(WishlistItem("Keyboard", 70, 3000,"low"))
        # tasks
    dsa = Task("DSA", mandatory=True, difficulty="hard")
    lld = Task("LLD", mandatory=False, difficulty="medium")

    # executions (what you did TODAY)
    exec1 = TaskExecution(dsa, 60)
    exec2 = TaskExecution(lld, 30)

    # system session
    engine = AllocationEngine(RandomAllocation())
    policy = TimeBasedPolicy()
    session = Session(engine, policy)

    # log work
    session.log_execution(exec1)
    session.log_execution(exec2)

    # allocate points
    session.allocate(wishlist)
    repo.save(wishlist)


    # output
    for item in wishlist.items:
        print(
            f"{item.name} -> "
            f"Permanent: {item.permanent_points}, "
            f"Flexible: {item.flexible_points}, "
            f"Total: {item.allocated_points}"
        )
