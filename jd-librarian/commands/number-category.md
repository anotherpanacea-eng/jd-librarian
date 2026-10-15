---
description: Give the folders and loose files inside one Johnny.Decimal category real IDs, reversibly
argument-hint: "<category path or AC number>"
allowed-tools: [Read, Glob, Grep, Bash, Write]
---

# Number a category

Turn one category's named subfolders and loose files into IDs, following the
`jd-number-category` skill.

## Arguments

`$ARGUMENTS` names the category, as a path or a two-digit category number
(e.g. `71`). If it is missing, run the audit's checker and offer the
categories with the most unnumbered folders and loose files.

## Workflow

1. **Survey** the category with `category_plan.py survey`.
2. **Propose** IDs as a table (`.01 Inbox`, content from `.10`), marking
   guesses with **?**. Stop here until the person approves.
3. **Check references** with `category_plan.py refs`, scanning the JDex, root
   agent instructions and any tool registries.
4. **Apply** the approved plan: dry run, then `--execute` with a receipt.
5. **Relink** the JDex and other references from the receipt, then write the
   JDex entries for the new IDs.
6. **Verify** with `structural_check.py --jdex --baseline`, and save the new
   baseline.

## Never

- Move anything before the person approves the plan for that category.
- Delete anything. Emptied folders and duplicates go on a list for the person.
- Move files out of a shared folder without asking.

## Examples

```
/jd-librarian:number-category 71
/jd-librarian:number-category "30-39 Programs/34 Open City Advocates"
```
