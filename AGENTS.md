# TaxiMobile — Coding Agent Instructions

## Project

TaxiMobile is a cross-platform taxi application intended to provide digital infrastructure for taxi drivers and passengers.

The project uses Kotlin Multiplatform / Compose Multiplatform for shared application development.

---

## Before Coding

Before making changes:

1. Read the relevant files in `docs/`.
2. Understand the existing architecture.
3. Check whether the requested functionality already exists.
4. Avoid changing unrelated code.
5. Follow existing conventions.

Do not read every documentation file for every task. Read the documents relevant to the current task.

---

## Documentation Authority

The following documents define project decisions:

```text
docs/product.md
docs/architecture.md
docs/api.md
docs/auth.md
docs/database.md
docs/drivers.md
docs/rides.md
docs/matching.md
docs/pricing.md
docs/payments.md
docs/design.md
docs/ui.md
docs/extended_ui.md
docs/security.md
docs/roadmap.md
docs/implementation.md
```

If implementation conflicts with documentation, stop and identify the conflict rather than silently inventing a new architecture.

---

## Implementation Rules

### Keep changes focused

A task should modify only the files necessary to accomplish it.

Do not perform unrelated refactoring.

### Prefer simple solutions

Use the simplest architecture that satisfies the documented requirements.

Do not introduce additional frameworks, services, or abstractions without a reason.

### Do not prematurely implement future features

Consult `docs/roadmap.md`.

A feature being possible does not mean it should be implemented now.

### Backend authority

The client must not be treated as authoritative for:

* Authentication
* Authorization
* Ride assignment
* Pricing
* Payment status
* Driver eligibility

### Shared code

Business logic that can be shared between platforms should remain in the shared Kotlin module.

Platform-specific functionality belongs in the appropriate platform source set.

### UI

Follow `docs/design.md` for interaction and state-authority rules.

Follow `docs/ui.md` for visual identity, layout chrome, typography, motion, and shared components.

Keep the Compose shell minimal until a documented UI wave is being implemented. Do not invent a competing brand system.

### Database

Do not modify the database schema casually.

Schema changes should be deliberate and reflected in `docs/database.md` when they affect the documented model.

### API

Do not create duplicate API conventions.

Follow `docs/api.md`.

### Security

Never:

* Commit secrets.
* Hard-code credentials.
* Trust client-provided authorization.
* Expose unnecessary personal data.
* Store sensitive information without a reason.

---

## Testing

When implementing functionality:

1. Add or update appropriate tests.
2. Run relevant tests.
3. Fix failures caused by the change.
4. Do not declare functionality complete without verifying it.

Testing should focus first on business logic and backend behavior.

---

## Error Handling

Errors should be explicit and actionable.

Do not silently swallow exceptions.

Do not use generic error handling everywhere merely to make the application appear functional.

---

## Dependencies

Do not add a dependency simply because it makes a small task easier.

Before adding one, consider whether:

* Existing dependencies already provide the functionality.
* The dependency is maintained.
* It is compatible with all required platforms.
* It introduces unnecessary complexity.

---

## Communication

When completing a task, report:

```text
What changed
Files changed
Tests performed
Known limitations
```

If a requirement is ambiguous or conflicts with the documentation, ask before making a major architectural decision.

---

## Scope

The coding agent is responsible for implementing the software.

The project owner retains final control over:

* Product direction
* Visual design
* Business rules
* Pricing policy
* Deployment decisions
* Major architectural changes
