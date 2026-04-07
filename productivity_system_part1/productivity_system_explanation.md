# Productivity System - Complete Explanation

## System Overview

This is a **gamified productivity system** that converts real work into XP (experience points), then into redeemable points for wishlist items. It uses **Low-Level Design (LLD)** principles to create a flexible, maintainable architecture.

---

## 🎯 Core Concept: The Flow

```
TASK EXECUTION → XP GENERATION → POINT CONVERSION → ALLOCATION TO WISHLIST
```

Here's what happens when you work:

1. **You complete tasks** (like studying DSA for 60 minutes)
2. **Tasks generate XP** based on time spent and difficulty
3. **XP is capped daily** to prevent abuse
4. **XP converts to points** using policies (time-based multipliers)
5. **Points are allocated** to wishlist items (things you want to buy)
6. **Points accumulate** until you can redeem items

---

## 📦 Module Architecture

The system is divided into **6 main modules**:

### 1. **tasks/** - What You Do
### 2. **xp/** - Experience Tracking
### 3. **points/** - Conversion Policies
### 4. **strategies/** - Point Allocation Logic
### 5. **wishlist/** - Rewards System
### 6. **core/** - Orchestration (Session & Main)

Let's examine each in detail:

---

## 1. TASKS MODULE (`tasks/`)

### Purpose
Define what work you can do and track its execution.

### Components

#### **TaskComponent (base.py)** - Abstract Base Class
```python
class TaskComponent(ABC):
    @abstractmethod
    def complete(self)
    
    @abstractmethod
    def is_complete(self) -> bool
```

**Role:** Defines the interface for anything that can be completed.

**Design Pattern:** **Component Pattern** (allows both single tasks and groups)

---

#### **Task (task.py)** - Individual Task
```python
class Task(TaskComponent):
    - name: str
    - mandatory: bool
    - difficulty: str (easy/medium/hard)
    - _completed: bool
```

**Key Features:**
- **Difficulty weights:** easy=0.8x, medium=1.0x, hard=1.3x
- **Mandatory flag:** Some tasks must be done before earning points
- **Completion tracking:** Tracks whether task is done

**Example:**
```python
dsa = Task("DSA", mandatory=True, difficulty="hard")
```

---

#### **TaskGroup (group.py)** - Composite of Tasks
```python
class TaskGroup(TaskComponent):
    - name: str
    - children: list[TaskComponent]
```

**Key Features:**
- **Composite Pattern:** Can contain tasks OR other task groups
- **Recursive completion:** Completes all children
- **Mandatory validation:** Checks if any child has incomplete mandatory tasks

**Use Case:** Group related tasks together (e.g., "Morning Routine" contains multiple subtasks)

---

#### **TaskExecution (execution.py)** - Actual Work Done
```python
class TaskExecution:
    - task: Task
    - minutes: int
```

**Purpose:** Records that you actually DID a task for a certain duration.

**XP Calculation:**
```python
def calculate_xp(self) -> int:
    base_xp_per_minute = 2
    difficulty_weight = self.task.get_difficulty_weight()
    xp = minutes * base_xp_per_minute * difficulty_weight
    return int(xp)
```

**Example:**
- Task: DSA (hard difficulty, weight=1.3)
- Time: 60 minutes
- XP = 60 × 2 × 1.3 = **156 XP**

**Why separate Task from TaskExecution?**
- Task = Definition (what it is)
- TaskExecution = Instance (when you did it)
- Same task can be executed multiple times

---

## 2. XP MODULE (`xp/`)

### Purpose
Track experience points with daily limits.

#### **XPBar (xp_bar.py)**
```python
class XPBar:
    - daily_cap: int (default 1000)
    - current_xp: int
```

**Key Features:**
- **Daily Cap Enforcement:** Prevents earning unlimited XP in one day
- **Automatic Capping:** `add_xp()` never exceeds the cap

