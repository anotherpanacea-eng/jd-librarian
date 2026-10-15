"""Regression tests for the jd-librarian scripts.

Run from the repository root: python3 -m unittest discover -s tests
"""
import contextlib
import importlib.util
import io
import ntpath
import os
import posixpath
import tempfile
import types
import unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jd-librarian", "skills")


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check = load("structural_check", "jd-jdex-audit/scripts/structural_check.py")
plan = load("category_plan", "jd-number-category/scripts/category_plan.py")


def write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = fn(*args)
    return code, out.getvalue()


class JdexLinks(unittest.TestCase):
    def test_link_forms(self):
        self.assertEqual(list(check.link_destinations("[d](a%20(2026)/)")), ["a%20(2026)/"])
        self.assertEqual(list(check.link_destinations('[t](<a b/c> "T")')), ["a b/c"])
        self.assertEqual(list(check.link_destinations('[t](p/q "T")')), ["p/q"])

    def test_unterminated_link_is_not_a_link(self):
        self.assertEqual(list(check.link_destinations("[d](a(b/) tail")), [])
        self.assertEqual(list(check.link_destinations("[d](<a b>")), [])
        self.assertEqual(list(check.link_destinations("[d](a b)")), [])

    def test_correct_index_with_parentheses_is_clean(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "00-09 Sys", "00 Mgmt"))
            os.makedirs(os.path.join(root, "10-19 Work", "11 Projects", "11.10 Draft (2026)"))
            jdex = os.path.join(root, "00-09 Sys", "00 Mgmt", "00.00 JDex.md")
            write(jdex, "- [00](./)\n"
                        "- [11](../../10-19%20Work/11%20Projects/)\n"
                        "  - [draft](../../10-19%20Work/11%20Projects/11.10%20Draft%20(2026)/)\n"
                        '- [mgmt](<../../00-09 Sys/> "area")\n')
            self.assertEqual(check.check_jdex(root, jdex), [])


class Structure(unittest.TestCase):
    def test_numbered_loose_file_is_still_loose(self):
        with tempfile.TemporaryDirectory() as root:
            cat = os.path.join(root, "10-19 Admin", "10 Management")
            os.makedirs(os.path.join(cat, "10.01 Inbox"))
            write(os.path.join(cat, "10.00 JDex.md"))
            write(os.path.join(cat, "99.10 Wrong category.txt"))
            write(os.path.join(cat, "10.10 Notes.txt"))
            found = {(k, p.split("/")[-1]) for _, k, p, _ in check.check(root)}
            self.assertIn(("file-at-category-level", "99.10 Wrong category.txt"), found)
            self.assertIn(("id-outside-category", "99.10 Wrong category.txt"), found)
            self.assertIn(("file-at-category-level", "10.10 Notes.txt"), found)
            self.assertNotIn(("file-at-category-level", "10.00 JDex.md"), found)

    def test_misused_standard_zero_files_are_reported(self):
        with tempfile.TemporaryDirectory() as root:
            cat = os.path.join(root, "10-19 Admin", "10 Management")
            write(os.path.join(cat, "10.01 Inbox", "note.txt"))
            write(os.path.join(cat, "10.05 Secrets.txt"))
            write(os.path.join(cat, "10.00 Unrelated.txt"))
            write(os.path.join(cat, "10.04 Links.md"))
            found = {(k, p.split("/")[-1]) for _, k, p, _ in check.check(root)}
            self.assertIn(("id-in-reserved-range", "10.05 Secrets.txt"), found)
            self.assertIn(("id-in-standard-zero-range", "10.00 Unrelated.txt"), found)
            self.assertFalse([f for f in found if f[1] == "10.04 Links.md"])


