"""Regression tests for the jd-librarian scripts. Run: python3 -m unittest"""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

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
        write(self.plan, "SHA\t71.18 SHA\nSHA/report.txt\tx.txt\n")
        code, out = quiet(plan.apply, self.cat, self.plan, False, None)
        self.assertEqual(code, 1)
        self.assertIn("missing source: SHA/report.txt", out)

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
        write(self.receipt, "moved\tSHA\t71.18 SHA\n")

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
