"""Tests for medcode_eval.checker (and the two helpers it adds to
medcode_eval.tabular) on an invented fixture.

Every fixture is invented: codes U90-U96, made-up titles and notes. The
fixture files live in a temporary directory that the tests remove. No
network.
"""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from medcode_eval import checker, tabular
from medcode_eval.part_a.generate import REPO_ROOT

FIXTURE_XML = """<?xml version="1.0" encoding="utf-8"?>
<ICD10CM.tabular>
  <version>2099</version>
  <introduction>
    <introSection type="notes"><title>Invented</title>
      <instruction><note>Invented instruction that is not about manifestations.</note></instruction>
      <instruction><note>In most cases the manifestation codes will have in the code title, 'in diseases classified elsewhere.' Invented: such codes are never first listed.</note></instruction>
    </introSection>
  </introduction>
  <chapter>
    <name>1</name>
    <desc>Invented chapter (U90-U96)</desc>
    <section id="U90-U94">
      <desc>Invented section (U90-U94)</desc>
      <diag>
        <name>U90</name>
        <desc>Invented category with a 7th character</desc>
        <sevenChrDef>
          <extension char="A">initial</extension>
          <extension char="D">subsequent</extension>
          <extension char="S">sequela</extension>
        </sevenChrDef>
        <diag>
          <name>U90.0</name>
          <desc>Invented subcategory</desc>
          <diag>
            <name>U90.01</name>
            <desc>Invented subcategory two</desc>
            <diag>
              <name>U90.012</name>
              <desc>Invented six-character leaf</desc>
            </diag>
          </diag>
        </diag>
        <diag placeholder="true">
          <name>U90.1</name>
          <desc>Invented short leaf needing X padding</desc>
        </diag>
      </diag>
      <diag>
        <name>U91</name>
        <desc>Invented category two</desc>
        <diag>
          <name>U91.0</name>
          <desc>Invented code with excludes1 notes</desc>
          <excludes1>
            <note>invented other (U92.1)</note>
            <note>invented qualified (U93.-) except with seventh character 5</note>
            <note>invented free text see U96</note>
            <note>invented own category (U91.-)</note>
          </excludes1>
        </diag>
        <diag>
          <name>U91.1</name>
          <desc>Invented manifestation in diseases classified elsewhere</desc>
          <codeFirst>
            <note>underlying invented disease (U92.0)</note>
          </codeFirst>
        </diag>
      </diag>
      <diag>
        <name>U92</name>
        <desc>Invented category three</desc>
        <diag><name>U92.0</name><desc>Invented etiology</desc></diag>
        <diag><name>U92.1</name><desc>Invented excluded</desc></diag>
      </diag>
      <diag>
        <name>U93</name>
        <desc>Invented category four</desc>
        <excludes1><note>invented sibling (U93.-)</note></excludes1>
        <codeFirst>
          <note>invented range (U95-U96)</note>
          <note>invented underlying U92.1</note>
        </codeFirst>
        <diag><name>U93.0</name><desc>Invented four zero</desc></diag>
        <diag><name>U93.1</name><desc>Invented four one</desc></diag>
      </diag>
      <diag>
        <name>U94</name>
        <desc>Invented category with eleven children</desc>
CHILDREN_U94
      </diag>
    </section>
    <section id="U95-U96">
      <desc>Invented section two (U95-U96)</desc>
      <excludes1><note>invented section range (U92.0-U92.1)</note></excludes1>
      <diag><name>U95</name><desc>Invented three-character code</desc></diag>
      <diag><name>U96</name><desc>Invented three-character code two</desc></diag>
    </section>
  </chapter>
</ICD10CM.tabular>
"""

U94_KIDS = [f"U94.{c}" for c in "0123456789A"]
FIXTURE_XML = FIXTURE_XML.replace("CHILDREN_U94", "\n".join(
    f"        <diag><name>{n}</name><desc>Invented child {n}</desc></diag>" for n in U94_KIDS))

