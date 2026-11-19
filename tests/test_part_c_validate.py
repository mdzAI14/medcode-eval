"""Tests for medcode_eval.part_c.validate on invented fixtures.

The code set is the invented one of tests/test_checker.py (codes U90-U96).
Specs and cases are the Part B fixture texts; gold files are Part C gold.
Every file is an obvious fake in a temporary directory the tests remove.
No network.
"""

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_c import matches
from medcode_eval.part_c import validate
from tests.part_c_fixture import gold_obj
from tests.test_part_b_validate import Fixture, write_case


def c_gold(case_id, codes=("U95",), gap_type="unspecified_detail", unsupported=("U96",),
           optional=(), **over):
    g = gold_obj(case_id, codes, gap_type, unsupported, optional)
    g.update(over)
    return g


class CFixture(Fixture):
    def run_validate(self):
        return validate.validate(self.root, data=self.data)

    def write(self, case_id="fake-c-one", **kw):
        write_case(self.root, case_id, gold_obj=c_gold(case_id, **kw))

    def problems(self, kind):
        return [p for p in self.run_validate().problems if p.kind == kind]


class TestMatchRule(unittest.TestCase):
    def test_equal_or_prefix(self):
        self.assertTrue(matches("U96", "U96"))
        self.assertTrue(matches("U93.1", "U93"))
        self.assertTrue(matches("u931", "U93.1"))
        self.assertTrue(matches("U90012A", "U90.01"))
        self.assertFalse(matches("U95", "U96"))
        self.assertFalse(matches("U93", "U93.1"))
        self.assertFalse(matches("U9", "U93"))


class TestClean(CFixture):
    def test_valid_gap_case(self):
        self.write()
        r = self.run_validate()
        self.assertEqual(r.problems, [])
        self.assertEqual(r.case_ids, ["fake-c-one"])

    def test_valid_counter_case(self):
        self.write(codes=("U90.012A",), gap_type="counter_case", unsupported=())
        self.assertEqual(self.run_validate().problems, [])

    def test_valid_with_category_and_optional(self):
        self.write(codes=("U91.0",), gap_type="provider_statement",
                   unsupported=("U92", "U93.0"), optional=("U94.0",))
        self.assertEqual(self.run_validate().problems, [])

    def test_every_gap_type_accepted(self):
        for i, gt in enumerate(("unspecified_detail", "uncertain_diagnosis",
                                "provider_statement", "unstated_link", "not_current")):
            self.write(f"fake-c-{i}", gap_type=gt)
        self.assertEqual(self.run_validate().problems, [])

    def test_empty_folders_with_readmes(self):
        for d in ("specs", "cases", "gold"):
            (self.root / d / "README.md").write_text("Invented readme.\n")
        r = self.run_validate()
        self.assertEqual((r.problems, r.warnings, r.reviews), ([], [], []))
        self.assertEqual(r.counts, {"spec": 0, "case": 0, "gold": 0})


class TestGoldFields(CFixture):
    def test_unknown_gap_type(self):
        self.write(gap_type="invented_gap")
        hits = self.problems("bad_enum")
        self.assertTrue(any("gap_type" in p.message for p in hits), hits)

    def test_target_trap_is_unknown_field(self):
        self.write(target_trap="laterality")
        hits = self.problems("unknown_field")
        self.assertTrue(any("target_trap" in p.message for p in hits), hits)

    def test_missing_unsupported_codes(self):
        g = c_gold("fake-c-one")
        del g["unsupported_codes"]
        write_case(self.root, "fake-c-one", gold_obj=g)
        hits = self.problems("missing_field")
        self.assertTrue(any("unsupported_codes" in p.message for p in hits), hits)

    def test_missing_gap_type(self):
        g = c_gold("fake-c-one")
        del g["gap_type"]
        write_case(self.root, "fake-c-one", gold_obj=g)
        self.assertTrue(self.problems("missing_field"))

    def test_part_b_rules_still_apply(self):
        self.write(codes=("U90.012",))  # a header: checker error
        self.assertTrue(self.problems("checker_error"))
        self.write("fake-c-two", code_set="other")
        self.assertTrue(self.problems("bad_code_set"))


