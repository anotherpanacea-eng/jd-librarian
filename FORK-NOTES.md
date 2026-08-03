# Fork notes

Fork of [ngerakines/jd](https://github.com/ngerakines/jd) (Apache-2.0),
reconciled against the official Johnny.Decimal documentation at
<https://johnnydecimal.com/documentation>.

Upstream is a good scaffold — the skill decomposition, the trigger phrasing,
and the jdtodo.txt work are all sound, and this fork keeps them. What it got
wrong is the model of Johnny.Decimal itself, in ways that made the tooling
quietly incorrect on a real system. Every change below is a conformance fix,
not a preference.

## The eight substantive corrections

### 1. Standard zeros exist at three levels, not one

Upstream put the zeros only at the system level (`00.00`–`00.09`) and called
category-level zeros "less common." The documentation says the opposite: the
zeros are standard in **every category**, and the governing rule is
**"prefer the most specific zero."** `15.01` is the inbox for category 15;
`00.01` is the least specific inbox in the system, not the only one.

### 2. The inbox processor looked in one place

Following from (1): upstream globbed `SYS/00-09 */00 */00.01 Inbox/` and
processed that. On a system using category inboxes it would report "inbox
empty" while most of the unfiled material sat in `15.01`, `24.01`, `31.01`.
Now scans `**/*.01 Inbox*`.

### 3. `.05`–`.08` are reserved, and upstream was assigning them

`00.08 Someday` and `00.04 Needs review` were invented. `.04` is **Links**;
`.05`–`.08` are **reserved for future expansion** by the spec. Someday-lists
and review queues are task management, so they now live as files under
`.02 Task & project management`. The migration is called out where a system
built the old way is detected.

### 4. The area-management category `x0` was missing entirely

Upstream described categories as running `11`–`19` within area `10-19`,
dropping `10`. But `x0` is a real category — "Management of area 10-19" — and
it's where area-level material belongs. Its absence is why systems built on
this plugin end up with unnumbered `_admin` folders inside areas.

### 5. The JDex was modelled backwards

Upstream: "the JDex is authoritative for what *should* exist; the filesystem
is authoritative for what *does* exist." That is a both-sides fudge, and it
legitimises exactly the drift the JDex exists to prevent. The documentation
is unambiguous:

> **"Your filesystem is not your index."**

You create the note **before** the folder; creating the note *is* creating the
ID. Consequences now encoded:

- **One note per ID**, not a single `00.00 JDex.md`. That file is a flat
  *export* for tooling to read, and is generated from the real index — never
  the place the user edits.
- An entry records **where the thing actually lives**, across cloud storage,
  email, apps, other machines, and paper — plus keywords and decisions. This
  is the JDex's actual job; a one-line description isn't a JDex.
- **A JDex entry with no folder is usually correct**, because the ID may name
  material that lives only in email or on paper. The audit skill listed these
  as "orphaned entries" and offered deletion as a fix. It no longer does.
- A folder with no JDex entry is *always* a defect, and the fix is always to
  write the entry.

### 6. `+SUB` was presented as canon; it isn't

The documented mechanism is **"extend the end"**: `13.41+ Ozito mower`, and in
the filesystem a subfolder named `+ Ozito mower/`, which sorts above ordinary
subfolders and signals that it has its own JDex entry. It is the simplest and
most preferred of the three expansion strategies.

Upstream's `AC.ID+NNNN` / `AC.ID+CODE` scheme, its index files, and its
"20+ items" threshold appear nowhere in the documentation. They're a
reasonable house style and the fork keeps them — now labelled
**[plugin convention]**, layered explicitly on the documented `+`, with an
instruction to treat a user's existing `+ Name` folders as already correct.

### 7. System expansion and headers were absent

Added: the three expansion strategies in preference order (extend the end →
expand an area → multiple systems), and the hard rule that governs the last
one:

> "Do not use this if you think you have 'filled up' an existing system and
> need more room. Correct your design instead."

Also added headers (`14.10 ■ Computers & other devices 🖥️` — IDs ending in
zero, holding nothing) and the caution that they suit finished systems and
constrain systems still being designed.

Corrected alongside: the `SYS` prefix format. Upstream stated `[A-Z][0-9][0-9]`
and "2,600 possible system codes" as fact; the documentation specifies no
format at all, and its worked example is `D25`.

### 8. Root discovery assumed macOS and a folder called `JD`

Three hardcoded paths, all under `$HOME`, one of them iCloud-specific. Added
Dropbox and OneDrive roots, Windows and non-`C:` drives, and — more usefully —
a **detect-by-shape** rule: a JD root is any directory with two or more
immediate children matching `^\d0-\d9 `. A system that grew by migrating an
existing cloud folder is never called `JD`, and that is the common case for
anyone adopting JD onto material they already have.

## Also added

**Structural violation checks in `jd-jdex-audit`** (§2.4). A JDex-versus-
filesystem diff is not meaningful over a tree that has collisions in it, so
the audit now checks the tree first: duplicate category numbers, unnumbered
folders inside numbered areas, files at area or category level, areas over ten
categories, nesting past ID-plus-one, empty numbered folders, and categories
with no `.01` inbox while the system inbox is overflowing. These are the
failure modes of a JD system built by migrating an existing hierarchy, which
is how most real ones start.

**A canon pointer in every skill.** All six now read
`jd-inbox-processor/references/jd-system-rules.md` before acting. That file
was rewritten from the documentation and marks every house convention as
**[plugin convention]**, so a skill can't present one to the user as a rule of
Johnny.Decimal.

## Not changed

The jdtodo.txt specification, the task manager, and the next-action dashboard
are upstream's own design on top of todo.txt. They aren't Johnny.Decimal
features and aren't claimed to be. Left alone apart from the root-discovery
and standard-zero fixes that touch them.

## Upstreaming

These are conformance fixes, not taste, so most should go back. Reasonable
PR order: (1) the rewritten rules reference, (2) the standard-zeros and inbox
discovery fixes, (3) the JDex direction fix in the audit, (4) root discovery.
The `+SUB` relabelling is the one that's arguably a judgement call, since it
changes how the maintainer's own convention is framed.
