"""Tests for medcode_eval.part_b.validate on invented fixtures.

The code set is the invented one of tests/test_checker.py (codes U90-U96,
made-up titles and notes); the real reference files hold none of them.
Every spec, case and gold file here is an obvious fake written to a
temporary directory that the tests remove. No network.
"""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from medcode_eval import checker
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT
from medcode_eval.part_b import validate
from tests.test_checker import FIXTURE_XML, ORDER_ROWS, PATHS, order_text

SPEC = """---
id: {id}
specialty: {specialty}
setting: invented fixture clinic
author: fixture-author
date: 2099-01-01
---
- Invented fact one for a fixture, not a real patient.
- Invented fact two.
"""

CASE = """---
id: {id}
specialty: {specialty}
setting: invented fixture clinic
origin: invented test fixture
drafter: fixture-drafter
draft_date: 2099-01-02
---
Invented note text for a fixture. Not a real patient.
"""


def gold(case_id, codes=("U92.0",), **over):
    g = {"id": case_id, "codes": codes if isinstance(codes, str) else list(codes),
         "optional_codes": [],
         "citations": {"case": "Invented guideline section 0.0"},
         "target_trap": "laterality", "coder_notes": "Invented fixture note.",
         "method": "coder_unassisted", "method_detail": "Invented fixture method detail.",
         "code_set": CODE_SET, "date_coded": "2099-01-03"}
    g.update(over)
    return g


def write_case(root, case_id, specialty="ortho", spec=None, case=None, gold_obj=None,
               parts=("spec", "case", "gold")):
    for d in ("specs", "cases", "gold"):
        (root / d).mkdir(exist_ok=True)
    if "spec" in parts:
        (root / "specs" / f"{case_id}.md").write_text(
            spec if spec is not None else SPEC.format(id=case_id, specialty=specialty),
            encoding="utf-8")
    if "case" in parts:
        (root / "cases" / f"{case_id}.md").write_text(
            case if case is not None else CASE.format(id=case_id, specialty=specialty),
            encoding="utf-8")
    if "gold" in parts:
        g = gold_obj if gold_obj is not None else gold(case_id)
        text = g if isinstance(g, str) else json.dumps(g, indent=2)
        (root / "gold" / f"{case_id}.json").write_text(text, encoding="utf-8")


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ref = tempfile.TemporaryDirectory()
        ref = Path(cls._ref.name)
        (ref / "ref").mkdir()
        (ref / PATHS["order"]).write_text(order_text(ORDER_ROWS), encoding="ascii")
        (ref / PATHS["tabular"]).write_text(FIXTURE_XML, encoding="utf-8")
        cls.data = checker.load(root=ref, paths=PATHS)

    @classmethod
    def tearDownClass(cls):
        cls._ref.cleanup()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for d in ("specs", "cases", "gold"):
            (self.root / d).mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def run_validate(self):
        return validate.validate(self.root, data=self.data)

    def assertProblem(self, result, kind, file=None):
        hits = [p for p in result.problems if p.kind == kind
                and (file is None or p.file == file)]
        self.assertTrue(hits, f"no {kind} problem for {file}: {result.problems}")
        return hits[0]


class TestClean(Fixture):
    def test_empty_folders(self):
        r = self.run_validate()
        self.assertEqual((r.problems, r.warnings, r.reviews), ([], [], []))
        self.assertEqual(r.case_ids, [])

    def test_clean_cases(self):
        write_case(self.root, "fake-case-one")
        write_case(self.root, "fake-case-two", specialty="ent",
                   gold_obj=gold("fake-case-two", ["U90.012A", "U95"],
                                 citations={"U90.012A": "Invented section 1.1",
                                            "U95": "Invented section 1.2"},
                                 target_trap="seventh_character"))
        r = self.run_validate()
        self.assertEqual(r.problems, [])
        self.assertEqual(r.warnings, [])
        self.assertEqual(r.reviews, [])
        self.assertEqual(r.case_ids, ["fake-case-one", "fake-case-two"])

    def test_readme_and_gitkeep_ignored(self):
        for d in ("specs", "cases", "gold"):
            (self.root / d / "README.md").write_text("# invented readme U92.0\n")
            (self.root / d / ".gitkeep").write_text("")
        r = self.run_validate()
        self.assertEqual(r.problems, [])

    def test_undotted_code_in_gold_is_accepted(self):
        write_case(self.root, "fake-case-one", gold_obj=gold("fake-case-one", ["u920"]))
        self.assertEqual(self.run_validate().problems, [])