# (code, billable, long description)
ORDER_ROWS = [
    ("U90", 0, "Invented category with a 7th character"),
    ("U900", 0, "Invented subcategory"),
    ("U9001", 0, "Invented subcategory two"),
    ("U90012", 0, "Invented six-character leaf"),
    ("U90012A", 1, "Invented six-character leaf, initial"),
    ("U90012D", 1, "Invented six-character leaf, subsequent"),
    ("U90012S", 1, "Invented six-character leaf, sequela"),
    ("U901", 0, "Invented short leaf needing X padding"),
    ("U901XXA", 1, "Invented short leaf, initial"),
    ("U901XXD", 1, "Invented short leaf, subsequent"),
    ("U901XXS", 1, "Invented short leaf, sequela"),
    ("U91", 0, "Invented category two"),
    ("U910", 1, "Invented code with excludes1 notes"),
    ("U911", 1, "Invented manifestation in diseases classified elsewhere"),
    ("U92", 0, "Invented category three"),
    ("U920", 1, "Invented etiology"),
    ("U921", 1, "Invented excluded"),
    ("U93", 0, "Invented category four"),
    ("U930", 1, "Invented four zero"),
    ("U931", 1, "Invented four one"),
    ("U94", 0, "Invented category with eleven children"),
] + [(n.replace(".", ""), 1, f"Invented child {n}") for n in U94_KIDS] + [
    ("U95", 1, "Invented three-character code"),
    ("U96", 1, "Invented three-character code two"),
]


def order_text(rows):
    return "".join(f"{i:05d} {c:<7} {b} {d[:60]:<60} {d}\n"
                   for i, (c, b, d) in enumerate(rows, start=1))


PATHS = {"order": Path("ref") / "order.txt", "tabular": Path("ref") / "tabular.xml"}


class FixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        (root / "ref").mkdir()
        (root / PATHS["order"]).write_text(order_text(ORDER_ROWS), encoding="ascii")
        (root / PATHS["tabular"]).write_text(FIXTURE_XML, encoding="utf-8")
        cls.root = root
        cls.data = checker.load(root=root, paths=PATHS)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_check(self, *codes):
        return checker.check(list(codes), data=self.data)

    def rules(self, findings):
        return [f["rule"] for f in findings]

    def only(self, findings, rule):
        hits = [f for f in findings if f["rule"] == rule]
        self.assertEqual(len(hits), 1, findings)
        return hits[0]


class TestTabularHelpers(unittest.TestCase):
    def test_split_by_parentheses(self):
        inside, outside = tabular.split_by_parentheses(
            "a (U92.1, U93.-) see U96 and (b (U95-U96)) then U97")
        self.assertEqual([r.text for r in inside], ["U92.1", "U93.-", "U95-U96"])
        self.assertEqual([r.text for r in outside], ["U96", "U97"])

    def test_split_unbalanced_close_does_not_go_negative(self):
        inside, outside = tabular.split_by_parentheses("x) U90 (U91)")
        self.assertEqual([r.text for r in inside], ["U91"])
        self.assertEqual([r.text for r in outside], ["U90"])

    def test_reference_matches(self):
        ref = lambda t: tabular.find_references(t)[0]
        self.assertTrue(tabular.reference_matches(ref("U92.1"), "U921"))
        self.assertFalse(tabular.reference_matches(ref("U92.1"), "U9210"))
        self.assertTrue(tabular.reference_matches(ref("U93.-"), "U931"))
        self.assertFalse(tabular.reference_matches(ref("U93.-"), "U941"))
        self.assertTrue(tabular.reference_matches(ref("U95-U96"), "U96"))
        self.assertTrue(tabular.reference_matches(ref("U95-U96"), "U9612"))
        self.assertFalse(tabular.reference_matches(ref("U95-U96"), "U97"))
        self.assertTrue(tabular.reference_matches(ref("U92.0-U92.1"), "U9219XA"))
        self.assertFalse(tabular.reference_matches(ref("U92.0-U92.1"), "U922"))
        self.assertFalse(tabular.reference_matches(ref("U92.0-U92.1"), "U92"))
        # category order puts digits before letters, as chapter_of does
        self.assertTrue(tabular.reference_matches(ref("O00-O9A"), "O99"))
        self.assertTrue(tabular.reference_matches(ref("O00-O9A"), "O9A1"))
        self.assertFalse(tabular.reference_matches(ref("O00-O9A"), "P00"))