**Methods:**
```python
add_xp(xp)  # Adds XP, respects cap
to_points() # Returns current XP as points
is_full()   # Checks if cap reached
```

**Example:**
```python
xp_bar = XPBar(daily_cap=1000)
xp_bar.add_xp(600)  # current_xp = 600
xp_bar.add_xp(600)  # current_xp = 1000 (capped!)
```

**Design Principle:** **Single Responsibility** - Only manages XP limits, doesn't know about tasks or rewards.

---

## 3. POINTS MODULE (`points/`)

### Purpose
Convert XP into redeemable points using different policies.

#### **PointPolicy (policy.py)** - Abstract Strategy
```python
class PointPolicy(ABC):
    @abstractmethod
    def to_points(self, xp: int, session) -> int
```

**Design Pattern:** **Strategy Pattern** - Different policies are interchangeable.

---

#### **TimeBasedPolicy (time.py)** - Time Multiplier
```python
class TimeBasedPolicy(PointPolicy):
    def to_points(self, xp: int, session) -> int
```

**Rules:**
- **Weekend work:** 1.3x multiplier (encourages weekend productivity)
- **Early morning (before 9am):** 1.5x multiplier (reward early risers)
- **Afternoon/Evening (12:30pm-9pm):** 0.7x multiplier (discourage procrastination)
- **Default:** 1.0x multiplier

**Example:**
- You earn 200 XP
- You worked on Saturday (weekend)
- Points = 200 × 1.3 = **260 points**

---

#### **DifficultyPolicy (difficulty.py)** - Difficulty Multiplier
```python
class DifficultyPolicy(PointPolicy):
    MULTIPLIERS = {
        "easy": 0.5,
        "medium": 1,
        "hard": 1.5
    }
```

**Purpose:** Reward harder sessions more than easier ones.

**Note:** Currently not used in main.py, but available as alternative policy.

---

## 4. STRATEGIES MODULE (`strategies/`)

### Purpose
Decide HOW to distribute points across wishlist items.

#### **PointAllocationStrategy (base.py)** - Abstract Strategy
```python
class PointAllocationStrategy(ABC):
    @abstractmethod
    def allocate(self, points, wishlist)
```

---

#### **AllocationEngine (engine.py)** - Strategy Executor
```python
class AllocationEngine:
    def __init__(self, strategy):
        self.strategy = strategy
    
    def run(self, points, wishlist):
        self.strategy.allocate(points, wishlist)
```

**Design Pattern:** **Strategy Pattern** + **Dependency Injection**

**Why this design?**
- Engine doesn't care WHICH strategy is used
- Strategies can be swapped at runtime
- Easy to add new allocation strategies

---

#### **Concrete Strategies:**

##### **1. RandomAllocation (random.py)**
```python
class RandomAllocation(PointAllocationStrategy)
```

**Logic:**
- Randomly distributes points across items
- Each item gets random split between permanent and flexible points
- Last item gets all remaining points

**Example:**
- 216 points total
- Item 1: Gets random amount (e.g., 40 points)
- Item 2: Gets all remaining (176 points)

---

##### **2. LockedAllocation (locked.py)**
```python
class LockedAllocation(PointAllocationStrategy)
```

**Logic:**
- Divides points equally across ALL items
- ALL points go to **permanent_points**
- No flexible points allocated

**Use Case:** When you're committed to saving for all items equally.

---

##### **3. FlexibleAllocation (flexible.py)**
```python
class FlexibleAllocation(PointAllocationStrategy)
```

**Logic:**
- Divides points equally across ALL items
- ALL points go to **flexible_points**
- No permanent points allocated

**Use Case:** When you want freedom to move points later.

---

## 5. WISHLIST MODULE (`wishlist/`)

### Purpose
Manage rewards and track point accumulation.

