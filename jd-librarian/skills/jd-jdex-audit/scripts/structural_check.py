#!/usr/bin/env python3
"""Structural conformance check for a Johnny.Decimal tree.

Implements the checks in SKILL.md section 2.4. Read-only: reports, never fixes.
Run before any JDex/filesystem diff -- a diff is meaningless over a tree that
has collisions in it.

Usage:  python structural_check.py <system-root> [--jdex FILE]
                                   [--baseline FILE] [--tsv]

  --jdex FILE      also compare a single-file JDex (a Markdown link tree) with
                   the disk: links that point nowhere, and categories or
                   folders inside categories that no link names (SKILL.md 1.2b)
  --baseline FILE  report only findings missing from an earlier run's output
                   (either format), plus the baseline findings now gone
  --tsv            print SEVERITY<TAB>kind<TAB>path<TAB>detail, one per line

Exit:   0 clean (or nothing new), 1 findings, 2 bad invocation.
"""
import argparse
import os
import re
import sys
from urllib.parse import unquote

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

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def jdex_links(jdex):
    """Yield (line number, resolved path) for each local link in the JDex."""
    base = os.path.dirname(os.path.abspath(jdex))
    with open(jdex, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            for target in LINK.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) \
                        or target.startswith("#"):
                    continue      # web, mailto, obsidian:// or same-file anchor
                target = unquote(target.split("#", 1)[0])
                yield n, os.path.normpath(os.path.join(base, target))


def check_jdex(root, jdex):
    """Compare a single-file JDex link tree with the top three levels on disk.

    An entry with no link (plain or bold text) records material held
    somewhere other than this tree and is never a finding (SKILL.md 2.1).
    """
    findings = []
    root = os.path.abspath(root)
    linked = set()
    for n, path in jdex_links(jdex):
        linked.add(path)
        if not os.path.exists(path):
            findings.append(("MEDIUM", "jdex-broken-link",
                             os.path.relpath(path, root),
                             f"JDex line {n} points at nothing"))

    def unindexed(path, what):
        if path not in linked:
            findings.append(("MEDIUM", "unindexed-folder",
                             os.path.relpath(path, root),
                             f"{what} with no JDex link; write the entry"))

    for area in areas(root):
        apath = os.path.join(root, area)
        for cat in sorted(os.listdir(apath)):
            cpath = os.path.join(apath, cat)
            if not os.path.isdir(cpath) or cat.startswith("."):
                continue
            unindexed(cpath, "category" if CATEGORY.match(cat)
                      else "unnumbered folder")
            if not CATEGORY.match(cat):
                continue
            for name in sorted(os.listdir(cpath)):
                full = os.path.join(cpath, name)
                if os.path.isdir(full) and not name.startswith("."):
                    unindexed(full, "ID" if ID_FOLDER.match(name)
                              else "folder in a category")
    return findings


def load_baseline(path):
    """Read (kind, path) keys from an earlier run, in TSV or report format."""
    keys = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            fields = line.split("\t")
            if len(fields) == 4 and fields[0] in ORDER:
                keys.add((fields[1], fields[2]))
            elif line.startswith("  ") and not line.strip().startswith("->"):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    keys.add((parts[0], parts[1]))
    return keys


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("root", nargs="?")
    ap.add_argument("--jdex")
    ap.add_argument("--baseline")
    ap.add_argument("--tsv", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    args, extra = ap.parse_known_args()
    if args.help or extra or not args.root:
        print(__doc__, file=sys.stderr)
        return 2
    root = args.root
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    for opt in (args.jdex, args.baseline):
        if opt and not os.path.isfile(opt):
            print(f"not a file: {opt}", file=sys.stderr)
            return 2

    findings = check(root)
    if args.jdex:
        findings += check_jdex(root, args.jdex)
    findings = sorted(findings, key=lambda f: (ORDER[f[0]], f[1], f[2]))

    gone = []
    if args.baseline:
        before = load_baseline(args.baseline)
        now = {(f[1], f[2]) for f in findings}
        gone = sorted(before - now)
        known = len([f for f in findings if (f[1], f[2]) in before])
        findings = [f for f in findings if (f[1], f[2]) not in before]

    if args.tsv:
        for f in findings:
            print("\t".join(f))
        return 1 if findings else 0

    if args.baseline:
        print(f"Baseline: {args.baseline}\n{len(findings)} new, {known} "
              f"unchanged, {len(gone)} gone since the baseline.")
        for kind, path in gone:
            print(f"  gone  {kind}  {path}")
    if not findings:
        print("No new findings." if args.baseline
              else "No structural violations found.")
        return 0

    width = max(len(f[1]) for f in findings)
    current = None
    for sev, kind, path, detail in findings:
        if sev != current:
            print(f"\n{sev}")
            current = sev
        print(f"  {kind:<{width}}  {path}")
        print(f"  {'':<{width}}  -> {detail}")
    print(f"\n{len(findings)} {'new ' if args.baseline else ''}finding(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
