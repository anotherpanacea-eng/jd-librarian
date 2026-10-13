#!/usr/bin/env python3
"""Number the folders inside one Johnny.Decimal category, reversibly.

Subcommands (see ../SKILL.md for the workflow around them):

  survey CATEGORY
      One TSV line per entry: kind, name, files, MB, newest change.
  refs CATEGORY [--scan PATH ...] [--max-mb N]
      Text files that mention each entry's name, so you know what a rename
      breaks. Scans the category itself plus any --scan files or folders.
  apply CATEGORY PLAN [--execute] [--receipt FILE]
      PLAN lines are SOURCE<TAB>DESTINATION, relative to CATEGORY; a line
      starting with '#' is a comment. 'SOURCE/*' moves every child of SOURCE into DESTINATION/.
      Missing destination folders are created. Without --execute it only
      checks the plan. Never overwrites; stops at the first failure. The
      receipt goes to --receipt, or the current folder (not the category).
  reverse CATEGORY RECEIPT [--execute]
      Undo an apply, newest move first. Folders the apply created are left
      in place (empty) for a person to remove.
  relink CATEGORY RECEIPT FILE ... [--execute --backup-dir DIR] [--bare]
      Rewrite paths the apply changed inside text files (a JDex, CLAUDE.md,
      a tool registry), in plain, %-encoded and backslash forms. Paths are
      matched with the category folder name in front unless --bare.

Exit: 0 ok, 1 problems found or a step failed, 2 bad invocation.
"""
import argparse
import os
import re
import shutil
import sys
import time
from urllib.parse import quote

TEXT = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv", ".tsv",
        ".html", ".htm", ".xml", ".ini", ".cfg", ".py", ".js", ".ts", ".sh"}


def survey(cat):
    for e in sorted(os.scandir(cat), key=lambda e: e.name.lower()):
        if e.is_dir():
            n, size, newest = 0, 0, 0
            for root, _, files in os.walk(e.path):
                for f in files:
                    try:
                        st = os.stat(os.path.join(root, f))
                    except OSError:
                        continue
                    n, size = n + 1, size + st.st_size
                    newest = max(newest, st.st_mtime)
            kind = "dir"
        else:
            st = e.stat()
            n, size, newest, kind = 1, st.st_size, st.st_mtime, "file"
        day = time.strftime("%Y-%m-%d", time.localtime(newest)) if newest else "-"
        print(f"{kind}\t{e.name}\t{n}\t{size / 1e6:.1f}\t{day}")
    return 0


def text_files(paths, max_bytes):
    for p in paths:
        walk = os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p), [],
                                                     [os.path.basename(p)])]
        for root, _, files in walk:
            for f in files:
                full = os.path.join(root, f)
                if os.path.splitext(f)[1].lower() in TEXT \
                        and os.path.getsize(full) <= max_bytes:
                    yield full


def name_pattern(name):
    forms = {name, quote(name)}
    alt = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<![\w.-])(?:{alt})(?![\w.-])")


def refs(cat, scan, max_mb):
    names = sorted(os.listdir(cat), key=str.lower)
    pats = {n: name_pattern(n) for n in names}
    hits = {n: [] for n in names}
    for path in text_files([cat] + scan, max_mb * 1e6):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        for n, pat in pats.items():
            k = len(pat.findall(body))
            if k:
                hits[n].append((k, path))
    for n in names:
        found = sorted(hits[n], reverse=True)
        print(f"{n}\t{sum(k for k, _ in found)}")
        for k, path in found:
            print(f"    {k}\t{path}")
    return 0


