---
name: jd-system-setup
description: >
  Initialize a new Johnny.Decimal system by creating the folder structure,
  standard zeros, and initial JDex. Use this skill when the user wants to
  set up a new JD system, create their JD folder structure, initialize a
  system, start organizing with Johnny.Decimal, or says things like "set up
  my JD system," "create a new system," "initialize JD," "build my folder
  structure," or "I want to start using Johnny.Decimal." Handles both
  single-system and multi-system (SYS.AC.ID) configurations.
---

# Johnny.Decimal System Setup

This skill creates a new Johnny.Decimal system from scratch — building the
folder structure, standard zeros, and initial JDex based on the user's needs.

Before doing anything, read
`../jd-inbox-processor/references/jd-system-rules.md` — the plugin's single
source of Johnny.Decimal canon. It marks which conventions come from
<https://johnnydecimal.com/documentation> and which are this plugin's own
house style, so you never present a house rule to the user as a rule of JD.


---

## 1. Gather Requirements

Before creating anything, understand what the user needs.

### 1.1 Single or Multi-System?

Ask the user:

- **Single system**: One organizational domain (e.g., just personal life, or
  just work). No system prefix needed — folders use plain `AC.ID` notation.
- **Multi-system**: Multiple distinct domains (e.g., personal + work, or
  personal + work + child). Each system gets a `SYS` prefix using the
  `[A-Z][0-9][0-9]` format.

If the user already has JD systems, check the existing root to avoid
conflicts.

### 1.2 System Identity

For each system to create, gather:

- **System code** (multi-system only): A three-character `[A-Z][0-9][0-9]`
  identifier. Encourage memorable codes (e.g., `P10` for personal, `W20` for
  work). The code should be visually distinctive.
- **System name**: A plain-English name (e.g., "Personal", "Work", "Jamie").
- **Root location**: Where the system will live on disk. Common locations:
  - `~/Library/Mobile Documents/com~apple~CloudDocs/JD/` (iCloud Drive)
  - `~/Documents/JD/`
  - `~/JD/`

### 1.3 Areas and Categories

Walk the user through defining their areas. Provide guidance:

- Maximum 10 areas (including `00-09 System`)
- Each area covers a major life/work domain
- Fewer areas is better — compression over granularity
- Area `00-09` is always created automatically for system management

For each area, ask about categories:

- Maximum 10 categories per area
- Categories are "where you work" — collections of similar things
- Category names should be short and clear

For each category, ask if they have specific IDs in mind, or if they'll create
IDs as content arrives.

---

## 2. Create the Folder Structure

### 2.1 System Root

Create the system root folder:

- **Single system**: `[Root]/` (e.g., `~/JD/`)
- **Multi-system**: `[Root]/SYS Name/` (e.g., `~/JD/P10 Personal/`)

### 2.2 Area Folders

Create area folders using the format `AC-range Description`:

```
00-09 System
10-19 [Area name]
20-29 [Area name]
...
```

### 2.3 Category Folders

Within each area, create category folders using the format `AC Description`:

```
00 System management
01 [Category name]
11 [Category name]
12 [Category name]
...
```

### 2.4 Standard Zeros

The standard zeros are the same seven meanings at every level. Do not invent
new ones — `.05` through `.08` are **reserved by the specification**, and
assigning them a local meaning breaks compatibility with every other JD tool
the user might adopt.

| ID | Purpose |
|----|---------|
| `.00` | JDex |
| `.01` | Inbox |
| `.02` | Task & project management |
| `.03` | Templates |
| `.04` | Links |
| `.05`–`.08` | **Reserved — leave empty** |
| `.09` | Archive |

**System level** — create in `00-09 System/00 System management/`:

| Path | Purpose |
|------|---------|
| `00.00 JDex.md` | Master index export (see §3 for why this is a *view*, not the JDex itself) |
| `00.01 Inbox/` | Captures with no home yet |
| `00.02 Tasks/` | `todo.txt`, `done.txt`, `someday.txt`, and the processing log |
| `00.09 Archive/` | Kept, never to be organised |

Note what moved: a "Someday" list and a "Needs review" queue are **task
management**, so they live under `.02` as files. Earlier versions of this
plugin put them at `00.08` and `00.04`; those are reserved and "Links"
respectively. If you encounter a system built that way, say so and offer to
migrate — don't perpetuate it.