#### **WishlistItem (item.py)**
```python
class WishlistItem:
    - name: str
    - price: int (actual cost in currency)
    - time: int (estimated time to earn)
    - priority: str (high/medium/low)
    - permanent_points: int
    - flexible_points: int
```

**Two Types of Points:**

1. **Permanent Points:** 
   - Cannot be moved to other items
   - Locked to this item forever
   - Safer for high-priority items

2. **Flexible Points:**
   - Can potentially be reallocated
   - More adaptable
   - Useful when priorities change

**Total Points:**
```python
@property
def allocated_points(self):
    return self.permanent_points + self.flexible_points
```

**Example:**
```python
item = WishlistItem("Headphones", time=100, price=5000, priority="high")
# After allocations:
# permanent_points = 164
# flexible_points = 130
# Total = 294 points
```

---

#### **WishList (wishlist.py)**
```python
class WishList:
    - items: list[WishlistItem]
    - history: list[AllocationRecord]
```

**Key Methods:**

##### `add_item(new_item)`
- If item exists (same name): **Updates** it
- If item is new: **Adds** it
- Prevents duplicates while allowing updates

##### `apply_allocation(item, permanent, flexible)`
- Adds points to an item
- Creates an **AllocationRecord** for history tracking
- Records timestamp for each allocation

**Why track history?**
- See how points accumulated over time
- Analyze earning patterns
- Undo/audit trail if needed

---

#### **AllocationRecord (record.py)**
```python
class AllocationRecord:
    - item_name: str
    - permanent: int
    - flexible: int
    - timestamp: datetime
```

**Purpose:** Historical record of each point allocation.

**Features:**
- Serialization: `to_dict()` for JSON storage
- Deserialization: `from_dict()` for loading
- Timestamp tracking: Know when points were earned

---

#### **WishlistRepository (repository.py)**
```python
class WishlistRepository:
    FILE_PATH = "wishlist.json"
```

**Purpose:** Persist wishlist data to disk.

**Methods:**

##### `save(wishlist)`
- Converts all items and history to JSON
- Saves to `wishlist.json`
- Pretty-printed with indent=2

##### `load() -> WishList`
- Reads from `wishlist.json`
- Reconstructs WishList with all items and history
- Handles first run (file not found)

**Data Persistence Example:**
```json
{
  "items": [
    {
      "name": "Headphones",
      "price": 5000,
      "permanent_points": 164,
      "flexible_points": 130
    }
  ],
  "history": [
    {
      "item_name": "Headphones",
      "permanent": 67,
      "flexible": 35,
      "timestamp": "2026-01-09T11:26:10.236069"
    }
  ]
}
```

---

## 6. CORE MODULE (`core/`)

### Purpose
Orchestrate the entire system.

#### **Session (session.py)** - The Orchestrator
```python
class Session:
    - xp_bar: XPBar
    - allocation_engine: AllocationEngine
    - point_policy: PointPolicy
    - executed_tasks: set
    - minimum_xp: int (30)
    - start_time: datetime
```

**Design Pattern:** **Orchestrator Pattern** (coordinates multiple subsystems)

**Dependencies Injected:**
- AllocationEngine (with its strategy)
- PointPolicy

**Key Methods:**

##### `log_execution(execution: TaskExecution)`
```python
def log_execution(self, execution):
    xp = execution.calculate_xp()  # Get XP from execution
    self.xp_bar.add_xp(xp)         # Add to XP bar (respects cap)
    self.executed_tasks.add(id(execution.task))  # Track completion
```

**What happens:**
1. Calculate XP from the task execution
2. Add XP to the XP bar (will be capped if needed)
3. Remember that this task was executed

---

##### `allocate(wishlist)`
```python
def allocate(self, wishlist):
    # 1. Check minimum XP requirement
    if self.xp_bar.current_xp < self.minimum_xp:
        raise ValueError("Daily minimum XP not reached")
    
    # 2. Convert XP to points using policy
    points = self.point_policy.to_points(self.xp_bar.current_xp, self)
    
    # 3. Allocate points using strategy
    self.allocation_engine.run(points, wishlist)
```

