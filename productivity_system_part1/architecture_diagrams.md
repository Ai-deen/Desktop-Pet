# System Architecture Diagrams

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         MAIN.PY                             │
│                     (Entry Point)                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├──────────────────────────────────────┐
                 │                                      │
                 ▼                                      ▼
        ┌────────────────┐                    ┌─────────────────┐
        │   WISHLIST     │                    │     SESSION     │
        │   REPOSITORY   │                    │  (Orchestrator) │
        └────────┬───────┘                    └────────┬────────┘
                 │                                     │
                 │ loads/saves                         │
                 ▼                                     │
        ┌────────────────┐              ┌──────────────┼──────────────┐
        │   WISHLIST     │              │              │              │
        │  - items       │◄─────────────┤              │              │
        │  - history     │  allocates   │              │              │
        └────────────────┘  points to   │              │              │
                 │                      │              │              │
                 │ contains             ▼              ▼              ▼
                 ▼              ┌──────────┐   ┌──────────┐   ┌──────────┐
        ┌────────────────┐     │  XP BAR  │   │  POINT   │   │ALLOCATION│
        │ WISHLIST ITEM  │     │          │   │  POLICY  │   │  ENGINE  │
        │ - permanent    │     └──────────┘   └──────────┘   └────┬─────┘
        │ - flexible     │                                          │
        └────────────────┘                                          │
                                                                    │ uses
                                                                    ▼
                                                            ┌────────────────┐
                                                            │   ALLOCATION   │
                                                            │    STRATEGY    │
                                                            └────────────────┘
```

## 2. Data Flow Diagram

```
USER COMPLETES TASK
        │
        ▼
┌────────────────────┐
│  TASK EXECUTION    │  ──► Contains reference to Task
│  - task            │      (DSA, LLD, etc.)
│  - minutes: 60     │
└─────────┬──────────┘
          │
          │ calculate_xp()
          │ = minutes × 2 × difficulty_weight
          ▼
    ┌──────────┐
    │ XP: 156  │
    └─────┬────┘
          │
          │ log_execution()
          ▼
    ┌──────────────────┐
    │    XP BAR        │
    │ current_xp: 156  │  ──► Enforces daily cap (1000)
    │ daily_cap: 1000  │
    └─────┬────────────┘
          │
          │ allocate()
          ▼
    ┌──────────────────┐
    │  POINT POLICY    │
    │ (TimeBasedPolicy)│  ──► Applies multipliers
    │ XP × multiplier  │      (weekend, early morning, etc.)
    └─────┬────────────┘
          │
          │ to_points()
          ▼
    ┌──────────┐
    │Points:203│
    └─────┬────┘
          │
          │ AllocationEngine.run()
          ▼
    ┌────────────────────────┐
    │ ALLOCATION STRATEGY    │
    │ (RandomAllocation)     │  ──► Decides how to split
    └─────┬──────────────────┘      points across items
          │
          │ allocate()
          ▼
    ┌────────────────────────┐
    │ Item: Headphones       │
    │ permanent_points += 67 │
    │ flexible_points += 35  │
    └─────┬──────────────────┘
          │
          │ apply_allocation()
          ▼
    ┌────────────────────────┐
    │ ALLOCATION RECORD      │  ──► History tracking
    │ - item_name           │
    │ - permanent: 67       │
    │ - flexible: 35        │
    │ - timestamp           │
    └─────┬──────────────────┘
          │
          │ save()
          ▼
    ┌────────────────┐
    │ wishlist.json  │  ──► Persistent storage
    └────────────────┘
```

## 3. Module Interaction Map

```
╔══════════════════════════════════════════════════════════╗
║                    TASKS MODULE                          ║
╠══════════════════════════════════════════════════════════╣
║  TaskComponent (ABC)                                     ║
║      ├─ Task (individual task)                           ║
║      └─ TaskGroup (composite of tasks)                   ║
║                                                          ║
║  TaskExecution (records actual work)                     ║
╚═════════════════════╤════════════════════════════════════╝
                      │
                      │ generates
                      ▼
╔══════════════════════════════════════════════════════════╗
║                     XP MODULE                            ║
╠══════════════════════════════════════════════════════════╣
║  XPBar                                                   ║
║    - Tracks XP                                           ║
║    - Enforces daily cap                                  ║
╚═════════════════════╤════════════════════════════════════╝
                      │
                      │ converts via
                      ▼
╔══════════════════════════════════════════════════════════╗
║                   POINTS MODULE                          ║
╠══════════════════════════════════════════════════════════╣
║  PointPolicy (ABC)                                       ║
║      ├─ TimeBasedPolicy (time multipliers)               ║
║      └─ DifficultyPolicy (difficulty multipliers)        ║
╚═════════════════════╤════════════════════════════════════╝
                      │
                      │ feeds into
                      ▼