class TestUnsupported(CFixture):
    def test_not_a_list(self):
        self.write()
        g = c_gold("fake-c-one", unsupported_codes={"code": "U96"})
        write_case(self.root, "fake-c-one", gold_obj=g)
        self.assertTrue(self.problems("bad_unsupported"))

    def test_empty_list_on_gap_case(self):
        self.write(unsupported=())
        self.assertTrue(self.problems("bad_unsupported"))

    def test_non_empty_list_on_counter_case(self):
        self.write(codes=("U90.012A",), gap_type="counter_case", unsupported=("U96",))
        self.assertTrue(self.problems("bad_unsupported"))

    def test_entry_not_in_code_set(self):
        self.write(unsupported=("U97",))
        self.assertTrue(self.problems("unsupported_not_in_code_set"))
        self.write("fake-c-two", unsupported=("U93.9",))
        self.assertEqual(len(self.problems("unsupported_not_in_code_set")), 2)

    def test_entry_given_twice(self):
        self.write(unsupported=("U96", "U96"))
        self.assertTrue(self.problems("bad_unsupported"))

    def test_entry_with_third_key(self):
        g = c_gold("fake-c-one")
        g["unsupported_codes"][0]["extra"] = "x"
        write_case(self.root, "fake-c-one", gold_obj=g)
        self.assertTrue(self.problems("bad_unsupported"))

    def test_entry_missing_reason(self):
        g = c_gold("fake-c-one", unsupported_codes=[{"code": "U96"}])
        write_case(self.root, "fake-c-one", gold_obj=g)
        self.assertTrue(self.problems("bad_unsupported"))

    def test_entry_empty_strings(self):
        g = c_gold("fake-c-one", unsupported_codes=[{"code": "U96", "reason": " "}])
        write_case(self.root, "fake-c-one", gold_obj=g)
        self.assertTrue(self.problems("bad_unsupported"))

    def test_entry_not_dotted(self):
        self.write(unsupported=("U930",))
        self.assertTrue(self.problems("bad_unsupported"))

    def test_gold_code_equal_to_entry(self):
        self.write(codes=("U95",), unsupported=("U95",))
        self.assertTrue(self.problems("unsupported_matches_code"))

    def test_gold_code_starts_with_entry(self):
        self.write(codes=("U93.1",), unsupported=("U93",))
        self.assertTrue(self.problems("unsupported_matches_code"))

    def test_gold_code_not_matching_is_fine(self):
        self.write(codes=("U93",), unsupported=("U93.1",))
        self.assertEqual(self.problems("unsupported_matches_code"), [])

    def test_optional_code_matches_entry(self):
        self.write(codes=("U95",), optional=("U94.0",), unsupported=("U94",))
        self.assertTrue(self.problems("unsupported_matches_optional"))


class TestMain(CFixture):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = validate.main(["--data-dir", str(self.root), *argv], data=self.data)
        return code, out.getvalue(), err.getvalue()

    def test_header_and_zero_files(self):
        for d in ("specs", "cases", "gold"):
            (self.root / d / "README.md").write_text("Invented readme.\n")
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith(f"Part C validation: {CODE_SET}\n"))
        self.assertIn("files: specs 0, cases 0, gold 0", out)
        self.assertTrue(out.rstrip().endswith("Result: PASS"))

    def test_exit_one_on_problem(self):
        self.write(unsupported=())
        code, out, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("Result: FAIL", out)

    def test_exit_two_missing_folder(self):
        (self.root / "gold").rmdir()
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("gold/", err)

    def test_default_data_dir(self):
        self.assertEqual(validate.SCHEMA.default_dir, "data/part_c")

    def test_module_entry_usage(self):
        p = subprocess.run([sys.executable, "-m", "medcode_eval.part_c.validate", "--invented"],
                           cwd=REPO_ROOT, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 2)

    def test_files_are_never_changed(self):
        self.write()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.run_main()
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_gold_json_roundtrip(self):
        self.write()
        g = json.loads((self.root / "gold" / "fake-c-one.json").read_text())
        self.assertNotIn("target_trap", g)


if __name__ == "__main__":
    unittest.main()