**What happens:**
1. **Validation:** Must earn at least 30 XP
2. **Conversion:** XP → Points (with time multiplier)
3. **Distribution:** Points → Wishlist items (using allocation strategy)

---

##### `validate_mandatory_tasks(tasks)`
```python
def validate_mandatory_tasks(self, tasks):
    for task in tasks:
        if task.mandatory and id(task) not in self.executed_tasks:
            raise ValueError(f"Mandatory task {task} is not executed")
```

**Purpose:** Ensure all mandatory tasks are completed before allowing point allocation.

---

#### **main.py** - The Entry Point

Here's the complete flow:

```python
if __name__ == "__main__":
    # 1. LOAD WISHLIST
    repo = WishlistRepository()
    wishlist = repo.load()
    
    # 2. ADD/UPDATE WISHLIST ITEMS
    wishlist.add_item(WishlistItem("Headphones", 100, 5000, "high"))
    wishlist.add_item(WishlistItem("Keyboard", 70, 3000, "low"))
    
    # 3. DEFINE TASKS
    dsa = Task("DSA", mandatory=True, difficulty="hard")
    lld = Task("LLD", mandatory=False, difficulty="medium")
    
    # 4. CREATE TASK EXECUTIONS (what you did today)
    exec1 = TaskExecution(dsa, 60)  # 60 minutes on DSA
    exec2 = TaskExecution(lld, 30)  # 30 minutes on LLD
    
    # 5. CREATE SESSION
    engine = AllocationEngine(RandomAllocation())
    policy = TimeBasedPolicy()
    session = Session(engine, policy)
    
    # 6. LOG WORK
    session.log_execution(exec1)  # Earns XP
    session.log_execution(exec2)  # Earns XP
    
    # 7. ALLOCATE POINTS
    session.allocate(wishlist)  # Distributes points
    
    # 8. SAVE WISHLIST
    repo.save(wishlist)
    
    # 9. OUTPUT RESULTS
    for item in wishlist.items:
        print(f"{item.name} -> Permanent: {item.permanent_points}, "
              f"Flexible: {item.flexible_points}, Total: {item.allocated_points}")
```

---

## 🔄 Complete Data Flow Example

Let's trace a complete execution:

### Input:
```python
# Tasks
dsa = Task("DSA", mandatory=True, difficulty="hard")
lld = Task("LLD", mandatory=False, difficulty="medium")

# Executions
exec1 = TaskExecution(dsa, 60)  # 60 min
exec2 = TaskExecution(lld, 30)  # 30 min

# It's Saturday at 3pm
```

### Step-by-Step:

#### Step 1: Calculate XP

**exec1 (DSA):**
- Minutes: 60
- Difficulty weight: 1.3 (hard)
- XP = 60 × 2 × 1.3 = **156 XP**

**exec2 (LLD):**
- Minutes: 30
- Difficulty weight: 1.0 (medium)
- XP = 30 × 2 × 1.0 = **60 XP**

**Total XP: 156 + 60 = 216 XP**

#### Step 2: Add to XP Bar
```python
xp_bar.add_xp(156)  # current_xp = 156
xp_bar.add_xp(60)   # current_xp = 216
```
(Cap is 1000, so no limiting occurs)

#### Step 3: Check Minimum XP
```python
if 216 >= 30:  # ✓ Pass
```

#### Step 4: Convert XP to Points
```python
# TimeBasedPolicy checks:
# - Is it weekend? YES (Saturday) → multiplier = 1.3

points = 216 × 1.3 = 280.8 ≈ 280 points
```

#### Step 5: Allocate Points (RandomAllocation)
```python
# Wishlist items:
# - Headphones
# - Keyboard

# RandomAllocation distributes:
# Item 1 (Headphones): random split, e.g., 102 points (67 perm, 35 flex)
# Item 2 (Keyboard): remaining 178 points (111 perm, 67 flex)
```

