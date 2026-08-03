# Johnny.Decimal System Rules Reference

The structural conventions that govern all classification and filing
decisions. This file is the plugin's single source of canon; every skill in
this plugin reads it.

Sourced from <https://johnnydecimal.com/documentation>. Where this plugin
adds a convention that is *not* in the official documentation, it is marked
**[plugin convention]** so you never present it to the user as a rule of
Johnny.Decimal.

---

## The Three-Level Hierarchy

Johnny.Decimal has exactly three levels. Nothing deeper.

```
Area (00-09, 10-19, 20-29, ..., 90-99)
  └── Category (two-digit number within the area range: 10, 11, ..., 19)
        └── ID (AC.ID format: 11.01, 11.02, ..., 11.99)
```

### Areas

- Ranges of ten: `00-09`, `10-19`, ..., `90-99` — ten areas maximum.
- `00-09` is the system-management area.
- Areas are broad domains of life or work. **Make them broad enough to grow:**
  "if they're too narrow, you'll use them up."
- Folder name format: `10-19 Description`.
- Never save files directly in area folders. Area-level material belongs in
  the area's `x0` management category (below).

### Categories

- Two-digit numbers within the area's range: `10` through `19` for area
  `10-19`. Ten categories maximum per area.
- **`x0` is the area-management category** — e.g. `10 Management of area
  10-19`. It is a real category, not a skipped slot.
- Categories are "where you work" — the point at which you sit down with a
  task in mind. **Prefer fewer, broader categories.** One `13 Money` beats
  separate investments / budget / savings categories; granularity is what
  produces decision paralysis.
- Folder name format: `11 Description`.
- Never save files directly in category folders.

### IDs

- Format `AC.ID`: two digits, decimal point, two digits. `11.23`, `34.01`.
- `.00` through `.99` — 100 per category. With the standard zeros reserved,
  content IDs run `.10`–`.99`.
- An ID is a manila folder: one topic, one container. If it gets busy, split
  it into multiple IDs.
- Folder name format: `11.23 Description`.
- **IDs are where content lives.** All files go inside ID folders.
- Subfolders inside an ID: "sometimes one more level — *and I mean one* —
  makes sense." Do not nest deeper.

---

## AC.ID Notation

`AC.ID` — **A**rea, **C**ategory, **ID**.

- First digit → the area (`1` → `10-19`)
- First two digits → the category (`15` → category 15)
- After the decimal → the item within that category

The notation is also used as a wildcard when talking about the system:
`1C.ID` = anything in area 10-19; `11.ID` = anything in category 11;
`AC.11` = ID `.11` in any category.

### Multiple systems: SYS.AC.ID

With more than one system the notation extends to `SYS.AC.ID`. Each system
lives in its own folder named for its identifier — e.g. `D25 Johnny.Decimal`.

**The official documentation does not specify a format for the `SYS`
prefix**; its worked example is `D25`. A letter-plus-two-digits code is a
reasonable house style **[plugin convention]** — do not tell the user JD
requires it, and never override a prefix scheme they already use.

Rules that *are* documented:

- Inside a single isolated domain, the prefix may be unnecessary in the
  filesystem.
- In any **shared tool** — one JDex covering several systems, for instance —
  always write the full `SYS.AC.ID`.
- For files that get distributed, encode the system identifier in the
  filename so it survives the trip.

---

## The Standard Zeros

Numbers ending in zero are reserved for managing the system rather than for
content. They exist at **three levels**, and the governing rule is:

> **Prefer the most specific zero.** Category-level before area-level,
> area-level before system-level.

### Category level — `.00` to `.09`, in *every* category

| ID | Purpose |
|----|---------|
| `.00` | JDex — the index for this category |
| `.01` | Inbox — temporary holding for things to be filed soon |
| `.02` | Task & project management |
| `.03` | Templates |
| `.04` | Links |
| `.05`–`.08` | Reserved for future expansion — **do not assign your own meanings** |
| `.09` | Archive — kept, but never to be organised |

So `15.01` is the inbox *for category 15*, and `15.09` is category 15's
archive. This is the normal case, not an exotic one.

### Area level — the `x0` category

Each area's `x0` category manages that area: `10 Management of area 10-19`.

### System level — area `00-09`, category `00`

`00.00 JDex` is "the very first ID" — it holds or references the system's
master index.

### Consequences for tooling

- **An inbox is not a single location.** Scan for `*.01 Inbox*` across every
  category, plus the area and system zeros. A processor that only looks at
  `00.01` will silently miss most of what needs filing.
- `.05`–`.08` are reserved. Assigning "Someday", "Needs review", or a
  processing log to them is inventing structure the user's other JD tools
  won't understand. If this plugin needs such a bucket, put it under `.02`
  (task & project management) and say so.

---

## The JDex

The JDex is the master record of every ID in a system, normally kept in a
notes app. **The index _is_ the Johnny.Decimal system.**

### The rule that governs everything else

> **"Your filesystem is not your index."**

Create the JDex note **before** you create the folder. Creating the note *is*
creating the ID; the folder is downstream. Never treat the filesystem as a
co-equal authority — when they disagree, the filesystem is drift to be
reconciled, not a second opinion.

### Structure

**One note per ID**, not one big file. The note title is the index entry:

```
15.55 Japan, 2025
```