class TestPairing(Fixture):
    def test_case_without_spec_or_gold(self):
        write_case(self.root, "fake-case-one", parts=("case",))
        r = self.run_validate()
        self.assertProblem(r, "missing_spec", "cases/fake-case-one.md")
        self.assertProblem(r, "missing_gold", "cases/fake-case-one.md")

    def test_spec_or_gold_without_case(self):
        write_case(self.root, "fake-case-one", parts=("spec",))
        write_case(self.root, "fake-case-two", parts=("gold",))
        r = self.run_validate()
        self.assertProblem(r, "missing_case", "specs/fake-case-one.md")
        self.assertProblem(r, "missing_case", "gold/fake-case-two.json")

    def test_bad_file_name(self):
        write_case(self.root, "Fake_Case")
        r = self.run_validate()
        self.assertProblem(r, "bad_id", "cases/Fake_Case.md")

    def test_stray_file(self):
        write_case(self.root, "fake-case-one")
        (self.root / "gold" / "fake-case-one.txt").write_text("invented")
        (self.root / "specs" / "sub").mkdir()
        r = self.run_validate()
        self.assertProblem(r, "stray_file", "gold/fake-case-one.txt")
        self.assertProblem(r, "stray_file", "specs/sub")

    def test_id_field_must_match_file_name(self):
        write_case(self.root, "fake-case-one",
                   spec=SPEC.format(id="fake-case-other", specialty="ortho"),
                   gold_obj=gold("fake-case-other"))
        r = self.run_validate()
        self.assertProblem(r, "id_mismatch", "specs/fake-case-one.md")
        self.assertProblem(r, "id_mismatch", "gold/fake-case-one.json")

    def test_specialty_and_setting_must_agree(self):
        write_case(self.root, "fake-case-one",
                   case=CASE.format(id="fake-case-one", specialty="gi"))
        r = self.run_validate()
        self.assertProblem(r, "spec_case_mismatch", "cases/fake-case-one.md")


class TestFrontMatter(Fixture):
    def test_missing_front_matter(self):
        write_case(self.root, "fake-case-one", spec="- invented fact only\n")
        r = self.run_validate()
        self.assertProblem(r, "front_matter", "specs/fake-case-one.md")

    def test_missing_field(self):
        text = CASE.format(id="fake-case-one", specialty="ortho").replace(
            "drafter: fixture-drafter\n", "")
        write_case(self.root, "fake-case-one", case=text)
        p = self.assertProblem(self.run_validate(), "missing_field", "cases/fake-case-one.md")
        self.assertIn("drafter", p.message)

    def test_empty_field(self):
        text = SPEC.format(id="fake-case-one", specialty="ortho").replace(
            "author: fixture-author", "author:   ")
        write_case(self.root, "fake-case-one", spec=text)
        self.assertProblem(self.run_validate(), "missing_field", "specs/fake-case-one.md")

    def test_unknown_and_duplicate_field(self):
        text = SPEC.format(id="fake-case-one", specialty="ortho").replace(
            "date: 2099-01-01\n", "date: 2099-01-01\ntrap: invented\nauthor: again\n")
        write_case(self.root, "fake-case-one", spec=text)
        r = self.run_validate()
        self.assertProblem(r, "unknown_field", "specs/fake-case-one.md")
        self.assertProblem(r, "duplicate_field", "specs/fake-case-one.md")

    def test_bad_specialty(self):
        write_case(self.root, "fake-case-one", specialty="cardio")
        r = self.run_validate()
        self.assertProblem(r, "bad_enum", "specs/fake-case-one.md")
        self.assertProblem(r, "bad_enum", "cases/fake-case-one.md")

    def test_bad_date(self):
        text = CASE.format(id="fake-case-one", specialty="ortho").replace(
            "2099-01-02", "2099-13-40")
        write_case(self.root, "fake-case-one", case=text)
        self.assertProblem(self.run_validate(), "bad_date", "cases/fake-case-one.md")

    def test_spec_needs_a_list(self):
        text = SPEC.format(id="fake-case-one", specialty="ortho").replace("- Invented", "Invented")
        write_case(self.root, "fake-case-one", spec=text)
        self.assertProblem(self.run_validate(), "empty_body", "specs/fake-case-one.md")

    def test_case_needs_note_text(self):
        text = CASE.format(id="fake-case-one", specialty="ortho").split("---\n")
        write_case(self.root, "fake-case-one", case="---\n".join(text[:2]) + "---\n\n")
        self.assertProblem(self.run_validate(), "empty_body", "cases/fake-case-one.md")


