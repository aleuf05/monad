# Monad Education 001 — Moonbase Architect v0.1

**Audience**: Fourth grade  
**Subject**: Common Core Mathematics  
**Focus**: Area, perimeter, multiplication, factors, optimization

## Core Principle

The child manipulates a mathematical world directly rather than answering worksheets.
The mathematics is deterministic and implemented directly in code.

## User Experience

- Instant lunar construction environment (no login, onboarding sequence, curriculum picker, or manual).
- Interactive square grid representing the habitat.
- Direct manipulation via mouse, touch, stepper buttons, and sliders.
- Instant calculation updates on the Compact Engineering Instrument Panel:
  - `WIDTH`
  - `LENGTH`
  - `FLOOR TILES / AREA` ($W \times L$)
  - `OUTSIDE WALL / PERIMETER` ($2W + 2L$)
  - `SHIELDING COST` ($P \times \$10,000$)

## Missions

1. **Mission 1 — BUILD IT**: Build an area of exactly 48 floor tiles (accepts all factor pairs: $6 \times 8$, $4 \times 12$, $3 \times 16$, $2 \times 24$, $1 \times 48$, etc.).
2. **Mission 2 — MAKE IT CHEAPER**: Keep 48 floor tiles while minimizing the exterior wall perimeter. Discovers the $6 \times 8$ minimum perimeter ($P = 28\text{m}$) engineering record.
3. **Mission 3 — BEAT THE ENGINEERS**: Given a fixed exterior wall budget ($P \le 24\text{m}$), build the largest possible floor area (discovers the $6 \times 6 = 36$ square maximum area).
4. **Sandbox — FREE BUILD**: Freeform manipulation up to $24 \times 24$.

## MARA (Moonbase Architecture & Research Assistant)

Deterministic, state-aware responses triggered by actual behavior to guide observation rather than revealing answers.
