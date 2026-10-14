---
name: jd-number-category
description: >
  Give the loose folders and files inside one Johnny.Decimal category real
  IDs: survey the category, propose a numbering, find what a rename would
  break, apply it with a receipt that can be reversed, and update the JDex.
  Use when a category has grown named subfolders and loose files instead of
  IDs, or the user says "number this category," "give these folders IDs,"
  "clean up 34," "the JDex falls apart below the categories," or "adopt JD
  inside this folder."
---

# Number a Johnny.Decimal category

Systems built by migrating an existing folder tree usually get their areas and
categories right and then stop. Inside each category sit named folders
(`Policy`, `Policy Briefs`, `Research`), loose files and leftovers from the
migration (`_from-paper`, `_old`). This skill turns one such category into IDs
without losing anything and without breaking the tools and notes that point
into it.

Before doing anything, read
`../jd-inbox-processor/references/jd-system-rules.md`, the plugin's single
source of Johnny.Decimal canon. It marks which conventions come from
<https://johnnydecimal.com/documentation> and which are this plugin's own
house style.

The helper is `scripts/category_plan.py`. Every subcommand is read-only
except `apply --execute`, `reverse --execute` and `relink --execute`.

---

## 0. Ground rules

- **Nothing moves without the person's approval of the written plan**, one
  category at a time. A person may approve 21 and hold 85.
- **Nothing is deleted.** Merging two folders moves the contents and leaves
  the emptied folder for the person to remove. Empty folders, duplicates and
  stubs go on a list for them.
- **Shared and synced folders.** On Dropbox, Google Drive or OneDrive, moving a
  whole shared folder is safe, but moving files *out* of a shared folder
  removes them for every other member. Ask before doing that, and copy rather
  than move when unsure.
- **Live work waits.** If anything in the category changed in the last day,
  or an app keeps a project open there (Scrivener, an IDE, a running job),
  schedule the apply for a quiet moment and say so.
- **Choose which categories to number.** Not every category needs IDs. A
  reading shelf of 300 PDFs is a working pile that the person browses, and
  numbering it adds nothing. Number the categories where people file and
  retrieve things by topic.

## 1. Survey

```
python scripts/category_plan.py survey "<root>/30-39 Programs/34 Open City Advocates"
```

One line per entry: kind, name, file count, MB, newest change. Read it for:

- **Near-duplicates** to merge (`SHA` and `SHA Documents`, `LOC sources` and
  `Library of Congress`).
- **Loose files** that belong with a folder, or together as a new ID.
- **Tool data** (`.apodictic`, `_scrivener-config`, `.ynabSettings.yroot`):
  data an app expects to find at a fixed path. Leave it where it is or give it
  `.03 Templates`, and never rename it inside an app's own folder.
- **Leftovers** (`_from-paper`, `_old`, `Test`, `drafts`): open them. `Test`
  is often something real that was misnamed.
- **Recent changes**, which tell you whether the category is live.

## 2. Propose IDs

Write the proposal as a table the person can approve line by line:

| ID | Name | Gets |
|---|---|---|
| 71.01 | Inbox | |
| 71.09 | Archive | Before 2002 |
| 71.10 | Taxes | Tax records; 2020 Form 1040; W-2 2022 |
| 71.18 | SHA | merges `SHA` and `SHA Documents` |

Rules for the proposal:

- Every numbered category gets `.01 Inbox`, so new material stops landing
  loose. Add `.03 Templates` or `.09 Archive` only when there is material for
  them. Leave `.05`–`.08` empty.
- Content IDs start at `.10`. Order them alphabetically when names are
  natural (courses, manuscripts), or by how often the person reaches for
  them. Don't invent headers in a system that is still settling.
- An existing ID keeps its number. Fit new IDs around it.
- A folder becomes its ID by renaming (`Policy` → `34.10 Policy & testimony`).
  Its contents stay as they are. Don't restructure inside the ID in the same
  pass; nesting deeper than ID-plus-one is a separate finding for later.
- Mark every guess with **?** and ask. A file you couldn't identify gets a
  **?**, not a home.
- Keep the person's spelling unless they ask for cleanup. A rename that also
  fixes underscores doubles what has to be relinked.

## 3. Find what a rename breaks