def read_plan(cat, plan):
    ops = []
    with open(plan, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                raise ValueError(f"plan line {n}: need SOURCE<TAB>DESTINATION")
            src, dst = parts
            if src.endswith("/*"):
                base = src[:-2]
                for child in sorted(os.listdir(os.path.join(cat, base))):
                    ops.append((f"{base}/{child}", f"{dst.rstrip('/')}/{child}"))
            else:
                ops.append((src, dst))
    return ops


def check_ops(cat, ops):
    problems, claimed = [], set()
    for src, dst in ops:
        s, d = os.path.join(cat, src), os.path.join(cat, dst)
        if not os.path.lexists(s):
            problems.append(f"missing source: {src}")
        if os.path.lexists(d) and not (os.path.lexists(s)
                                       and os.path.samefile(s, d)):
            problems.append(f"destination exists: {dst}")
        if dst.lower() in claimed:
            problems.append(f"two moves land on: {dst}")
        claimed.add(dst.lower())
    return problems


def apply(cat, plan, execute, receipt):
    ops = read_plan(cat, plan)
    problems = check_ops(cat, ops)
    for p in problems:
        print(f"problem: {p}")
    if problems:
        return 1
    if not execute:
        for src, dst in ops:
            print(f"would move\t{src}\t{dst}")
        print(f"{len(ops)} move(s) checked; rerun with --execute.")
        return 0
    receipt = receipt or f"receipt-{time.strftime('%Y%m%d-%H%M%S')}.tsv"
    status = 0
    with open(receipt, "a", encoding="utf-8") as out:
        out.write(f"# category\t{os.path.abspath(cat)}\n"
                  f"# applied\t{time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
        for src, dst in ops:
            d = os.path.join(cat, dst)
            parent = os.path.dirname(d)
            try:
                if not os.path.isdir(parent):
                    os.makedirs(parent)
                    out.write(f"mkdir\t{os.path.relpath(parent, cat)}\n")
                os.rename(os.path.join(cat, src), d)
            except OSError as err:
                print(f"failed: {src} -> {dst}: {err}")
                status = 1
                break
            out.write(f"moved\t{src}\t{dst}\n")
            out.flush()
    print(f"receipt: {receipt}")
    return status


def read_receipt(path):
    moves, dirs = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if parts[0] == "moved" and len(parts) == 3:
                moves.append((parts[1], parts[2]))
            elif parts[0] == "mkdir" and len(parts) == 2:
                dirs.append(parts[1])
    return moves, dirs


def reverse(cat, receipt, execute):
    moves, dirs = read_receipt(receipt)
    back = [(dst, src) for src, dst in reversed(moves)]
    problems = check_ops(cat, back)
    for p in problems:
        print(f"problem: {p}")
    if problems:
        return 1
    for dst, src in back:
        if execute:
            os.rename(os.path.join(cat, dst), os.path.join(cat, src))
        print(f"{'moved back' if execute else 'would move back'}\t{dst}\t{src}")
    for d in dirs:
        print(f"left in place (created by the apply): {d}")
    return 0


def relink(cat, receipt, files, execute, backup_dir, bare):
    moves, _ = read_receipt(receipt)
    catname = os.path.basename(os.path.abspath(cat))
    subs = []
    for src, dst in moves:
        old, new = src, dst
        if not bare:
            old, new = f"{catname}/{src}", f"{catname}/{dst}"
        forms = [(old, new), (quote(old), quote(new)),
                 (old.replace("/", "\\"), new.replace("/", "\\")),
                 (old.replace("/", "\\\\"), new.replace("/", "\\\\"))]
        seen = set()
        for o, n in forms:
            if o not in seen:
                seen.add(o)
                subs.append((re.compile(rf"(?<![\w.-]){re.escape(o)}"
                                        rf"(?=[/\\\"')\s\]>]|$)", re.M), n))
    if execute and not backup_dir:
        print("--execute needs --backup-dir", file=sys.stderr)
        return 2
    for path in files:
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        total, new_body = 0, body
        for pat, rep in subs:
            new_body, k = pat.subn(lambda m: rep, new_body)
            total += k
        print(f"{total}\t{path}")
        if execute and total:
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(path, os.path.join(backup_dir, os.path.basename(path)))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new_body)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("survey"); p.add_argument("category")
    p = sub.add_parser("refs"); p.add_argument("category")
    p.add_argument("--scan", action="append", default=[])
    p.add_argument("--max-mb", type=float, default=20)
    p = sub.add_parser("apply"); p.add_argument("category"); p.add_argument("plan")
    p.add_argument("--execute", action="store_true"); p.add_argument("--receipt")
    p = sub.add_parser("reverse"); p.add_argument("category"); p.add_argument("receipt")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("relink"); p.add_argument("category"); p.add_argument("receipt")
    p.add_argument("files", nargs="+"); p.add_argument("--execute", action="store_true")
    p.add_argument("--backup-dir"); p.add_argument("--bare", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(a.category):
        print(f"not a directory: {a.category}", file=sys.stderr)
        return 2
    try:
        if a.cmd == "survey":
            return survey(a.category)
        if a.cmd == "refs":
            return refs(a.category, a.scan, a.max_mb)
        if a.cmd == "apply":
            return apply(a.category, a.plan, a.execute, a.receipt)
        if a.cmd == "reverse":
            return reverse(a.category, a.receipt, a.execute)
        return relink(a.category, a.receipt, a.files, a.execute,
                      a.backup_dir, a.bare)
    except (OSError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