The body records:

- **Where the thing actually lives** — and it will be several places: cloud
  storage, email, a hard drive, an app, a calendar, paper. This is the JDex's
  main job in a world where one ID's material is scattered across services.
- **Keywords** to make it findable later.
- **Decisions** — including the "I looked for this here and it wasn't, it's
  actually over there" notes that stop you re-litigating a filing call.

A flat Markdown export of all notes is a fine *artifact* for tooling to read
**[plugin convention]**, but do not tell the user that a single `00.00
JDex.md` file is what a JDex is.

---

## Headers

Headers group similar IDs into sections within a category. They are IDs
ending in `0`, conventionally marked with `■` and an emoji:

```
14.10 ■ Computers & other devices 🖥️
```

**Store nothing in a header** — it is a signpost. Headers suit fixed,
complete, pre-built systems; in a system still being designed they constrain
where new IDs can go, so introduce them only when the shape has settled.

---

## System Expansion

When a system feels tight there are exactly three documented strategies.
Try them in this order.

### 1. Extend the end — `+` (simplest, and therefore preferred)

For an ID that needs to repeat, add `+` after the ID:

```
13.41  Purchase receipts
13.41+ Ozito mower
```

In notes this sorts the child directly below the parent. In the filesystem
the subfolder is named with a leading `+`:

```
13.41 Purchase receipts/
  + Ozito mower/
  + Bosch drill/
  scans/
```

The `+` signals that the folder is not an ordinary subfolder — **it has a
JDex entry.** These sort above normal subfolders.

> **[plugin convention]** — this plugin's other skills use a stricter
> "+SUB" form: `AC.ID+NNNN` (zero-padded sequence) and `AC.ID+CODE` (short
> mnemonic), with index files per category. These are a *house style layered
> on the documented `+`*, useful when there are enough children to want a
> roster. They are not Johnny.Decimal canon. Offer them; don't impose them,
> and read a user's existing `+ Name` folders as valid.

### 2. Expand an area

Redesign **one** area with a custom, deeper structure — for example area
`50-59` using five-digit codes `50000`–`59999`. The hard rule: **all IDs
still start with the area number.**

Guidance for the expanded part: sort alphabetically where there's a natural
name; use `yyyy-mm-dd` dates; stop using numbers as identifiers when
something better exists; follow hierarchies that already exist in the domain
(client → product → job); find the repeating pattern and template it.

> **Only expand the part that needs expanding.** The rest of the system stays
> standard.

### 3. Multiple systems (last resort)

Only when you have two genuinely non-overlapping domains — a personal life
and a work life that share no tools.

> **"Do not use this if you think you have 'filled up' an existing system and
> need more room. Correct your design instead."**

Extending an existing system adds one ID. A new system adds thousands of
empty ones. Before agreeing to a second system, check whether the real
problem is categories that were drawn too narrow.

---

## Naming Files and Subfolders

### Dates

ISO 8601, `yyyy-mm-dd` — "the only date format you should ever use." Shorten
to `yyyy-mm` or `yyyy` when that's the real precision. Never any other order;
it breaks the sort.

A date prefix is a strong default for documents with an inherent date. It is
**not** mandatory for every file — a file whose name is its identity
(`Contract.pdf`, `v3 Cover letter.docx`) does not need one.

### Versions

Pick one position and never move it: `v1 Name.doc` / `v2 Name.doc`, **or**
`Name v1.doc` / `Name v2.doc`.

### The ID in the filename

**Optional.** Worth it when the file gets emailed (the number travels with
it) or when you want to recognise it in a recent-files list. On Windows,
weigh it against path-length limits.

### The actual rule

Ruthless consistency. "As soon as you get lazy the sort breaks." Spacing,
capitalisation, and separators matter more than which scheme you picked.

### Subfolder patterns

Everything has a pattern — find it before inventing one.

- **By date** — `yyyy-mm-dd`, `yyyy-mm`, or `yyyy-ww`.
- **Alphabetical** — by supplier, person, or organisation. Choose first name
  *or* surname *or* org name and apply it uniformly. Bracketed numbers
  (`[01]`, `[02]`) can be appended without breaking the sort.
- **Sequential fallback**, when there's no natural order — number in
  **increments of ten**: `10`, `20`, `30`, leaving room to slot `15` in
  later.

---

## Using the Inbox and the Archive

**Inbox (`.01`)** — a *temporary* holding area. The point is that saving to
an inbox beats saving to the Desktop. Drain it periodically. An inbox that
has stopped draining has become a second Desktop and needs its own pass.

**Archive (`.09`)** — for material you'll keep but will never organise. It is
**"one step away from the trash."** Do not use it to defer filing decisions,
and throw things away sometimes.

---

## Core Philosophy

1. **Decide and document.** When something could go two places, pick one and
   record it in the JDex. Ambiguity is resolved by the index, not by a
   deeper hierarchy.
2. **Compression over granularity.** Fewer, broader categories. Every extra
   choice is a chance to hesitate.
3. **Nothing in area or category folders.** A file found at those levels
   needs a home in an ID.
4. **"The goal is to reduce mental burden. It is not to use up all the
   numbers."** Don't create IDs to fill gaps; create them when content needs
   a home. Equally, don't fear the numbers — they're an address, not a
   filing fee.