class TestNormalise(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(checker.normalise("u91.0"), "U910")
        self.assertEqual(checker.normalise("U910"), "U910")
        self.assertEqual(checker.normalise(" u91.0 "), "U910")
        self.assertEqual(checker.normalise("U90.012a"), "U90012A")
        self.assertEqual(checker.normalise("u91"), "U91")

    def test_misplaced_dot_is_kept(self):
        self.assertEqual(checker.normalise("U9.10"), "U9.10")
        self.assertEqual(checker.normalise("U91."), "U91.")
        self.assertEqual(checker.normalise("U91.0.1"), "U91.0.1")

    def test_empty_is_usage_error(self):
        for s in ("", "   "):
            with self.assertRaises(checker.UsageError):
                checker.normalise(s)


class TestNotInCodeSet(FixtureCase):
    def test_no_stored_prefix(self):
        f = self.only(self.run_check("U99"), "not_in_code_set")
        self.assertEqual(f["level"], "error")
        self.assertEqual(f["codes"], ["U99"])
        self.assertIsNone(f["details"]["longest_stored_prefix"])

    def test_prefix_billable(self):
        f = self.only(self.run_check("U9109"), "not_in_code_set")
        self.assertEqual(f["details"]["longest_stored_prefix"],
                         {"code": "U91.0", "billable": True})
        self.assertNotIn("allowed_7th_characters", f["details"])
        self.assertNotIn("padded_code", f["details"])

    def test_prefix_header(self):
        f = self.only(self.run_check("U900Z"), "not_in_code_set")
        self.assertEqual(f["details"]["longest_stored_prefix"],
                         {"code": "U90.0", "billable": False})
        self.assertNotIn("allowed_7th_characters", f["details"])

    def test_seventh_character_not_allowed(self):
        f = self.only(self.run_check("U90.012Z"), "not_in_code_set")
        self.assertEqual(f["details"]["allowed_7th_characters"], ["A", "D", "S"])
        self.assertEqual(f["details"]["longest_stored_prefix"],
                         {"code": "U90.012", "billable": False})
        self.assertIn({"file": "ref/tabular.xml", "element": "sevenChrDef",
                       "owner_type": "diag", "owner": "U90",
                       "extensions": [["A", "initial"], ["D", "subsequent"],
                                      ["S", "sequela"]]}, f["source"])

    def test_seventh_character_allowed_no_listing(self):
        # 7 characters, allowed 7th character, but not stored
        f = self.only(self.run_check("U9001ZA"), "not_in_code_set")
        self.assertNotIn("allowed_7th_characters", f["details"])

    def test_missing_x_padding(self):
        f = self.only(self.run_check("U901A"), "not_in_code_set")
        self.assertEqual(f["details"]["padded_code"], "U90.1XXA")
        self.assertIn("U90.1XXA", f["message"])

    def test_padding_not_offered_when_padded_code_not_stored(self):
        f = self.only(self.run_check("U9001A"), "not_in_code_set")
        self.assertNotIn("padded_code", f["details"])

    def test_padding_not_offered_for_char_not_allowed(self):
        f = self.only(self.run_check("U901Z"), "not_in_code_set")
        self.assertNotIn("padded_code", f["details"])

    def test_misplaced_dot(self):
        f = self.only(self.run_check("U9.10"), "not_in_code_set")
        self.assertEqual(f["codes"], ["U9.10"])

    def test_order_file_source(self):
        f = self.only(self.run_check("U99"), "not_in_code_set")
        self.assertEqual(f["source"][0]["file"], "ref/order.txt")


class TestHeader(FixtureCase):
    def test_seventh_character_needed_no_padding(self):
        f = self.only(self.run_check("U90.012"), "header_not_billable")
        d = f["details"]
        self.assertEqual(f["level"], "error")
        self.assertEqual(d["case"], "seventh_character_needed")
        self.assertEqual(d["allowed_7th_characters"], ["A", "D", "S"])
        self.assertEqual(d["seventh_character_from"], "U90")
        self.assertFalse(d["x_padding_needed"])

    def test_seventh_character_needed_with_padding(self):
        f = self.only(self.run_check("U90.1"), "header_not_billable")
        d = f["details"]
        self.assertEqual(d["case"], "seventh_character_needed")
        self.assertTrue(d["x_padding_needed"])
        self.assertEqual(d["padded_base"], "U90.1XX")
        self.assertIn("X", f["message"])

    def test_seventh_character_case_lists_children_when_present(self):
        d = self.only(self.run_check("U90"), "header_not_billable")["details"]
        self.assertEqual(d["case"], "seventh_character_needed")
        self.assertEqual(d["children"], ["U90.0", "U90.1"])

    def test_more_specific_codes(self):
        f = self.only(self.run_check("U91"), "header_not_billable")
        d = f["details"]
        self.assertEqual(d["case"], "more_specific_codes")
        self.assertEqual(d["children"], ["U91.0", "U91.1"])
        self.assertEqual(d["children_total"], 2)
        self.assertNotIn("allowed_7th_characters", d)

    def test_children_capped_at_ten(self):
        d = self.only(self.run_check("U94"), "header_not_billable")["details"]
        self.assertEqual(d["children"], U94_KIDS[:10])
        self.assertEqual(d["children_total"], 11)

    def test_billable_alone_no_finding(self):
        self.assertEqual(self.run_check("U90.012A"), [])
        self.assertEqual(self.run_check("U95"), [])


class TestManifestation(FixtureCase):
    def test_first_listed(self):
        f = self.only(self.run_check("U91.1"), "manifestation_first")
        self.assertEqual(f["level"], "error")
        self.assertEqual(f["codes"], ["U911"])
        kinds = [(s["file"], s["element"]) for s in f["source"]]
        self.assertEqual(kinds, [("ref/order.txt", "long description"),
                                 ("ref/tabular.xml", "instruction"),
                                 ("ref/tabular.xml", "codeFirst")])
        self.assertIn("in diseases classified elsewhere", f["source"][0]["text"])
        self.assertTrue(f["source"][1]["text"].startswith("In most cases"))
        self.assertEqual(f["source"][2]["text"], "underlying invented disease (U92.0)")
        self.assertEqual(f["source"][2]["owner"], "U91.1")

    def test_not_first_listed(self):
        self.assertNotIn("manifestation_first", self.rules(self.run_check("U92.0", "U91.1")))


class TestExcludes1(FixtureCase):
    def test_exact(self):
        for codes in (("U91.0", "U92.1"), ("U92.1", "U91.0")):
            f = self.only(self.run_check(*codes), "excludes1_pair")
            self.assertEqual(f["level"], "review")
            self.assertEqual(f["codes"], ["U910", "U921"])
            self.assertFalse(f["qualified"])
            self.assertEqual(f["source"][0]["text"], "invented other (U92.1)")
            self.assertEqual(f["source"][0]["owner_type"], "diag")
            self.assertEqual(f["source"][0]["owner"], "U91.0")

    def test_exact_does_not_match_other_code(self):
        self.assertEqual(self.run_check("U91.0", "U92.0"), [])

    def test_prefix_and_qualified(self):
        f = self.only(self.run_check("U91.0", "U93.0"), "excludes1_pair")
        self.assertTrue(f["qualified"])
        self.assertEqual(f["details"]["reference"], "U93.-")

    def test_prefix_own_category(self):
        f = self.only(self.run_check("U91.0", "U91.1"), "excludes1_pair")
        self.assertEqual(f["details"]["reference"], "U91.-")

    def test_never_with_itself(self):
        self.assertEqual(self.run_check("U91.0", "U91.0"), [])
        self.assertEqual(self.run_check("U91.0", "u910"), [])

    def test_one_finding_per_pair_and_note(self):
        # the U93 note is in scope of both codes and matches each
        f = self.only(self.run_check("U93.0", "U93.1"), "excludes1_pair")
        self.assertEqual(f["source"][0]["owner"], "U93")

    def test_section_range(self):
        f = self.only(self.run_check("U95", "U92.0"), "excludes1_pair")
        self.assertEqual(f["source"][0]["owner_type"], "section")
        self.assertEqual(f["source"][0]["owner"], "U95-U96")
        self.assertEqual(f["details"]["reference"], "U92.0-U92.1")

    def test_reference_outside_parentheses_ignored(self):
        self.assertEqual(self.run_check("U91.0", "U96"), [])

    def test_not_stored_codes_skipped(self):
        self.assertEqual(self.rules(self.run_check("U91.0", "U92.1Q")), ["not_in_code_set"])


class TestCodeFirst(FixtureCase):
    def test_listed_after(self):
        f = self.only(self.run_check("U93.0", "U96"), "code_first_order")
        self.assertEqual(f["level"], "review")
        self.assertEqual(f["codes"], ["U930", "U96"])
        self.assertEqual(f["source"][0]["element"], "codeFirst")
        self.assertEqual(f["source"][0]["text"], "invented range (U95-U96)")

    def test_listed_before(self):
        self.assertEqual(self.run_check("U96", "U93.0"), [])

    def test_with_manifestation(self):
        rules = self.rules(self.run_check("U91.1", "U92.0"))
        self.assertEqual(sorted(rules), ["code_first_order", "manifestation_first"])

    def test_reference_outside_parentheses_ignored(self):
        self.assertEqual(self.run_check("U93.0", "U92.1"), [])


class TestParenthesisCounts(FixtureCase):
    def test_counts(self):
        c = checker.parenthesis_counts(self.data)
        self.assertEqual(c["excludes1"]["outside_resolvable"], 1)
        self.assertEqual(c["excludes1"]["examples"][0]["reference"], "U96")
        self.assertEqual(c["codeFirst"]["outside_resolvable"], 1)
        self.assertEqual(c["codeFirst"]["examples"][0]["reference"], "U92.1")
        self.assertEqual(c["excludes1"]["inside"], 5)
        self.assertEqual(c["codeFirst"]["inside"], 2)


class TestCli(FixtureCase):
    def run_main(self, argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(argv, **kw)
        return code, out.getvalue(), err.getvalue()

    def test_json_shape(self):
        code, out, _ = self.run_main(["u91.0", "U92.1"], data=self.data)
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(set(doc), {"code_set", "tabular_version", "codes_given",
                                    "codes_normalised", "findings"})
        self.assertEqual(doc["code_set"], checker.CODE_SET)
        self.assertEqual(doc["tabular_version"], "2099")
        self.assertEqual(doc["codes_given"], ["u91.0", "U92.1"])
        self.assertEqual(doc["codes_normalised"], ["U910", "U921"])
        f = doc["findings"][0]
        for key in ("rule", "level", "codes", "message", "source"):
            self.assertIn(key, f)

    def test_exit_zero_clean(self):
        self.assertEqual(self.run_main(["U95"], data=self.data)[0], 0)

    def test_exit_one_on_error(self):
        self.assertEqual(self.run_main(["U91"], data=self.data)[0], 1)

    def test_exit_two_no_codes(self):
        self.assertEqual(self.run_main([], data=self.data)[0], 2)

    def test_exit_two_empty_code(self):
        self.assertEqual(self.run_main(["U95", " "], data=self.data)[0], 2)

    def test_exit_two_missing_refdata(self):
        with tempfile.TemporaryDirectory() as empty:
            code, out, err = self.run_main(["U95"], root=Path(empty), paths=PATHS)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err)

    def test_module_entry_usage(self):
        p = subprocess.run([sys.executable, "-m", "medcode_eval.checker"],
                           cwd=REPO_ROOT, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 2)


class TestLoadOnce(unittest.TestCase):
    def test_default_data_cached(self):
        calls = []
        real = checker.load
        try:
            checker._DEFAULT = None
            checker.load = lambda: calls.append(1) or "sentinel"
            self.assertEqual(checker.default_data(), "sentinel")
            self.assertEqual(checker.default_data(), "sentinel")
        finally:
            checker.load = real
            checker._DEFAULT = None
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