╔══════════════════════════════════════════════════════════╗
║                STRATEGIES MODULE                         ║
╠══════════════════════════════════════════════════════════╣
║  AllocationEngine (uses strategy)                        ║
║      │                                                   ║
║      ├─ RandomAllocation                                 ║
║      ├─ LockedAllocation                                 ║
║      └─ FlexibleAllocation                               ║
╚═════════════════════╤════════════════════════════════════╝
                      │
                      │ distributes to
                      ▼
╔══════════════════════════════════════════════════════════╗
║                 WISHLIST MODULE                          ║
╠══════════════════════════════════════════════════════════╣
║  WishList                                                ║
║      ├─ WishlistItem (rewards)                           ║
║      └─ AllocationRecord (history)                       ║
║                                                          ║
║  WishlistRepository (persistence)                        ║
╚═════════════════════╤════════════════════════════════════╝
                      │
                      │ coordinated by
                      ▼
╔══════════════════════════════════════════════════════════╗
║                    CORE MODULE                           ║
╠══════════════════════════════════════════════════════════╣
║  Session (orchestrates all components)                   ║
║    - log_execution()                                     ║
║    - allocate()                                          ║
║    - validate_mandatory_tasks()                          ║
║                                                          ║
║  main.py (entry point)                                   ║
╚══════════════════════════════════════════════════════════╝
```

## 4. Class Relationship Diagram

```
                    ┌──────────────┐
                    │TaskComponent │ (ABC)
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        ┌───────▼────┐        ┌──────▼─────┐
        │    Task    │        │ TaskGroup  │
        └───────┬────┘        └──────┬─────┘
                │                    │
                │ referenced by      │ contains
                │                    │
        ┌───────▼─────────┐          │
        │ TaskExecution   │          │
        │                 │          │
        │ + calculate_xp()│          │
        └────────┬────────┘          │
                 │                   │
                 │                   │
                 ▼                   ▼
        ┌─────────────────────────────────┐
        │          SESSION                │
        ├─────────────────────────────────┤
        │ - xp_bar: XPBar                 │
        │ - allocation_engine             │
        │ - point_policy                  │
        │ - executed_tasks: set           │
        ├─────────────────────────────────┤
        │ + log_execution()               │
        │ + allocate()                    │
        │ + validate_mandatory_tasks()    │
        └───┬─────────────────────────┬───┘
            │                         │
            │ has                     │ has
            │                         │
    ┌───────▼────────┐       ┌────────▼─────────┐
    │     XPBar      │       │  PointPolicy     │ (ABC)
    ├────────────────┤       └────────┬─────────┘
    │ - current_xp   │                │
    │ - daily_cap    │     ┌──────────┴──────────┐
    ├────────────────┤     │                     │
    │ + add_xp()     │ ┌───▼──────────┐  ┌───────▼────────┐
    │ + is_full()    │ │TimeBasedPolicy│  │DifficultyPolicy│
    └────────────────┘ └───────────────┘  └────────────────┘


        ┌───────────────────┐
        │ AllocationEngine  │
        ├───────────────────┤
        │ - strategy        │
        ├───────────────────┤
        │ + run()           │
        └─────────┬─────────┘
                  │
                  │ uses
                  ▼
        ┌────────────────────────────┐
        │ PointAllocationStrategy    │ (ABC)
        └────────────┬───────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼────┐ ┌────▼─────┐ ┌───▼──────────┐
│  Random    │ │  Locked  │ │  Flexible    │
│Allocation  │ │Allocation│ │ Allocation   │
└────────────┘ └──────────┘ └──────────────┘
        │
        │ allocates to
        ▼
┌────────────────────┐
│     WishList       │
├────────────────────┤
│ - items[]          │───┐
│ - history[]        │   │
├────────────────────┤   │ contains
│ + add_item()       │   │
│ + apply_allocation │   │
└────────────────────┘   │
                         │
        ┌────────────────┴─────────────┐
        │                              │
