LLD Concepts Used in the Productivity / XP System
1. Single Responsibility Principle (SRP)

Definition
A class should have one and only one reason to change.

Where it appears in your code
WorkSession

Responsibility: represent work effort

Inputs: hours, metadata

Output: raw XP

It does not:

Apply difficulty

Enforce limits

Handle rewards

That’s correct SRP.

XPBar

Responsibility: enforce XP limits

Knows:

Daily cap

Current XP

Does not know:

Why XP was earned

How XP converts to rewards

Wishlist

Responsibility: reward redemption

Manages items, costs, persistence

It does not care:

How points were earned

How sessions work

👉 This separation prevents ripple effects.

2. Strategy Pattern (Core LLD Concept)

Definition
Define a family of algorithms, encapsulate each one, and make them interchangeable.

Structure in your system
Strategy Interface
PointPolicy (abstract)
└── to_points(xp, session)


This defines what can vary.

Concrete Strategies

DifficultyPolicy

TimePolicy

Each:

Implements the same interface

Encapsulates one rule

Is independently replaceable

Why this is good design

Adding a new rule (e.g., streak bonus) requires:

New class

No modification to existing code

This follows Open/Closed Principle.

Interview framing

“I used Strategy Pattern to decouple XP calculation rules from session orchestration, allowing new scoring policies to be added without modifying existing logic.”

3. Open / Closed Principle (OCP)

Definition
Software entities should be open for extension, closed for modification.

Where it appears

You can add:

New point rules

New reward logic

New caps

Without modifying:

Session

WorkSession

Existing policies

This is real OCP, not theoretical.

4. Dependency Injection (Manual DI)

Definition
Dependencies are supplied from the outside rather than created internally.

In your system

Session does NOT do this:

self.policy = DifficultyPolicy()


Instead:

Session(policies=[DifficultyPolicy(), TimePolicy()])

Why this matters

Loose coupling

Easy testing

Configurable behavior

This is constructor injection, the simplest DI form.

Interview framing

“I avoided hard dependencies by injecting policies and XP constraints into the session object, which keeps orchestration logic flexible.”

5. Composition over Inheritance

Definition
Prefer building behavior by composing objects instead of extending classes.

Example

Instead of:

HardSession extends Session


You have:

Session
 ├── WorkSession
 ├── XPBar
 └── List<PointPolicy>

Why this is superior

No rigid inheritance tree

Behavior changes at runtime

More realistic domain modeling

This is good LLD maturity.

6. Separation of Concerns (SoC)

Definition
Different aspects of the system are handled in different layers/modules.

Your module separation
Concern	Module
Effort tracking	xp/
Point conversion	points/
Orchestration	core/
Rewards	wishlist/
Execution	main.py

This is clean vertical slicing.

7. Orchestrator Pattern (Session)

What Session is

Not a data object

Not a strategy

Not a utility

It is an orchestrator:

Coordinates multiple subsystems

Controls execution order

Enforces invariants

Why this is acceptable (for now)

Centralized flow control

Clear entry point

Avoids scattered logic

⚠️ Risk: can become a God Object if expanded carelessly.

8. Encapsulation

Definition
Objects protect their internal state and expose behavior through methods.

Examples

XP cannot exceed cap because:

XPBar enforces it internally

Points cannot be arbitrarily redeemed:

Wishlist validates cost internally

State is not manipulated directly.

9. Domain Modeling (Partial but Present)

You modeled concepts, not just data.

Examples:

WorkSession ≠ hours (it’s effort)

XP ≠ points (two different currencies)

Wishlist ≠ points store (has rules)

This is early domain-driven thinking, even if informal.