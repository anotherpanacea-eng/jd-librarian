---
description: Process items in a Johnny.Decimal inbox — classify, file, extract tasks, and log actions
argument-hint: "[system-code]"
allowed-tools: [Read, Glob, Grep, Bash, Write]
---

# Process Johnny.Decimal Inbox

Process items in a Johnny.Decimal system's inboxes. `.01` is a standard zero
in **every** category, so a system has many inboxes — `15.01`, `24.01`,
`00.01` — and the rule is to prefer the most specific one. Each item is read,
classified against the JDex, and moved to the correct ID.

## Arguments

`$ARGUMENTS` may contain a system code (e.g., `P10`), or a category number
(e.g., `15`) to drain one category's inbox. If no argument is provided,
discover every inbox across every system, report counts per inbox, and ask
which to process. Always say what you are *not* touching, so a full inbox
elsewhere doesn't stay invisible.

## Workflow

1. **Discover** the JD root and available systems.
2. **Load** the target system's JDex and folder structure.
3. **List** every inbox found (`**/*.01 Inbox*`) with item count, types, and
   date range — not just `00.01`.
4. **Classify** each item using the JDex as the primary reference.
5. **File** items to their destination ID folders with date-prefix naming.
6. **Extract** tasks from items that contain action items.
7. **Log** every action to `00.02 Tasks/processing-log.md`. (Not `00.03` —
   that standard zero is Templates.)
8. **Summarize** what was processed, filed, and flagged.

## Classification Confidence

- **High confidence**: File without asking.
- **Medium confidence**: Recommend a destination and ask the user to confirm.
- **Low confidence**: Present 2–3 candidate locations and ask the user to choose.

## Batch Mode

For inboxes with many items, present a table of proposed filings and let the
user approve, modify, or flag specific items before executing.

## Examples

```
/jd-librarian:process-inbox
/jd-librarian:process-inbox P10
/jd-librarian:process-inbox W20
```