#### Step 6: Update Items
```python
# Before:
Headphones: permanent=164, flexible=130

# After:
Headphones: permanent=231, flexible=165
```

#### Step 7: Create History Record
```python
AllocationRecord(
    item_name="Headphones",
    permanent=67,
    flexible=35,
    timestamp="2026-02-01T15:30:00"
)
```

#### Step 8: Save to JSON
```python
repo.save(wishlist)  # Persists to wishlist.json
```

---

## 🔗 How Components Connect

### Dependency Graph:

```
main.py
  ├─→ Session (orchestrates everything)
  │     ├─→ XPBar (tracks XP)
  │     ├─→ AllocationEngine
  │     │     └─→ PointAllocationStrategy (Random/Locked/Flexible)
  │     └─→ PointPolicy (Time/Difficulty)
  │
  ├─→ Task (what to do)
  ├─→ TaskExecution (what was done)
  │     └─→ Task (references)
  │
  └─→ WishList
        ├─→ WishlistItem (rewards)
        └─→ AllocationRecord (history)
```

### Communication Flow:

```
TaskExecution.calculate_xp()
          ↓
Session.log_execution() → XPBar.add_xp()
          ↓
Session.allocate()
          ↓
PointPolicy.to_points() [XP → Points conversion]
          ↓
AllocationEngine.run()
          ↓
PointAllocationStrategy.allocate() [distribute to items]
          ↓
WishList.apply_allocation() [update items + record history]
          ↓
WishlistRepository.save() [persist to JSON]
```

---

## 🎨 Design Patterns Used

### 1. **Strategy Pattern**
- **Where:** PointPolicy, PointAllocationStrategy
- **Why:** Different policies/strategies can be swapped without changing code
- **Benefit:** Easy to add new rules (e.g., streak bonuses)

### 2. **Dependency Injection**
- **Where:** Session constructor
- **Why:** Dependencies provided externally, not created internally
- **Benefit:** Loose coupling, easy testing, configurable behavior

### 3. **Single Responsibility Principle (SRP)**
- **XPBar:** Only manages XP limits
- **WishList:** Only manages rewards
- **Session:** Only orchestrates flow
- **Benefit:** Changes in one area don't affect others

### 4. **Composite Pattern**
- **Where:** TaskComponent → Task / TaskGroup
- **Why:** Treat single tasks and groups uniformly
- **Benefit:** Can create hierarchical task structures

### 5. **Repository Pattern**
- **Where:** WishlistRepository
- **Why:** Abstracts data persistence
- **Benefit:** Can change storage (JSON → DB) without affecting other code

### 6. **Orchestrator Pattern**
- **Where:** Session
- **Why:** Coordinates multiple subsystems
- **Benefit:** Centralized flow control

### 7. **Open/Closed Principle**
- **Where:** Adding new policies/strategies
- **Why:** Open for extension, closed for modification
- **Benefit:** Add features without breaking existing code

---

## 💡 Key Design Decisions

### Why Two Types of Points (Permanent vs Flexible)?

**Permanent Points:**
- Represent commitment to an item
- Cannot be reallocated
- Good for high-priority goals

**Flexible Points:**
- Represent tentative allocation
- Can potentially be moved later
- Good for exploratory priorities

**Real-world analogy:**
- Permanent = Money in a savings account for a specific goal
- Flexible = Money you've earmarked but can reallocate

---

### Why Separate XP from Points?

**XP (Experience Points):**
- Represents RAW work effort
- Has a daily cap (prevents gaming the system)
- Consistent across all sessions

**Points (Redeemable Currency):**
- Represents VALUED work effort
- Multiplied by context (time of day, difficulty)
- Used for actual rewards

**Benefit:** You can change how XP converts to points without changing XP tracking.

---

### Why Track Task Execution Separately?