class TestGoldFields(Fixture):
    def test_invalid_json(self):
        write_case(self.root, "fake-case-one", gold_obj="{invented")
        self.assertProblem(self.run_validate(), "bad_json", "gold/fake-case-one.json")

    def test_not_an_object(self):
        write_case(self.root, "fake-case-one", gold_obj="[]")
        self.assertProblem(self.run_validate(), "bad_json", "gold/fake-case-one.json")

    def test_missing_and_unknown_field(self):
        g = gold("fake-case-one")
        del g["coder_notes"]
        g["extra"] = 1
        write_case(self.root, "fake-case-one", gold_obj=g)
        r = self.run_validate()
        self.assertProblem(r, "missing_field", "gold/fake-case-one.json")
        self.assertProblem(r, "unknown_field", "gold/fake-case-one.json")

    def test_bad_trap(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", target_trap="invented_trap"))
        self.assertProblem(self.run_validate(), "bad_enum", "gold/fake-case-one.json")

    def test_wrong_release_label(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", code_set="ICD-10-CM FY2099"))
        self.assertProblem(self.run_validate(), "bad_code_set", "gold/fake-case-one.json")

    def test_bad_date_coded(self):
        write_case(self.root, "fake-case-one", gold_obj=gold("fake-case-one", date_coded="soon"))
        self.assertProblem(self.run_validate(), "bad_date", "gold/fake-case-one.json")

    def test_bad_codes_shape(self):
        for codes in ([], "U92.0", ["U92.0", 7], ["U92.0", " "]):
            with self.subTest(codes=codes):
                write_case(self.root, "fake-case-one",
                           gold_obj=gold("fake-case-one", codes=codes))
                self.assertProblem(self.run_validate(), "bad_codes", "gold/fake-case-one.json")

    def test_duplicate_code(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U92.0", "u920"]))
        self.assertProblem(self.run_validate(), "bad_codes", "gold/fake-case-one.json")

    def test_empty_citation(self):
        for cit in ({"case": "  "}, {"U92.0": ""}, {}, "invented", {"case": 3}):
            with self.subTest(citations=cit):
                write_case(self.root, "fake-case-one",
                           gold_obj=gold("fake-case-one", citations=cit))
                self.assertProblem(self.run_validate(), "bad_citation",
                                   "gold/fake-case-one.json")

    def test_citation_missing_for_a_code(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U92.0", "U95"],
                                 citations={"U92.0": "Invented section 1.1"}))
        p = self.assertProblem(self.run_validate(), "bad_citation", "gold/fake-case-one.json")
        self.assertIn("U95", p.message)

    def test_citation_for_a_code_not_listed(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one",
                                 citations={"case": "Invented 1", "U96": "Invented 2"}))
        self.assertProblem(self.run_validate(), "bad_citation", "gold/fake-case-one.json")

    def test_per_code_citation_matches_undotted_form(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U92.0"],
                                 citations={"U920": "Invented section 1.1"}))
        self.assertEqual(self.run_validate().problems, [])

    def test_coder_notes_must_be_a_string(self):
        write_case(self.root, "fake-case-one", gold_obj=gold("fake-case-one", coder_notes=None))
        self.assertProblem(self.run_validate(), "bad_type", "gold/fake-case-one.json")

    def test_empty_coder_notes_allowed(self):
        write_case(self.root, "fake-case-one", gold_obj=gold("fake-case-one", coder_notes=""))
        self.assertEqual(self.run_validate().problems, [])

    def test_both_methods_accepted(self):
        for m in ("ai_assisted_coder_verified", "coder_unassisted"):
            with self.subTest(method=m):
                write_case(self.root, "fake-case-one",
                           gold_obj=gold("fake-case-one", method=m))
                self.assertEqual(self.run_validate().problems, [])

    def test_method_fields_required(self):
        for k in ("method", "method_detail"):
            with self.subTest(field=k):
                g = gold("fake-case-one")
                del g[k]
                write_case(self.root, "fake-case-one", gold_obj=g)
                p = self.assertProblem(self.run_validate(), "missing_field",
                                       "gold/fake-case-one.json")
                self.assertIn(k, p.message)

    def test_bad_method(self):
        for m in ("invented_method", "AI_ASSISTED_CODER_VERIFIED"):
            with self.subTest(method=m):
                write_case(self.root, "fake-case-one",
                           gold_obj=gold("fake-case-one", method=m))
                p = self.assertProblem(self.run_validate(), "bad_enum",
                                       "gold/fake-case-one.json")
                self.assertIn("method", p.message)

    def test_empty_method_detail(self):
        for v in ("", "   "):
            with self.subTest(method_detail=v):
                write_case(self.root, "fake-case-one",
                           gold_obj=gold("fake-case-one", method_detail=v))
                p = self.assertProblem(self.run_validate(), "missing_field",
                                       "gold/fake-case-one.json")
                self.assertIn("method_detail", p.message)

    def test_method_fields_must_be_strings(self):
        for k, v in (("method", None), ("method", 1), ("method_detail", None),
                     ("method_detail", ["invented"])):
            with self.subTest(field=k, value=v):
                write_case(self.root, "fake-case-one", gold_obj=gold("fake-case-one", **{k: v}))
                self.assertProblem(self.run_validate(), "bad_type", "gold/fake-case-one.json")


