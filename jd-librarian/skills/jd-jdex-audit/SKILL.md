---
name: jd-jdex-audit
description: >
  Audit a Johnny.Decimal system by comparing the JDex against the actual
  folder structure, flagging mismatches, orphaned entries, and undocumented
  folders. Use this skill when the user wants to verify their JD system,
  check for inconsistencies, sync their JDex with the filesystem, or says
  things like "audit my JDex," "check my system," "sync JDex," "verify my
  JD system," "is my JDex up to date," or "find orphaned folders."
---

# Johnny.Decimal JDex Audit

This skill compares a system's JDex (the authoritative index) against the
actual folder structure on disk, identifying mismatches and suggesting fixes.

Before doing anything, read
`../jd-inbox-processor/references/jd-system-rules.md` — the plugin's single
source of Johnny.Decimal canon. It marks which conventions come from
<https://johnnydecimal.com/documentation> and which are this plugin's own
house style, so you never present a house rule to the user as a rule of JD.


---

## 1. Locate the System

### 1.1 Find the JD Root

Check common locations:

- `~/Library/Mobile Documents/com~apple~CloudDocs/JD/` (iCloud Drive, macOS)
- `~/Documents/JD/`
- `~/JD/`
- `~/Dropbox/` and `~/OneDrive/` — including the **case where the sync root
  *is* the JD system**, i.e. numbered area folders sit directly at the root
  rather than under a `JD/` subfolder