```
python scripts/category_plan.py refs "<category>" \
    --scan "<root>/CLAUDE.md" --scan "<root>/00-09 System/00 System/00.00 JDex.md"
```

`refs` counts, for each entry in the category, the text files that mention
its name: Markdown, JSON, YAML, CSV, code. It always scans the category
itself; add the JDex, the root agent instructions, tool registries and any
pipeline folder with `--scan`. Short common names (`SHA`, `Test`) match prose
too, so read the hits before counting them.

What the hits mean:

| Hit | Action |
|---|---|
| JDex links | Relink in the same step (section 5). |
| Agent instructions, READMEs | Relink, then check the result reads correctly. |
| A tool's registry or config (`registry.json`, `settings.yaml`) | Relink only with the tool closed; note it on the plan. |
| A data index with thousands of paths (a corpus index, a catalog) | Give the IDs in the JDex now and hold the renames for the next session that rewrites that index. Say so on the plan. |
| Historical receipts and logs | Leave them. They record what was true then. |

## 4. Apply with a receipt

Turn the approved table into a plan file, one move per line,
`SOURCE<TAB>DESTINATION`, relative to the category:

```
# 71 Finance, approved 2026-10-14
SHA	71.18 SHA
SHA Documents/*	71.18 SHA
Retirement	71.13 Investments & retirement/Retirement
W-2 2022.pdf	71.10 Taxes/W-2 2022.pdf
```

`SOURCE/*` moves every child of `SOURCE` into `DESTINATION/` (a merge).
Destination folders that don't exist yet are created.

```
python scripts/category_plan.py apply "<category>" plan.tsv
python scripts/category_plan.py apply "<category>" plan.tsv --execute --receipt receipt.tsv
```

The first run only checks the plan. It checks each move against the tree as
the earlier moves in the plan will leave it, so a merge into a folder that an
earlier line renamed is caught when two files share a name. It reports missing
sources, destinations that would already exist and folders moved into
themselves. Fix every problem before executing. The executed run renames with
no-replace semantics, stops at the first failure and writes each completed
move to the receipt as it goes, so a half-finished apply is still reversible. Keep the plan and receipt with the system's other reorganization
records, outside the category.

To undo:

```
python scripts/category_plan.py reverse "<category>" receipt.tsv            # check
python scripts/category_plan.py reverse "<category>" receipt.tsv --execute
```

Folders the apply created are left in place, empty, for the person to remove.

## 5. Update the JDex and other references

```
python scripts/category_plan.py relink "<category>" receipt.tsv "<JDex>" "<root>/CLAUDE.md"
python scripts/category_plan.py relink "<category>" receipt.tsv "<JDex>" "<root>/CLAUDE.md" \
    --execute --backup-dir "<reorg records>/before-relink"
```

`relink` rewrites each moved path in plain, %-encoded and backslash forms,
anchored on the category folder name so prose isn't touched. A match must
end a whole path component (a separator, a closing link bracket, a quote or
the end of the line), so renaming `SHA` never touches `SHA Documents`. Each
original goes to the backup folder under its own full path, and nothing is
rewritten if a backup of that file is already there. Use `--bare` for
files that hold paths relative to the category. The dry run prints a count per
file; a count of zero for a file that `refs` said mentions the category means
the paths are written some other way, so edit that file by hand.

Then write the JDex entries:

- One entry per new ID, with its name and what it holds. In a one-note-per-ID
  JDex, create the notes. In a single-file JDex link tree, add a linked line
  under the category.
- Record merges ("71.18 SHA: merged `SHA Documents` 2026-10-14") so nobody
  looks for the old name later.
- Remove the entries for folders that no longer exist.

## 6. Verify

Run the audit's checker against the root with the JDex and the last baseline:

```
python ../jd-jdex-audit/scripts/structural_check.py "<root>" \
    --jdex "<JDex>" --baseline "<last baseline>"
```

Expect the category's `unnumbered-folder-in-category`, `unindexed-folder` and
`no-category-inbox` findings under **gone**, and nothing new except what the
plan deliberately left (tool data, held renames). Save the new full output as
the next baseline.

Report to the person: what moved (count and receipt path), what was relinked,
what's waiting on them (empty folders to remove, **?** items, held renames).