class TestGoldChecker(Fixture):
    def test_error_findings_are_problems(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U90", "U99.9", "U91.1"]))
        r = self.run_validate()
        rules = sorted(p.rule for p in r.problems if p.kind == "checker_error")
        self.assertEqual(rules, ["header_not_billable", "not_in_code_set"])

    def test_manifestation_first(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U91.1", "U92.0"]))
        r = self.run_validate()
        self.assertEqual([p.rule for p in r.problems], ["manifestation_first"])

    def test_order_is_passed_to_the_checker(self):
        # codeFirst U92.0 on U91.1: a review when U92.0 is listed after U91.1
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U92.0", "U91.1"]))
        r = self.run_validate()
        self.assertEqual((r.problems, r.reviews), ([], []))

    def test_review_findings_are_not_problems(self):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes=["U91.0", "U92.1"]))
        r = self.run_validate()
        self.assertEqual(r.problems, [])
        self.assertEqual([x.rule for x in r.reviews], ["excludes1_pair"])
        self.assertEqual(r.reviews[0].file, "gold/fake-case-one.json")


def opt(*codes):
    return [{"code": c, "reason": f"Invented reason for {c}."} for c in codes]


class TestOptionalCodes(Fixture):
    F = "gold/fake-case-one.json"

    def write(self, optional, codes=("U92.0",), **over):
        write_case(self.root, "fake-case-one",
                   gold_obj=gold("fake-case-one", codes, optional_codes=optional, **over))
        return self.run_validate()

    def assertOptionalProblem(self, optional, **kw):
        return self.assertProblem(self.write(optional, **kw), "bad_optional", self.F)

    def test_field_is_required(self):
        g = gold("fake-case-one")
        del g["optional_codes"]
        write_case(self.root, "fake-case-one", gold_obj=g)
        p = self.assertProblem(self.run_validate(), "missing_field", self.F)
        self.assertIn("optional_codes", p.message)

    def test_empty_list_and_valid_entries_accepted(self):
        for optional in ([], opt("U95"), opt("U95", "U94.0")):
            with self.subTest(optional=optional):
                r = self.write(optional, codes=("U94.1",))
                self.assertEqual((r.problems, r.reviews), ([], []))

    def test_not_a_list(self):
        for optional in ("U95", None, {}, {"code": "U95", "reason": "x"}):
            with self.subTest(optional=optional):
                self.assertOptionalProblem(optional)

    def test_bad_entries(self):
        for entry in ("U95", ["U95"], {"code": "U95"}, {"reason": "Invented."},
                      {"code": "U95", "reason": "Invented.", "extra": 1},
                      {"code": "", "reason": "Invented."}, {"code": "  ", "reason": "Invented."},
                      {"code": "U95", "reason": ""}, {"code": "U95", "reason": "  "},
                      {"code": 95, "reason": "Invented."}, {"code": "U95", "reason": None}):
            with self.subTest(entry=entry):
                self.assertOptionalProblem([entry])

    def test_code_must_be_dotted_form(self):
        for code in ("U920", "u92.0", " U92.0"):
            with self.subTest(code=code):
                p = self.assertOptionalProblem(opt(code), codes=("U95",))
                self.assertIn("dotted", p.message)

    def test_code_given_twice(self):
        p = self.assertOptionalProblem(opt("U95", "U95"))
        self.assertIn("U95", p.message)

    def test_code_also_in_codes(self):
        for codes in (("U92.0",), ("u920",)):
            with self.subTest(codes=codes):
                p = self.assertOptionalProblem(opt("U92.0"), codes=codes)
                self.assertIn("U92.0", p.message)

    def test_citation_key_may_not_name_an_optional_code(self):
        for key in ("U95", "u95"):
            with self.subTest(key=key):
                r = self.write(opt("U95"), citations={"case": "Invented 1", key: "Invented 2"})
                p = self.assertProblem(r, "bad_citation", self.F)
                self.assertIn("optional", p.message)

    def test_error_finding_on_optional_code_is_problem(self):
        r = self.write(opt("U90", "U99.9"), codes=("U95",))
        rules = sorted(p.rule for p in r.problems if p.kind == "checker_error")
        self.assertEqual(rules, ["header_not_billable", "not_in_code_set"])

    def test_optional_codes_checked_after_codes(self):
        # U91.1 is a manifestation: an error only when first-listed
        r = self.write(opt("U91.1"), codes=("U92.0",))
        self.assertEqual((r.problems, r.reviews), ([], []))

    def test_error_on_codes_not_repeated(self):
        r = self.write(opt("U95"), codes=("U90",))
        self.assertEqual([p.rule for p in r.problems], ["header_not_billable"])

    def test_review_finding_with_optional_code_is_listed(self):
        r = self.write(opt("U92.1"), codes=("U91.0",))
        self.assertEqual(r.problems, [])
        self.assertEqual([x.rule for x in r.reviews], ["excludes1_pair"])
        self.assertEqual(r.reviews[0].file, self.F)

    def test_review_on_codes_not_repeated(self):
        r = self.write(opt("U94.0"), codes=("U91.0", "U92.1"))
        self.assertEqual(r.problems, [])
        self.assertEqual([x.rule for x in r.reviews], ["excludes1_pair"])