- On Windows, the same under `%USERPROFILE%`, plus non-`C:` drives
  (`D:\Dropbox\`, `D:\JD\`)

**Detect by shape, not by name.** A JD root is any directory containing two
or more immediate children matching `^\d0-\d9 ` (e.g. `10-19 Scholarship`).
Prefer that test over the path list above; the list is only a place to start
looking. A system that grew by migrating an existing cloud folder will never
be named `JD`.

If the user specifies a system code (e.g., "audit my P10 system"), target
that specific system. Otherwise, list all available systems and ask which
to audit.

### 1.2 Load the JDex

Read the JDex file at:

```
SYS/00-09 */00 */00.00 *JDex*
```

Parse it into a structured list of areas, categories, and IDs. Each entry
should capture:

- The AC.ID (or SYS.AC.ID) address
- The description/name
- Any +SUB entries

### 1.3 Snapshot the Filesystem

List all folders to depth 3 under the system root. Parse folder names to
extract AC.ID addresses, area ranges, and category numbers.

---

## 2. Compare JDex vs. Filesystem

**The two sides are not symmetric.** The JDex is the system; the filesystem
is one of several places an ID's material happens to live. So the two
directions of mismatch mean very different things, and only one of them is a
defect by default.

### 2.1 JDex Entries With No Folder — usually *not* an error

An ID can legitimately name material that has no folder at all: something
held in email, on paper, in a SaaS app, on another machine, or an ID reserved
before its content exists. If the entry records a non-filesystem location,
**it is correct and must not be flagged or deleted.**

Report as a finding only when the entry claims a filesystem location that
isn't there. Then it means:
- a folder was deleted or moved without updating the JDex, or
- a typo in the recorded path.

Never offer "delete the JDex entry" as the first fix. The entry is the ID.

### 2.2 Undocumented Folders — always a defect

Folders on disk with no JDex entry. This *is* an error every time, because
the folder was created without the ID being created:

- created directly in the filesystem, skipping the index
- the JDex fell out of sync during manual reorganisation
- created by another tool

The fix direction is always the same: **write the JDex entry**, don't delete
the folder.

### 2.3 Name Mismatches

JDex entries whose description doesn't match the folder name, or folders
whose name doesn't follow the expected `AC.ID Description` format.

### 2.4 Structural Violations

Independent of the JDex, check the tree itself. These are the failures that
show up in systems built by migrating an existing folder hierarchy, and they
compound if left alone:

| Check | Why it matters |
|---|---|
| **Duplicate category numbers** — two folders starting with the same two digits in one area | An ID must be unique. `22 Materials` + `22 Teaching Materials` means `22.01` is ambiguous. Highest severity; fix before filing anything new. |
| **Unnumbered folders inside a numbered area** — `_from-paper/`, `_review/` | Material that entered the system without getting an address. Each is a filing decision that was deferred and then forgotten. |
| **Files at area or category level** | Content must live in an ID. |
| **More than ten categories in an area** | The area is over capacity; the design needs correcting, not a workaround. |
| **Depth beyond ID + one subfolder** | Three levels, then at most one more. Deeper nesting is the hierarchy the numbers were meant to replace. |
| **A category with no `.01` inbox but a busy system inbox** | Capture is defaulting to the least specific zero. |
| **Numbered folders with zero files** | Either a reservation (fine, if the JDex says so) or migration residue (delete). |

Report these first — a JDex/filesystem diff is not meaningful over a tree
that has collisions in it.

---

## 3. Check +SUB Indexes

For categories that use +SUB extensions:

### 3.1 Locate Index Files

+SUB categories typically have an index file (e.g., `51.01 Open-source project
index.md`). Find these by looking for files matching `*.md` at the category
or ID level that contain +SUB listings.

### 3.2 Compare Index vs. Folders

- List all `+NNNN` or `+CODE` folders within the ID
- Compare against the index file entries
- Flag missing or extra entries

---

## 4. Report Findings

Present a clear audit report to the user:

### Report Format

```markdown
## JDex Audit: [System name]

**Audit date:** YYYY-MM-DD
**JDex location:** [path]
**System root:** [path]

### Summary

| Check | Count |
|-------|-------|
| JDex entries | N |
| Filesystem folders | N |
| Orphaned JDex entries | N |
| Undocumented folders | N |
| Name mismatches | N |
| +SUB index issues | N |

### Orphaned JDex Entries (in JDex but no folder)

| AC.ID | Description | Suggested Action |
|-------|-------------|-----------------|
| 11.05 | Home improvement | Create folder or remove from JDex |

### Undocumented Folders (folder exists but not in JDex)

| Folder | Path | Suggested Action |
|--------|------|-----------------|
| 11.08 Garage storage | 10-19/11/11.08 | Add to JDex |

### Name Mismatches

| AC.ID | JDex says | Folder says | Suggested Action |
|-------|-----------|-------------|-----------------|
| 11.03 | Home insurance | Homeowners insurance | Reconcile names |

### +SUB Index Issues

| Category | Issue | Details |
|----------|-------|---------|
| 51.01 | Missing from index | +0004 folder exists, not in index |
```

---

## 5. Offer Fixes

After presenting the report, offer to fix issues:

### Safe Fixes (do automatically with confirmation)

- **Add undocumented folders to JDex**: Append new entries matching the
  folder names.
- **Update +SUB index files**: Add missing entries to index files.

### Requires User Decision

- **Orphaned JDex entries**: Ask whether to create the missing folder or
  remove the JDex entry.
- **Name mismatches**: Ask which name is correct (JDex or folder) and
  update the other.

### Never Do Automatically

- **Delete folders**: Even if they appear orphaned, never delete without
  explicit user confirmation.
- **Rename folders**: Name changes can break references. Always confirm first.
- **Create new areas or categories**: These are structural decisions.

---

## 6. Regenerate JDex (Optional)

If the user requests it, offer to regenerate the JDex entirely from the
folder structure:

1. Walk the filesystem and build a complete list of areas, categories, and IDs.
2. Preserve any JDex-only metadata (cross-system references, notes, +SUB
   descriptions) from the existing JDex.
3. Write the new JDex, merging filesystem reality with JDex metadata.
4. Present the result for user approval before overwriting.

**Warning**: Regeneration loses any JDex entries that don't have corresponding
folders. Always confirm before proceeding.

---

## 7. Multi-System Audit

When auditing multiple systems:

1. Audit each system independently.
2. Present per-system reports.
3. Optionally check cross-system references: if P10.34.01 is referenced by
   F50.32.01, verify that both the source and the reference exist.
4. Provide a combined summary at the end.