┌───────▼───────┐          ┌───────────▼──────┐
│ WishlistItem  │          │AllocationRecord  │
├───────────────┤          ├──────────────────┤
│ - name        │          │ - item_name      │
│ - price       │          │ - permanent      │
│ - time        │          │ - flexible       │
│ - priority    │          │ - timestamp      │
│ - permanent   │          ├──────────────────┤
│ - flexible    │          │ + to_dict()      │
├───────────────┤          │ + from_dict()    │
│ + to_dict()   │          └──────────────────┘
└───────────────┘
```

## 5. Sequence Diagram for Complete Flow

```
User    main.py   Session   TaskExec   XPBar   PointPolicy   Engine   Strategy   WishList
 │         │         │          │         │         │          │         │          │
 │ work    │         │          │         │         │          │         │          │
 ├────────►│         │          │         │         │          │         │          │
 │         │         │          │         │         │          │         │          │
 │         │ create TaskExecution         │         │          │         │          │
 │         ├────────────────────►│        │         │          │         │          │
 │         │                     │        │         │          │         │          │
 │         │ log_execution(exec) │        │         │          │         │          │
 │         ├────────────────────►│        │         │          │         │          │
 │         │                     │        │         │          │         │          │
 │         │                     │calculate_xp()   │          │         │          │
 │         │                     ├───────►│        │          │         │          │
 │         │                     │ return XP       │          │         │          │
 │         │                     │◄───────┤        │          │         │          │
 │         │                     │        │        │          │         │          │
 │         │ add_xp(156)         │        │        │          │         │          │
 │         ├─────────────────────┼───────►│        │          │         │          │
 │         │                     │        │enforce │          │         │          │
 │         │                     │        │  cap   │          │         │          │
 │         │                     │        │        │          │         │          │
 │         │ allocate(wishlist)  │        │        │          │         │          │
 │         ├────────────────────►│        │        │          │         │          │
 │         │                     │        │        │          │         │          │
 │         │                     │ check minimum XP│          │         │          │
 │         │                     ├───────►│        │          │         │          │
 │         │                     │        │        │          │         │          │
 │         │                     │ to_points(xp, session)     │         │          │
 │         │                     ├────────┼───────►│          │         │          │
 │         │                     │        │  apply multiplier  │         │          │
 │         │                     │        │        │          │         │          │
 │         │                     │ return points   │          │         │          │
 │         │                     │◄───────┼────────┤          │         │          │
 │         │                     │        │        │          │         │          │
 │         │                     │ run(points, wishlist)       │         │          │
 │         │                     ├────────┼────────┼─────────►│         │          │
 │         │                     │        │        │          │         │          │
 │         │                     │        │        │   allocate(points, wishlist)  │
 │         │                     │        │        │          ├────────►│          │
 │         │                     │        │        │          │         │          │
 │         │                     │        │        │          │ apply_allocation() │
 │         │                     │        │        │          │         ├─────────►│
 │         │                     │        │        │          │         │  update  │
 │         │                     │        │        │          │         │  items   │
 │         │                     │        │        │          │         │  create  │
 │         │                     │        │        │          │         │  record  │
 │         │                     │        │        │          │         │◄─────────┤
 │         │                     │        │        │          │         │          │
 │         │ save(wishlist)      │        │        │          │         │          │
 │         ├─────────────────────┼────────┼────────┼──────────┼─────────┼─────────►│
 │         │                     │        │        │          │         │  to JSON │
 │         │                     │        │        │          │         │          │
 │◄────────┤                     │        │        │          │         │          │
 │ results │                     │        │        │          │         │          │
```

## 6. Strategy Pattern Implementation

```
                    ┌──────────────────────┐
                    │  PointPolicy (ABC)   │
                    │ ─────────────────────│
                    │ + to_points()        │
                    └──────────┬───────────┘
                               │
                               │ implements
                ┌──────────────┴──────────────┐
                │                             │
        ┌───────▼─────────┐          ┌────────▼────────┐
        │TimeBasedPolicy  │          │DifficultyPolicy │
        │─────────────────│          │─────────────────│
        │Weekend: 1.3x    │          │Easy: 0.5x       │
        │Morning: 1.5x    │          │Medium: 1.0x     │
        │Afternoon: 0.7x  │          │Hard: 1.5x       │
        └─────────────────┘          └─────────────────┘

                    ┌──────────────────────────────┐
                    │ PointAllocationStrategy (ABC)│
                    │ ─────────────────────────────│
                    │ + allocate()                 │
                    └──────────┬───────────────────┘
                               │
                               │ implements
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼────┐   ┌────────────▼────┐
│Random          │   │Locked        │   │Flexible         │
│Allocation      │   │Allocation    │   │Allocation       │
│────────────────│   │──────────────│   │─────────────────│
│Random split    │   │Equal split   │   │Equal split      │
│Perm + Flex     │   │All permanent │   │All flexible     │
└────────────────┘   └──────────────┘   └─────────────────┘
```

## 7. Dependency Injection Flow

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  engine = AllocationEngine(RandomAllocation())          │
│           ─────────────────────────────────             │
│                      │                                  │
│                      │ Inject Strategy                  │
│                      ▼                                  │
│           ┌────────────────────┐                        │
│           │ AllocationEngine   │                        │
│           │  - strategy        │                        │
│           └────────────────────┘                        │
│                                                         │
│  policy = TimeBasedPolicy()                             │
│           ──────────────────                            │
│                      │                                  │
│                      │ Inject Policy                    │
│                      ▼                                  │
│           ┌────────────────────┐                        │
│           │  TimeBasedPolicy   │                        │
│           └────────────────────┘                        │
│                                                         │
│  session = Session(engine, policy)                      │
│            ────────────────────────                     │
│                      │                                  │
│                      │ Inject Dependencies              │
│                      ▼                                  │
│           ┌────────────────────┐                        │
│           │      Session       │                        │
│           │  - engine          │◄─── Doesn't create    │
│           │  - policy          │     these internally! │
│           │  - xp_bar          │                        │
│           └────────────────────┘                        │
│                                                         │
└─────────────────────────────────────────────────────────┘

BENEFIT: Can easily swap strategies and policies without
         modifying Session class
```
