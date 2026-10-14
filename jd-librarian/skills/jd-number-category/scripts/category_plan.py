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
      checks the plan, move by move against the tree the earlier moves leave.
      Never overwrites; stops at the first failure. The
      receipt goes to --receipt, or the current folder (not the category).
  reverse CATEGORY RECEIPT [--execute]
      Undo an apply, newest move first. Folders the apply created are left
      in place (empty) for a person to remove.
  relink CATEGORY RECEIPT FILE ... [--execute --backup-dir DIR] [--bare]
      Rewrite paths the apply changed inside text files (a JDex, CLAUDE.md,
      a tool registry), in plain, %-encoded and backslash forms. Paths are
      matched with the category folder name in front unless --bare, as
      whole path components, and not where the text around a match spells
      a longer folder name beside it. Originals are backed up under their
      full paths in DIR; an existing backup stops the run before any write.

Exit: 0 ok, 1 problems found or a step failed, 2 bad invocation.
"""
import argparse
import errno
import os
import posixpath
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


def norm(path):
    """PATH with '/' separators and no '.', '..' or trailing-slash forms, so
    checking, applying and the receipt all use the same string."""
    for sep in {os.sep, os.altsep} - {None, "/"}:
        path = path.replace(sep, "/")
    return posixpath.normpath(path)


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
            src, dst = norm(parts[0]), norm(parts[1])
            if src.endswith("/*"):
                base = src[:-2]
                for child in sorted(os.listdir(os.path.join(cat, base))):
                    ops.append((f"{base}/{child}", f"{dst}/{child}"))
            else:
                ops.append((src, dst))
    return ops


def _under(path, top):
    """The rest of PATH below TOP ('' for TOP itself), or None. Case-blind,
    so a case-insensitive disk is treated as conservatively as possible."""
    p, t = path.lower(), top.lower()
    if p == t:
        return ""
    if p.startswith(t + "/"):
        return path[len(top) + 1:]
    return None


def exists_after(cat, path, done):
    """Whether PATH exists once the moves in DONE have run, in order.

    Walks the earlier moves newest first: a path inside a moved destination
    came from the matching path inside its source; a path inside a moved
    source is gone; a folder above a destination was there or was created
    for it. Otherwise the original disk decides.
    """
    for src, dst in reversed(done):
        rest = _under(path, dst)
        if rest is not None:
            if rest == "":
                return True
            path = f"{src}/{rest}"
            continue
        if _under(path, src) is not None:
            return False
        if _under(dst, path):
            return True
    return os.path.lexists(os.path.join(cat, path))


def check_ops(cat, ops):
    """Check every move against the tree as the earlier moves leave it."""
    problems, done = [], []
    for src, dst in ops:
        if not exists_after(cat, src, done):
            problems.append(f"missing source: {src}")
        if src.lower() != dst.lower() and exists_after(cat, dst, done):
            problems.append(f"destination exists when this move runs: {dst}")
        done.append((src, dst))
    return problems


def rename_noreplace(src, dst):
    """Rename, refusing to replace an existing destination. A case-only
    rename of the same entry is allowed."""
    if os.path.lexists(dst) and not os.path.samefile(src, dst):
        raise FileExistsError(errno.EEXIST, "destination exists", dst)
    os.rename(src, dst)


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
                    out.write(f"mkdir\t{norm(os.path.relpath(parent, cat))}\n")
                rename_noreplace(os.path.join(cat, src), d)
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
                moves.append((norm(parts[1]), norm(parts[2])))
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
            try:
                rename_noreplace(os.path.join(cat, dst), os.path.join(cat, src))
            except OSError as err:
                print(f"failed: {dst} -> {src}: {err}")
                return 1
        print(f"{'moved back' if execute else 'would move back'}\t{dst}\t{src}")
    for d in dirs:
        print(f"left in place (created by the apply): {d}")
    return 0


def neighbour_names(cat, moves):
    """Every folder or file name that sits beside a moved path or the
    category, now or before the apply."""
    names = set()
    for d in [os.path.dirname(os.path.abspath(cat)), cat] + [
            os.path.join(cat, posixpath.dirname(p)) for m in moves for p in m]:
        if os.path.isdir(d):
            names.update(os.listdir(d))
    for m in moves:
        for p in m:
            names.update(p.split("/"))
    return names


def relink(cat, receipt, files, execute, backup_dir, bare):
    moves, _ = read_receipt(receipt)
    catname = os.path.basename(os.path.abspath(cat))
    names = neighbour_names(cat, moves)
    subs = []
    for src, dst in moves:
        seen = set()  # per move: a later move may reuse an earlier source name
        old, new = (src, dst) if bare else (f"{catname}/{src}", f"{catname}/{dst}")
        first, last = old.split("/")[0], old.split("/")[-1]
        for enc, sep in ((str, "/"), (quote, "/"), (str, "\\"), (str, "\\\\")):
            o = enc(old).replace("/", sep)
            if o in seen:
                continue
            seen.add(o)
            # A match is a whole path component at both ends, and is left
            # alone where the text around it spells a longer name beside
            # it: renaming SHA, or Documents, leaves "SHA Documents" alone.
            heads = [enc(x[:-len(first)]) for x in names
                     if x != first and x.endswith(first)]
            tails = [enc(x[len(last):]) for x in names
                     if x != last and x.startswith(last)]
            subs.append((re.compile(rf"(?<![\w.-]){re.escape(o)}(?![\w.-])"),
                         enc(new).replace("/", sep), heads, tails))
    if execute and not backup_dir:
        print("--execute needs --backup-dir", file=sys.stderr)
        return 2
    changes, inodes = [], set()
    for path in files:
        st = os.stat(path)
        if (st.st_dev, st.st_ino) in inodes:
            continue                  # the same file named twice
        inodes.add((st.st_dev, st.st_ino))
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        total = 0
        for pat, new, heads, tails in subs:
            def swap(m):
                nonlocal total
                t = m.string
                if any(t.endswith(h, 0, m.start()) for h in heads) \
                        or any(t.startswith(x, m.end()) for x in tails):
                    return m.group()
                total += 1
                return new
            body = pat.sub(swap, body)
        print(f"{total}\t{path}")
        if total:
            changes.append((path, body))
    if not execute:
        return 0
    # Each original is backed up under its own full path, and nothing is
    # written unless every backup slot is free.
    plan = [(path, backup_path(backup_dir, path), body) for path, body in changes]
    taken = [b for _, b, _ in plan if os.path.lexists(b)]
    for b in taken:
        print(f"backup already exists, nothing rewritten: {b}")
    if len({b.lower() for _, b, _ in plan}) != len(plan):
        print("two files would share a backup slot, nothing rewritten")
        return 1
    if taken:
        return 1
    for path, backup, body in plan:
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"backed up\t{path}\t{backup}")
    return 0


def backup_path(backup_dir, path):
    """BACKUP_DIR plus PATH's absolute path, drive and root folded in."""
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    parts = [drive.strip(":\\/").replace(":", "")] if drive else []
    parts += [p for p in rest.replace("\\", "/").split("/") if p]
    return os.path.join(backup_dir, *parts)


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
