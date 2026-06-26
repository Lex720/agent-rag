# ARCHITECTURE.md

## When to apply each pattern

| Scenario | Architecture |
|---|---|
| Single script (1-2 files) | Simple functions, no layers |
| Multiple shared modules | Separate business logic from I/O, no formal layers |
| CRUD or multiple entities | Clean Architecture + DDD |
| Separate read/write models or high scale | Add CQRS |

## Clean Architecture
Layers: `domain` → `application` → `infrastructure` → `presentation`.
Domain has no external dependencies. Dependencies point inward only.

## DDD
- Entity: has identity, mutable state → `dataclass`
- Value object: represents a value, must not mutate → `dataclass(frozen=True)`
- Ubiquitous language: code names reflect business language.

## CQRS
Separate commands (write) from queries (read). Apply only when read and write have different models or scale needs.

## Data structures by layer

| Layer | Tool |
|---|---|
| Presentation (request/response) | `pydantic BaseModel` |
| Application (commands, queries) | `dataclass` |
| Domain (entities, value objects) | `dataclass` / `dataclass(frozen=True)` |
| Infrastructure (repositories) | native types: `dict`, `list`, `int` |

Rule: data crossing an external boundary → pydantic. Internal data → dataclass.

## frozen=True vs frozen=False
- `frozen=False`: entity with lifecycle, state changes over time → `Order`, `User`
- `frozen=True`: value object, never mutates → `Money`, `UserId`. Also makes it hasheable (usable as dict key or in sets).

## Validation placement
- Format/syntax rules (valid email, non-empty field) → input DTO `field_validator`
- Business rules (delivery date > creation date) → domain entity `__post_init__`

## Pure functions
One responsibility per function. Separate business logic from I/O. Business functions testeable without mocks.