class TestCodesInText(Fixture):
    def test_dotted_stored_code_is_problem(self):
        text = CASE.format(id="fake-case-one", specialty="ortho") + "Invented: U92.0 seen.\n"
        write_case(self.root, "fake-case-one", case=text)
        p = self.assertProblem(self.run_validate(), "code_in_text", "cases/fake-case-one.md")
        self.assertIn("U92.0", p.message)
        self.assertIn("line 10", p.message)

    def test_dotted_prefix_of_stored_codes_is_problem(self):
        text = SPEC.format(id="fake-case-one", specialty="ortho") + "- invented u90.01 lower case\n"
        write_case(self.root, "fake-case-one", spec=text)
        self.assertProblem(self.run_validate(), "code_in_text", "specs/fake-case-one.md")

    def test_dotted_wildcard_is_problem(self):
        text = SPEC.format(id="fake-case-one", specialty="ortho") + "- invented U93.-\n"
        write_case(self.root, "fake-case-one", spec=text)
        self.assertProblem(self.run_validate(), "code_in_text", "specs/fake-case-one.md")

    def test_dotted_unknown_string_is_not_flagged(self):
        text = CASE.format(id="fake-case-one", specialty="ortho") + "Invented U99.9 and U92.9.\n"
        write_case(self.root, "fake-case-one", case=text)
        r = self.run_validate()
        self.assertEqual((r.problems, r.warnings), ([], []))

    def test_undotted_category_is_warning(self):
        text = CASE.format(id="fake-case-one", specialty="ortho") + "Invented level U95-U96 and U92.\n"
        write_case(self.root, "fake-case-one", case=text)
        r = self.run_validate()
        self.assertEqual(r.problems, [])
        self.assertEqual(len(r.warnings), 2)
        self.assertTrue(all(w.kind == "category_in_text" for w in r.warnings))

    def test_undotted_non_category_is_not_flagged(self):
        # U900 is a stored code but not a category; U99 is not stored
        text = CASE.format(id="fake-case-one", specialty="ortho") + "Invented U900 and U99.\n"
        write_case(self.root, "fake-case-one", case=text)
        r = self.run_validate()
        self.assertEqual((r.problems, r.warnings), ([], []))