class Apply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cat = os.path.join(self.tmp.name, "71 Finance")
        write(os.path.join(self.cat, "SHA", "report.txt"), "first")
        write(os.path.join(self.cat, "SHA Documents", "report.txt"), "second")
        write(os.path.join(self.cat, "SHA Documents", "other.txt"), "other")
        self.plan = os.path.join(self.tmp.name, "plan.tsv")
        self.receipt = os.path.join(self.tmp.name, "receipt.tsv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_merge_into_renamed_folder_refuses_colliding_child(self):
        write(self.plan, "SHA\t71.18 SHA\nSHA Documents/*\t71.18 SHA\n")
        code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("destination exists when this move runs: 71.18 SHA/report.txt", out)
        code, _ = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertEqual(read(os.path.join(self.cat, "SHA", "report.txt")), "first")

    def test_clean_merge_applies_and_reverses(self):
        os.remove(os.path.join(self.cat, "SHA Documents", "report.txt"))
        write(self.plan, "SHA\t71.18 SHA\nSHA Documents/*\t71.18 SHA\n")
        code, _ = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 0)
        self.assertEqual(read(os.path.join(self.cat, "71.18 SHA", "other.txt")), "other")
        code, _ = quiet(plan.reverse, self.cat, self.receipt, True)
        self.assertEqual(code, 0)
        self.assertEqual(read(os.path.join(self.cat, "SHA", "report.txt")), "first")
        self.assertEqual(read(os.path.join(self.cat, "SHA Documents", "other.txt")), "other")

    def test_moved_away_source_is_missing_later(self):
        # Reached through the renamed folder, the file is gone already.
        write(self.plan, "SHA/report.txt\tx.txt\nSHA\t71.18 SHA\n71.18 SHA/report.txt\ty.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("missing source: 71.18 SHA/report.txt", out)

    def test_dry_run_sees_folders_apply_creates(self):
        write(self.plan, "SHA\tX/SHA\nSHA Documents\tX\n")
        code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("destination exists when this move runs: X", out)

    def test_windows_separators_still_catch_collisions(self):
        # Emulate Windows on any disk: backslash separators, ntpath's normpath.
        win = types.SimpleNamespace(**vars(posixpath))
        win.normpath = ntpath.normpath
        win.lexists = lambda p: posixpath.lexists(p.replace("\\", "/"))
        with mock.patch.object(os, "sep", "\\"), mock.patch.object(os, "altsep", "/"), \
                mock.patch.object(os, "path", win):
            write(self.plan, "SHA\t71.18 SHA\nSHA Documents/*\t71.18 SHA\n")
            code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("destination exists when this move runs: 71.18 SHA/report.txt", out)

    def test_trailing_slash_destination_moves(self):
        write(self.plan, "SHA\t71.18 SHA/\n")
        code, _ = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 0)
        self.assertEqual(read(os.path.join(self.cat, "71.18 SHA", "report.txt")), "first")
        self.assertFalse(os.path.exists(os.path.join(self.cat, "SHA")))
        self.assertIn("moved\tSHA\t71.18 SHA\n", read(self.receipt))

    def test_receipt_paths_outside_the_category_are_refused(self):
        outside = os.path.join(self.tmp.name, "elsewhere.txt")
        write(outside, "keep")
        for line in ("moved\t../outside.txt\t../elsewhere.txt\n",
                     f"moved\t{self.tmp.name}/outside.txt\t{outside}\n",
                     "moved\tSHA/../../outside.txt\tSHA/report.txt\n"):
            write(self.receipt, line)
            code, out = quiet(plan.reverse, self.cat, self.receipt, True)
            self.assertEqual(code, 1, line)
            self.assertRegex(out, r"(outside|not a path inside) the category")
            self.assertEqual(read(outside), "keep")
            self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "outside.txt")))

    def test_plan_paths_outside_the_category_are_refused(self):
        write(self.plan, "SHA/report.txt\t../stolen.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertIn("../stolen.txt: outside the category", out)
        self.assertEqual(read(os.path.join(self.cat, "SHA", "report.txt")), "first")
        write(self.plan, "../*\tX\n")
        with self.assertRaises(ValueError):
            plan.read_plan(self.cat, self.plan)

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_symlinked_folder_out_of_the_category_is_refused(self):
        away = os.path.join(self.tmp.name, "away")
        os.makedirs(away)
        try:
            os.symlink(away, os.path.join(self.cat, "Link"))
        except OSError:
            self.skipTest("symlinks not permitted here")
        write(self.plan, "SHA/report.txt\tLink/report.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertIn("goes through a link", out)
        self.assertEqual(os.listdir(away), [])
        write(self.plan, "Link\t71.19 Link\n")
        code, _ = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 0)

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_link_renamed_by_an_earlier_move_is_still_refused(self):
        away = os.path.join(self.tmp.name, "away")
        os.makedirs(away)
        write(os.path.join(away, "victim.txt"), "theirs")
        write(os.path.join(self.cat, "local.txt"), "mine")
        try:
            os.symlink(away, os.path.join(self.cat, "Link"))
        except OSError:
            self.skipTest("symlinks not permitted here")
        write(self.plan, "Link\tRenamed\nlocal.txt\tRenamed/export.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertIn("Renamed/export.txt: goes through a link", out)
        self.assertEqual(sorted(os.listdir(away)), ["victim.txt"])
        write(self.receipt, "moved\trescued.txt\tRenamed/victim.txt\n"
                            "moved\tRenamed\tLink\n")
        code, out = quiet(plan.reverse, self.cat, self.receipt, True)
        self.assertEqual(code, 1)
        self.assertIn("goes through a link", out)
        self.assertEqual(sorted(os.listdir(away)), ["victim.txt"])
        self.assertTrue(os.path.islink(os.path.join(self.cat, "Link")))

    def test_merge_from_a_folder_earlier_lines_touch_is_refused(self):
        for rows in ("SHA\t71.10 SHA\nSHA Documents\tSHA\nSHA/*\t71.11 Merge\n",
                     "SHA/*\tSHA Documents\nSHA Documents/*\tC\n",
                     "SHA\tB\nSHA/*\tC\n"):
            write(self.plan, rows)
            with self.assertRaisesRegex(ValueError, "an earlier line moves"):
                plan.read_plan(self.cat, self.plan)
        self.assertEqual(read(os.path.join(self.cat, "SHA", "report.txt")), "first")

    def test_merge_that_matches_nothing_is_refused(self):
        os.makedirs(os.path.join(self.cat, "Empty"))
        for rows, why in (("Empty/*\tX\n", "empty"), ("Typo/*\tX\n", "not a folder")):
            write(self.plan, rows)
            with self.assertRaisesRegex(ValueError, why):
                plan.read_plan(self.cat, self.plan)

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_relative_link_moved_up_a_level_is_refused(self):
        os.makedirs(os.path.join(self.cat, "safe"))
        os.makedirs(os.path.join(self.tmp.name, "safe"))
        write(os.path.join(self.cat, "local.txt"), "mine")
        os.makedirs(os.path.join(self.cat, "nested"))
        try:
            os.symlink("../safe", os.path.join(self.cat, "nested", "Link"))
        except OSError:
            self.skipTest("symlinks not permitted here")
        write(self.plan, "nested/Link\tLink\nlocal.txt\tLink/export.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertIn("Link/export.txt: goes through a link", out)
        self.assertEqual(os.listdir(os.path.join(self.tmp.name, "safe")), [])
        self.assertEqual(read(os.path.join(self.cat, "local.txt")), "mine")

    def test_plan_reusing_a_vacated_path_is_refused(self):
        write(os.path.join(self.cat, "loose.txt"), "loose")
        for rows, bad in (("SHA\tB\nloose.txt\tSHA/loose.txt\n", "SHA/loose.txt"),
                          ("SHA\tB\nloose.txt\tSHA/sub/loose.txt\nSHA\tC\n",
                           "SHA/sub/loose.txt"),
                          ("SHA\tB\nSHA Documents\tSHA\n", "SHA:"),
                          ("SHA\t71.18 SHA\nSHA/report.txt\tx.txt\n", "SHA/report.txt")):
            write(self.plan, rows)
            code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
            self.assertEqual(code, 1, rows)
            self.assertIn(f"{bad}", out)
            self.assertIn("an earlier line moves SHA away", out)
        self.assertEqual(read(os.path.join(self.cat, "SHA", "report.txt")), "first")
        self.assertFalse(os.path.exists(self.receipt))

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_moving_into_a_name_a_link_left_is_refused_as_reuse(self):
        away = os.path.join(self.tmp.name, "away")
        os.makedirs(away)
        try:
            os.symlink(away, os.path.join(self.cat, "Link"))
        except OSError:
            self.skipTest("symlinks not permitted here")
        write(os.path.join(self.cat, "f"), "f")
        write(self.plan, "Link\tSavedLink\nf\tLink/f\n")
        code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("Link/f: an earlier line moves Link away", out)

    def test_receipt_records_every_folder_the_apply_makes(self):
        write(os.path.join(self.cat, "loose.txt"), "loose")
        write(self.plan, "loose.txt\tNew/sub/loose.txt\n")
        code, _ = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 0)
        self.assertIn("mkdir\tNew\nmkdir\tNew/sub\n", read(self.receipt))
        code, out = quiet(plan.reverse, self.cat, self.receipt, True)
        self.assertEqual(code, 0, out)
        self.assertEqual(read(os.path.join(self.cat, "loose.txt")), "loose")
        self.assertIn("left in place (created by the apply): New/sub", out)

    def test_apply_refuses_an_existing_receipt(self):
        os.mkdir(os.path.join(self.cat, "A"))
        write(self.plan, "A\tB\n")
        code, _ = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 0)
        code, _ = quiet(plan.reverse, self.cat, self.receipt, True)
        self.assertEqual(code, 0)
        code, out = quiet(plan.apply, self.cat, self.plan, True, self.receipt)
        self.assertEqual(code, 1)
        self.assertIn("receipt already exists", out)
        self.assertTrue(os.path.isdir(os.path.join(self.cat, "A")))

    def test_rename_never_replaces(self):
        a, b = os.path.join(self.cat, "a.txt"), os.path.join(self.cat, "b.txt")
        write(a, "a")
        write(b, "b")
        with self.assertRaises(FileExistsError):
            plan.rename_noreplace(a, b)
        self.assertEqual(read(b), "b")


class Relink(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cat = os.path.join(self.tmp.name, "71 Finance")
        os.makedirs(self.cat)
        self.receipt = os.path.join(self.tmp.name, "receipt.tsv")
        write(self.receipt, "moved\tSHA\t71.18 SHA\n"
                            "moved\tSHA Documents/other.txt\t71.18 SHA/other.txt\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rename_does_not_touch_a_name_sharing_its_prefix(self):
        doc = os.path.join(self.tmp.name, "refs.json")
        write(doc, '{"a": "71 Finance/SHA Documents/report.txt",\n'
                   ' "b": "D:\\\\Dropbox\\\\71 Finance\\\\SHA Documents\\\\r.txt",\n'
                   ' "c": "71 Finance/SHA/report.txt",\n'
                   ' "d": "D:\\\\Dropbox\\\\71 Finance\\\\SHA\\\\r.txt"}\n'
                   "[link](../71%20Finance/SHA%20Documents/) [ok](../71%20Finance/SHA/)\n")
        code, _ = quiet(plan.relink, self.cat, self.receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak"), False)
        self.assertEqual(code, 0)
        body = read(doc)
        self.assertIn('"71 Finance/SHA Documents/report.txt"', body)
        self.assertIn("\\\\71 Finance\\\\SHA Documents\\\\", body)
        self.assertIn('"71 Finance/71.18 SHA/report.txt"', body)
        self.assertIn("\\\\71 Finance\\\\71.18 SHA\\\\r.txt", body)
        self.assertIn("71%20Finance/SHA%20Documents/", body)
        self.assertIn("71%20Finance/71.18%20SHA/", body)

    def test_quoted_prose_and_titled_forms_are_rewritten(self):
        doc = os.path.join(self.tmp.name, "notes.md")
        write(doc, "yaml: '71 Finance/SHA'\n"
                   "prose: see 71 Finance/SHA for receipts\n"
                   '[t](../71%20Finance/SHA "title")\n')
        code, _ = quiet(plan.relink, self.cat, self.receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak"), False)
        self.assertEqual(code, 0)
        self.assertEqual(read(doc), "yaml: '71 Finance/71.18 SHA'\n"
                                    "prose: see 71 Finance/71.18 SHA for receipts\n"
                                    '[t](../71%20Finance/71.18%20SHA "title")\n')

    def test_markdown_destination_stays_a_valid_link(self):
        doc = os.path.join(self.tmp.name, "bare.md")
        write(doc, "[report](SHA/report.txt) and SHA/report.txt in prose\n"
                   "[angle](<SHA/report.txt>)\n")
        receipt = os.path.join(self.tmp.name, "one.tsv")
        write(receipt, "moved\tSHA\t71.18 SHA\n")
        code, _ = quiet(plan.relink, self.cat, receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak3"), True)
        self.assertEqual(code, 0)
        self.assertEqual(read(doc), "[report](71.18%20SHA/report.txt) and "
                                    "71.18 SHA/report.txt in prose\n"
                                    "[angle](<71.18 SHA/report.txt>)\n")

    def test_markdown_destination_with_leading_space_or_parentheses(self):
        doc = os.path.join(self.tmp.name, "edge.md")
        write(doc, "[a]( SHA/report.txt)\n[b](x(1)/SHA/report.txt)\n"
                   "[c](x) then SHA/report.txt\n")
        receipt = os.path.join(self.tmp.name, "one2.tsv")
        write(receipt, "moved\tSHA\t71.18 SHA\n")
        code, _ = quiet(plan.relink, self.cat, receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak4"), True)
        self.assertEqual(code, 0)
        self.assertEqual(read(doc), "[a]( 71.18%20SHA/report.txt)\n"
                                    "[b](x(1)/71.18%20SHA/report.txt)\n"
                                    "[c](x) then 71.18 SHA/report.txt\n")

    def test_chained_moves_follow_each_file_to_its_last_home(self):
        receipt = os.path.join(self.tmp.name, "chain.tsv")
        write(receipt, "moved\tA\tB\nmoved\tC\tA\nmoved\tA\tD\n")
        doc = os.path.join(self.tmp.name, "chain.md")
        write(doc, "- 71 Finance/A/x\n- 71 Finance/C/x\n")
        code, _ = quiet(plan.relink, self.cat, receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak2"), False)
        self.assertEqual(code, 0)
        self.assertEqual(read(doc), "- 71 Finance/B/x\n- 71 Finance/D/x\n")

    def test_match_inside_a_longer_name_is_left_alone(self):
        os.makedirs(os.path.join(self.cat, "SHA Documents"))
        os.makedirs(os.path.join(self.tmp.name, "Old 71 Finance"))
        receipt = os.path.join(self.tmp.name, "bare.tsv")
        write(receipt, "moved\tDocuments\t71.12 Documents\n")
        doc = os.path.join(self.tmp.name, "list.md")
        write(doc, "- SHA Documents/report.txt\n- Documents/report.txt\n")
        code, _ = quiet(plan.relink, self.cat, receipt, [doc], True,
                        os.path.join(self.tmp.name, "bak1"), True)
        self.assertEqual(code, 0)
        self.assertEqual(read(doc), "- SHA Documents/report.txt\n"
                                    "- 71.12 Documents/report.txt\n")
        doc2 = os.path.join(self.tmp.name, "paths.json")
        write(doc2, '"D:\\\\Archive\\\\Old 71 Finance\\\\SHA\\\\x.pdf"\n')
        code, _ = quiet(plan.relink, self.cat, self.receipt, [doc2], True,
                        os.path.join(self.tmp.name, "bak2"), False)
        self.assertEqual(code, 0)
        self.assertIn("Old 71 Finance\\\\SHA\\\\", read(doc2))

    def test_same_file_named_twice_is_rewritten_once(self):
        a = os.path.join(self.tmp.name, "a", "config.json")
        write(a, '"71 Finance/SHA/one"\n')
        link = os.path.join(self.tmp.name, "A2", "config.json")
        os.makedirs(os.path.dirname(link))
        os.link(a, link)              # one file, two names, as on a case-blind disk
        bak = os.path.join(self.tmp.name, "bak")
        dotted = os.path.join(self.tmp.name, ".", "a", "config.json")
        code, _ = quiet(plan.relink, self.cat, self.receipt, [a, dotted, link], True, bak, False)
        self.assertEqual(code, 0)
        self.assertEqual(read(a), '"71 Finance/71.18 SHA/one"\n')
        self.assertEqual(read(plan.backup_path(bak, a)), '"71 Finance/SHA/one"\n')
        self.assertFalse(os.path.exists(plan.backup_path(bak, link)))

    def test_backups_are_distinct_and_never_overwritten(self):
        a = os.path.join(self.tmp.name, "a", "config.json")
        b = os.path.join(self.tmp.name, "b", "config.json")
        write(a, '"71 Finance/SHA/one"\n')
        write(b, '"71 Finance/SHA/two"\n')
        bak = os.path.join(self.tmp.name, "bak")
        code, _ = quiet(plan.relink, self.cat, self.receipt, [a, b], True, bak, False)
        self.assertEqual(code, 0)
        self.assertEqual(read(plan.backup_path(bak, a)), '"71 Finance/SHA/one"\n')
        self.assertEqual(read(plan.backup_path(bak, b)), '"71 Finance/SHA/two"\n')
        write(a, '"71 Finance/SHA/again"\n')
        code, _ = quiet(plan.relink, self.cat, self.receipt, [a], True, bak, False)
        self.assertEqual(code, 1)
        self.assertEqual(read(a), '"71 Finance/SHA/again"\n')
        self.assertEqual(read(plan.backup_path(bak, a)), '"71 Finance/SHA/one"\n')


if __name__ == "__main__":
    unittest.main()