**Task** = Definition (the concept of "DSA practice")
**TaskExecution** = Instance (you did DSA for 60 min today)

**Benefits:**
- Same task can be executed multiple times
- Track history of executions
- Calculate XP per execution

---

### Why Use Abstract Base Classes?

**PointPolicy, PointAllocationStrategy, TaskComponent:**

All are abstract base classes (ABC) with `@abstractmethod`.

**Benefits:**
- **Interface Contracts:** Enforces that subclasses implement required methods
- **Type Safety:** IDE can catch missing methods
- **Clear Intent:** Signals this is meant to be extended
- **Polymorphism:** Different implementations can be used interchangeably

---

## 🚀 How to Extend the System

### Add a New Point Policy

```python
# points/streak.py
from points.policy import PointPolicy

class StreakPolicy(PointPolicy):
    def __init__(self, streak_days: int):
        self.streak_days = streak_days
    
    def to_points(self, xp: int, session) -> int:
        # 10% bonus per consecutive day
        multiplier = 1.0 + (self.streak_days * 0.1)
        return int(xp * multiplier)
```

**Usage:**
```python
policy = StreakPolicy(streak_days=5)
session = Session(engine, policy)
```

---

### Add a New Allocation Strategy

```python
# strategies/priority.py
from strategies.base import PointAllocationStrategy

class PriorityAllocation(PointAllocationStrategy):
    def allocate(self, points, wishlist):
        # Sort items by priority
        sorted_items = sorted(
            wishlist.items,
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x.priority],
            reverse=True
        )
        
        # Give all points to highest priority item
        top_item = sorted_items[0]
        wishlist.apply_allocation(top_item, points, 0)
```

**Usage:**
```python
engine = AllocationEngine(PriorityAllocation())
```

---

### Add Task Groups (Already Supported!)

```python
# Create a group
morning_routine = TaskGroup("Morning Routine")
morning_routine.add(Task("Exercise", mandatory=True, difficulty="medium"))
morning_routine.add(Task("Meditation", mandatory=False, difficulty="easy"))

# Execute all tasks in group
morning_routine.complete()

# Check if all done
if morning_routine.is_complete():
    print("Morning routine completed!")
```

---

## 📊 Example Real Session

```python
# Monday morning at 7am
# Tasks: 90 min coding (hard), 30 min reading (easy)

coding = Task("Coding", mandatory=True, difficulty="hard")
reading = Task("Reading", mandatory=False, difficulty="easy")

exec1 = TaskExecution(coding, 90)
exec2 = TaskExecution(reading, 30)

session = Session(
    AllocationEngine(RandomAllocation()),
    TimeBasedPolicy()
)

session.log_execution(exec1)  # 90 × 2 × 1.3 = 234 XP
session.log_execution(exec2)  # 30 × 2 × 0.8 = 48 XP
# Total: 282 XP

# Early morning bonus (before 9am): 1.5x
# Points = 282 × 1.5 = 423 points

session.allocate(wishlist)
# Distributes 423 points randomly across wishlist items
```

---

## 🎯 Summary

This productivity system is a **well-architected** gamification engine that:

1. **Converts work into rewards** through a multi-stage pipeline
2. **Uses design patterns** (Strategy, Dependency Injection, Composite, Repository)
3. **Follows SOLID principles** (Single Responsibility, Open/Closed)
4. **Is highly extensible** (easy to add new policies, strategies, task types)
5. **Persists data** (survives across sessions)
6. **Enforces rules** (daily XP caps, mandatory tasks, minimum XP)

### The Beauty of This Design:

- **Session** doesn't know HOW points are allocated (strategy handles that)
- **XPBar** doesn't know WHY XP is earned (tasks handle that)
- **WishList** doesn't know HOW points were calculated (policies handle that)
- **Each component has ONE job** and does it well

This is **production-quality Low-Level Design** that would impress in technical interviews!
