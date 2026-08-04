---
description: Initialize a new Johnny.Decimal system with folder structure, standard zeros, and JDex
argument-hint: ""
allowed-tools: [Read, Glob, Grep, Bash, Write]
---

# Set Up a Johnny.Decimal System

Create a new Johnny.Decimal system from scratch — folders, standard zeros,
and initial JDex.

## Arguments

No required arguments. The command will walk the user through an interactive
setup process.

## Workflow

1. **Ask** whether this is a single-system or multi-system setup.
2. **Gather** system identity: code (if multi-system), name, and root location.
3. **Define areas**: Walk through area definitions (max 10 including 00-09).
4. **Define categories**: For each area, define categories (max 10 per area,
   `x0` through `x9`). `x0` is the area-management category — create it, don't
   skip it. Prefer fewer, broader categories.
5. **Define initial IDs**: Optionally pre-create ID folders. Content IDs start
   at `.10` — `.00`–`.09` are the standard zeros.
6. **Create structure**: Build all folders on disk.
7. **Generate JDex**: Ask first where the real index lives — a notes app is
   the JD-native answer, and "your filesystem is not your index." Write
   `00.00 JDex.md` as a flat **export** for tooling, never as the place the
   user edits.
8. **Initialize files**: Create `00.02 Tasks/` holding `todo.txt`, `done.txt`,
   `someday.txt`, and `processing-log.md`. Do not assign `.04`–`.08`; `.04` is
   Links and `.05`–`.08` are reserved by the spec.
9. **Verify**: Display the complete folder tree for user review.

## Templates

Offer starting templates for common system types:

- **Personal life**: Home, family, money, health, projects, travel, hobbies
- **Work**: System/employment, primary work domain, career, visibility
- **Child/dependent**: Identity, school, health, activities

## Examples

```
/jd-librarian:setup-system
```
