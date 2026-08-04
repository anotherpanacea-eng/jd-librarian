---
description: Audit a Johnny.Decimal system by comparing the JDex against the folder structure
argument-hint: "[system-code]"
allowed-tools: [Read, Glob, Grep, Bash, Write]
---

# Audit JDex

Compare a system's JDex against its actual folder structure, flagging
structural violations, undocumented folders, name mismatches, and +SUB index
issues.

The two sides are **not symmetric**. The JDex is the system; the filesystem is
one of several places an ID's material happens to live.

## Arguments

`$ARGUMENTS` may contain a system code (e.g., `P10`) to audit a specific
system. If no argument is provided, list all available systems and ask which
to audit.

## Workflow

1. **Load** the target system's JDex.
2. **Snapshot** the filesystem to depth 3.
3. **Check the tree first** — duplicate category numbers, unnumbered folders
   inside numbered areas, files at area or category level, areas over ten
   categories, nesting past ID-plus-one, IDs occupying the reserved `.00`–`.09`
   range. A JDex diff is meaningless over a tree with collisions in it.
4. **Compare** JDex entries against folders:
   - Undocumented folders (folder exists, not in JDex) — **always a defect**
   - Name mismatches between JDex and folder names
   - Entries whose *recorded filesystem location* is missing. An entry with no
     folder at all is usually **correct**: the ID may name material that lives
     only in email, on paper, or on another machine.
5. **Check** +SUB index files against +SUB folders.
6. **Report** findings in a structured table, structural violations first.
7. **Offer fixes**: Add missing JDex entries, update +SUB indexes, or flag
   items that need user decisions.

## Safe Fixes

- Adding undocumented folders to the JDex
- Updating +SUB index files with missing entries

## Requires User Decision

- Entries whose recorded path is missing (was the folder moved, or is the path
  a typo?)
- Name mismatches (which name is correct?)
- Deleting or renaming any folder
- Any structural violation — collisions and renumbering are never automatic

## Never

- Delete a JDex entry because it has no folder. The entry **is** the ID.

## Examples

```
/jd-librarian:jdex-audit
/jd-librarian:jdex-audit P10
/jd-librarian:jdex-audit F50
```