**Category level** — offer, per category, once the user has categories they
actually work in:

```
15.01 Inbox/
15.09 Archive/
```

Because the rule is **prefer the most specific zero**, category inboxes are
where day-to-day capture should land. Don't bulk-create them for all ten
categories at setup; create them for the two or three categories that see
real traffic, and let the rest appear on demand.

### 2.5 ID Folders

If the user specified initial IDs during requirements gathering, create them
using the format `AC.ID Description`:

```
11.01 Mortgage & title/
11.02 Property tax/
11.03 Homeowners insurance/
```

---

## 3. Generate the JDex

> **"Your filesystem is not your index."** In Johnny.Decimal the JDex is a set
> of notes — one per ID — usually kept in a notes app, and the note is created
> **before** the folder. Creating the note *is* creating the ID.
>
> The `00.00 JDex.md` file below is a flat **export** of that index, so
> file-based tooling has something to read. Tell the user which one they're
> adopting. If they keep their real JDex in Obsidian, Bear, Apple Notes, or
> anywhere else, this file is generated *from* it and must never become the
> place they edit.

Create `00.00 JDex.md` with a complete listing of every area, category, and
ID in the system.

### JDex Format

```markdown
# [SYS] JDex

## 00-09 System
- 00.00 JDex ← this file
- 00.01 Inbox
- 00.02 Tasks
- 00.02 Tasks (todo / done / someday / processing-log)

## 10-19 [Area name]

### 11 [Category name]
- 11.01 [ID description]
- 11.02 [ID description]

### 12 [Category name]
- 12.01 [ID description]

## 20-29 [Area name]
...
```

Each entry should carry more than a title. A JDex entry records **where the
thing actually is** — which for most IDs is several places at once — plus
keywords and any decision worth not re-making:

```markdown
### 15 Travel
- **15.55 Japan, 2025**
  - Files: `15.55 Japan, 2025/`
  - Email: label `travel/japan-2025`
  - Paper: ring binder, shelf 2
  - Keywords: JAL, Kyoto, ryokan, JR pass
  - Note: flight PDFs stay in email; only the itinerary is filed
```

### JDex Rules

- Every folder that exists must have a JDex entry.
- **A JDex entry need not have a folder.** This is the point of the index:
  an ID can name material that lives only in email, on paper, in a SaaS app,
  or on another machine. Do not "clean up" such entries.
- Child IDs created by extending the end (`13.41+ Ozito mower`) get their own
  entry, listed under the parent.
- Cross-system references use arrow notation: `→ P10.34.01`.

---

## 4. Initialize Task and Log Files

### 4.1 Tasks File

Create `00.02 Tasks.md`:

```markdown
# [System name] Tasks

Tasks extracted during inbox processing and daily use.

---

<!-- Add tasks below this line -->
```

### 4.2 Processing Log

Create `00.02 Tasks/processing-log.md`:

```markdown
# [System name] Processing Log

Record of inbox processing sessions.

---

<!-- Processing entries will be appended below -->
```

---

## 5. Verification

After creating the structure:

1. **List the complete folder tree** to depth 3 and present it to the user
   for review.
2. **Display the JDex** so the user can verify all entries are correct.
3. **Confirm iCloud sync** (if applicable): Verify folders appear correctly.
4. **Note next steps**: Suggest the user start capturing items into their
   inbox and run `/jd-librarian:process-inbox` when ready.

---

## 6. Multi-System Considerations

When setting up multiple systems at once:

- Each system gets its own independent JDex
- Each system gets its own standard zeros
- Cross-system references should be noted during setup if known
  (e.g., "F50.32.01 will reference P10.34.01 for health insurance")
- Suggest the user set up one system fully before moving to the next

---

## 7. Templates for Common System Types

Offer these as starting points when the user isn't sure what areas to create:

### Personal Life System

```
00-09 System
10-19 Home & property
20-29 Family & relationships
30-39 Money & legal
40-49 Health & wellness
50-59 Projects & hobbies
60-69 Travel & experiences
```

### Work System

```
00-09 System & employment
10-19 [Primary work domain]
20-29 Career development
30-39 Professional visibility
```

### Child/Dependent System

```
00-09 System
10-19 Identity & documents
20-29 School / academics
30-39 Health & medical
40-49 Activities & interests
```

These are suggestions, not prescriptions. The user's actual needs should
drive the structure.
