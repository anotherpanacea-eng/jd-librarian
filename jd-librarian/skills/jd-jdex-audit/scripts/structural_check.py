#!/usr/bin/env python3
"""Structural conformance check for a Johnny.Decimal tree.

Implements the checks in SKILL.md section 2.4. Read-only: reports, never fixes.
Run before any JDex/filesystem diff -- a diff is meaningless over a tree that
has collisions in it.

Usage:  python structural_check.py <system-root>
Exit:   0 clean, 1 findings, 2 bad invocation.
"""
import os
import re
import sys

AREA = re.compile(r"^(\d)0-\1?9 .+|^(\d)0-(\d)9 .+")
AREA_SIMPLE = re.compile(r"^(\d)0-(\d)9 ")
CATEGORY = re.compile(r"^(\d{2}) ")
ID_FOLDER = re.compile(r"^(\d{2})\.(\d{2})[ +]")


def areas(root):
    for name in sorted(os.listdir(root)):
        if AREA_SIMPLE.match(name) and os.path.isdir(os.path.join(root, name)):
            yield name


def check(root):
    findings = []

    def add(sev, kind, path, detail):
        findings.append((sev, kind, path, detail))

    area_names = list(areas(root))
    if len(area_names) < 2:
        print(f"warning: only {len(area_names)} area folder(s) under {root!r} "
              f"-- is this a JD root?", file=sys.stderr)

    for area in area_names:
        apath = os.path.join(root, area)
        digit = AREA_SIMPLE.match(area).group(1)
        seen = {}
        cats = []

        for name in sorted(os.listdir(apath)):
            full = os.path.join(apath, name)
            if not os.path.isdir(full):
                add("HIGH", "file-at-area-level", f"{area}/{name}",
                    "content must live in an ID")
                continue
            m = CATEGORY.match(name)
            if not m:
                add("HIGH", "unnumbered-folder-in-area", f"{area}/{name}",
                    "material with no address; belongs in an ID or the "
                    f"{digit}0 area inbox")
                continue
            num = m.group(1)
            cats.append(num)
            if num in seen:
                add("CRITICAL", "duplicate-category", f"{area}/{name}",
                    f"collides with {seen[num]!r} -- {num}.xx is ambiguous")
            else:
                seen[num] = name

            check_category(full, f"{area}/{name}", num, add)

        if len(set(cats)) > 10:
            add("HIGH", "area-over-capacity", area,
                f"{len(set(cats))} categories; maximum is 10")
        if cats and f"{digit}0" not in set(cats):
            add("LOW", "no-area-management-category", area,
                f"missing {digit}0 -- area-level material has nowhere to go")

    return findings


def check_category(cpath, label, catnum, add):
    ids, has_inbox, entries = [], False, 0
    for name in sorted(os.listdir(cpath)):
        full = os.path.join(cpath, name)
        entries += 1
        if not os.path.isdir(full):
            if ID_FOLDER.match(name) or re.match(r"^\d{2}\.0\d[ .]", name):
                continue          # a standard zero kept as a file, e.g. 00.00 JDex.md
            add("HIGH", "file-at-category-level", f"{label}/{name}",
                "content must live in an ID")
            continue
        m = ID_FOLDER.match(name)
        if not m:
            add("MEDIUM", "unnumbered-folder-in-category", f"{label}/{name}",
                "not an ID")
            continue
        if m.group(1) != catnum:
            add("HIGH", "id-outside-category", f"{label}/{name}",
                f"ID starts {m.group(1)} but sits in category {catnum}")
        seq = m.group(2)
        ids.append(seq)
        if seq == "01":
            has_inbox = True
        if seq in ZEROS:
            meaning, keywords = ZEROS[seq]
            if keywords and any(k in name.lower() for k in keywords):
                pass              # correctly used standard zero
            elif not keywords:
                add("HIGH", "id-in-reserved-range", f"{label}/{name}",
                    f".{seq} is {meaning}; leave it empty")
            else:
                add("HIGH", "id-in-standard-zero-range", f"{label}/{name}",
                    f".{seq} is {meaning}; content IDs start at .10")

        depth_scan(full, f"{label}/{name}", add)

        if not any(os.scandir(full)):
            add("LOW", "empty-id", f"{label}/{name}",
                "reservation, or migration residue")

    if entries and not has_inbox:
        add("INFO", "no-category-inbox", label,
            f"no {catnum}.01 -- capture defaults to the least specific zero")


def depth_scan(idpath, label, add):
    """An ID may hold at most one level of subfolders."""
    for entry in os.scandir(idpath):
        if not entry.is_dir():
            continue
        for sub in os.scandir(entry.path):
            if sub.is_dir():
                add("MEDIUM", "nesting-past-id-plus-one",
                    f"{label}/{entry.name}/{sub.name}",
                    "IDs allow one level of subfolders, and I mean one")
                return


ZEROS = {
    "00": ("JDex", ("jdex", "index")),
    "01": ("Inbox", ("inbox",)),
    "02": ("Task & project management", ("task", "project", "todo")),
    "03": ("Templates", ("template",)),
    "04": ("Links", ("link",)),
    "05": ("reserved for future expansion", ()),
    "06": ("reserved for future expansion", ()),
    "07": ("reserved for future expansion", ()),
    "08": ("reserved for future expansion", ()),
    "09": ("Archive", ("archive",)),
}

ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    findings = sorted(check(root), key=lambda f: (ORDER[f[0]], f[1], f[2]))
    if not findings:
        print("No structural violations found.")
        return 0

    width = max(len(f[1]) for f in findings)
    current = None
    for sev, kind, path, detail in findings:
        if sev != current:
            print(f"\n{sev}")
            current = sev
        print(f"  {kind:<{width}}  {path}")
        print(f"  {'':<{width}}  -> {detail}")
    print(f"\n{len(findings)} finding(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