class TestMain(Fixture):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = validate.main(["--data-dir", str(self.root), *argv], data=self.data)
        return code, out.getvalue(), err.getvalue()

    def test_exit_zero_clean(self):
        write_case(self.root, "fake-case-one")
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("Problems: 0", out)
        self.assertIn(CODE_SET, out)

    def test_exit_zero_with_warnings_and_reviews(self):
        text = CASE.format(id="fake-case-one", specialty="ortho") + "Invented U95.\n"
        write_case(self.root, "fake-case-one", case=text,
                   gold_obj=gold("fake-case-one", codes=["U91.0", "U92.1"]))
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("Warnings: 1", out)
        self.assertIn("Checker review findings (not problems): 1", out)

    def test_exit_one_on_problem(self):
        write_case(self.root, "fake-case-one", parts=("case",))
        code, out, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("missing_spec", out)

    def test_exit_two_missing_folder(self):
        (self.root / "gold").rmdir()
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("gold", err)

    def test_exit_two_bad_argument(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(validate.main(["--invented"], data=self.data), 2)

    def test_exit_two_missing_refdata(self):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = validate.main(["--data-dir", str(self.root)], ref_root=self.root)
        self.assertEqual(code, 2)
        self.assertIn("reference data", err.getvalue())

    def test_module_entry_usage(self):
        p = subprocess.run([sys.executable, "-m", "medcode_eval.part_b.validate", "--invented"],
                           cwd=REPO_ROOT, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 2)

    def test_files_are_never_changed(self):
        write_case(self.root, "fake-case-one", parts=("case", "gold"),
                   gold_obj=gold("fake-case-one", codes=["U90"]))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.run_main()
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
