"""Tests for the tabular tree, note references and 7th-character parsing in
medcode_eval.tabular, and for medcode_eval.tabular_survey.

Every fixture is invented: codes U9x and Q9x, made-up titles and notes.
No network.
"""

import tempfile
import unittest
from pathlib import Path

from medcode_eval import tabular, tabular_survey
from medcode_eval.tabular import (
    Reference,
    TabularError,
    classify_note,
    diag_level,
    element_census,
    find_references,
    load_tree,
    prefix_set,
    reference_resolves,
    scope_of,
    seven_chr_source,
)

FIXTURE_XML = """<?xml version="1.0" encoding="utf-8"?>
<ICD10CM.tabular>
  <version>2099</version>
  <introduction>
    <introSection type="instruction"><title>Invented</title>
      <instruction><note>Invented intro instruction</note></instruction>
    </introSection>
  </introduction>
  <chapter>
    <name>1</name>
    <desc>Invented chapter (U90-U99)</desc>
    <excludes2><note>invented thing (Q90-Q91)</note></excludes2>
    <sectionIndex>
      <sectionRef first="U90" last="U92" id="U90-U92">Invented</sectionRef>
    </sectionIndex>
    <section id="U90-U92">
      <desc>Invented section (U90-U92)</desc>
      <excludes1><note>invented free text only</note></excludes1>
      <diag>
        <name>U90</name>
        <desc>Invented category</desc>
        <includes><note>invented include</note></includes>
        <excludes1>
          <note>invented other (U91.1)</note>
          <note>invented mixed (U91.1, U98.7)</note>
          <note>invented wildcard (U91.-)</note>
          <note>invented none (U98.7)</note>
        </excludes1>
        <sevenChrNote><note>The appropriate 7th character is to be added to each code from category U90</note></sevenChrNote>
        <sevenChrDef>
          <extension char="A">initial</extension>
          <extension char="D">subsequent</extension>
          <note>an invented note in a definition</note>
        </sevenChrDef>
        <diag>
          <name>U90.0</name>
          <desc>Invented subcategory</desc>
          <diag>
            <name>U90.01</name>
            <desc>Invented leaf</desc>
            <inclusionTerm><note>Invented term</note></inclusionTerm>
          </diag>
        </diag>
        <diag placeholder="true">
          <name>U90.1X</name>
          <desc>Invented placeholder</desc>
          <sevenChrDef>
            <extension char="S">sequela</extension>
          </sevenChrDef>
        </diag>
      </diag>
      <diag>
        <name>U91</name>
        <desc>Invented second category</desc>
        <codeFirst><note>underlying invented disease (U90.-)</note></codeFirst>
        <diag>
          <name>U91.1</name>
          <desc>Invented billable</desc>
          <useAdditionalCode><note>code for invented range (U90.0-U90.01)</note></useAdditionalCode>
          <diag>
            <name>U91.1001</name>
            <desc>Invented seven-character diag</desc>
          </diag>
        </diag>
      </diag>
    </section>
  </chapter>
</ICD10CM.tabular>
"""

# invented order-file codes for the fixture: U90.01XA and U90.01XD take
# 7th characters from U90; U90.01XZ has a 7th character no definition lists;
# U91.1001 is a 7-character diag in the XML itself; U99 is a stored code
# that the XML does not have
STORED = {"U90", "U900", "U9001", "U9001XA", "U9001XD", "U9001XZ", "U901X",
          "U901XXS", "U91", "U911", "U911001", "U99"}
BILLABLE = {"U9001XA", "U9001XD", "U9001XZ", "U901XXS", "U911001", "U99"}


class TreeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "tab.xml"
        self.path.write_text(FIXTURE_XML, encoding="utf-8")
        self.tree = load_tree(self.path)

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def test_version_and_order(self):
        self.assertEqual(self.tree.version, "2099")
        self.assertEqual(list(self.tree.diags),
                         ["U90", "U900", "U9001", "U901X", "U91", "U911", "U911001"])

    def test_diag_fields(self):
        d = self.tree.diags["U9001"]
        self.assertEqual((d.name, d.parent, d.section, d.chapter, d.depth),
                         ("U90.01", "U900", "U90-U92", 1, 3))
        self.assertEqual(d.desc, "Invented leaf")
        self.assertEqual(self.tree.diags["U90"].children, ("U900", "U901X"))
        self.assertTrue(self.tree.diags["U901X"].placeholder)
        self.assertFalse(self.tree.diags["U90"].placeholder)

    def test_notes_by_owner(self):
        kinds = [(n.kind, n.owner_type, n.owner) for n in self.tree.notes]
        self.assertIn(("excludes2", "chapter", "1"), kinds)
        self.assertIn(("excludes1", "section", "U90-U92"), kinds)
        self.assertIn(("instruction", "introduction", "instruction"), kinds)
        self.assertEqual(sum(1 for k in kinds if k == ("excludes1", "diag", "U90")), 4)
        self.assertIn(("sevenChrNote", "diag", "U90"), kinds)
        self.assertIn(("sevenChrDef", "diag", "U90"), kinds)

    def test_seven_chr_def(self):
        self.assertEqual(self.tree.diags["U90"].seven_chr, (("A", "initial"),
                                                            ("D", "subsequent")))
        self.assertEqual(self.tree.diags["U901X"].seven_chr, (("S", "sequela"),))
        self.assertIsNone(self.tree.diags["U900"].seven_chr)

    def test_seven_chr_source_nearest_wins(self):
        self.assertEqual(seven_chr_source("U9001XA", self.tree).code, "U90")
        self.assertEqual(seven_chr_source("U901XXS", self.tree).code, "U901X")
        self.assertIsNone(seven_chr_source("U911", self.tree))
        self.assertIsNone(seven_chr_source("U911001", self.tree))
        self.assertIsNone(seven_chr_source("Q99", self.tree))

    def test_scope_of(self):
        s = scope_of("U9001XA", self.tree)
        self.assertEqual(s.diags, ("U9001", "U900", "U90"))
        self.assertEqual((s.section, s.chapter), ("U90-U92", 1))
        self.assertEqual(scope_of("U99", self.tree).diags, ())

    def test_diag_level(self):
        self.assertEqual(diag_level("U90", BILLABLE), "category")
        self.assertEqual(diag_level("U900", BILLABLE), "subcategory")
        self.assertEqual(diag_level("U911001", BILLABLE), "code")
        self.assertEqual(diag_level("U911", BILLABLE), "subcategory")
        self.assertEqual(diag_level("U99", BILLABLE), "category")

    def test_bad_name_raises(self):
        with self.assertRaises(TabularError):
            load_tree(self.write(FIXTURE_XML.replace("<name>U91.1</name>",
                                                     "<name>U91 1</name>")))

    def test_duplicate_name_raises(self):
        with self.assertRaises(TabularError):
            load_tree(self.write(FIXTURE_XML.replace("<name>U91.1</name>",
                                                     "<name>U90.0</name>")))

    def test_bad_extension_raises(self):
        with self.assertRaises(TabularError):
            load_tree(self.write(FIXTURE_XML.replace('char="S"', 'char="SS"')))

    def test_census(self):
        c = element_census(self.path)
        self.assertEqual(c["diag"]["count"], 7)
        self.assertEqual(c["diag"]["parents"], {"section": 2, "diag": 5})
        self.assertEqual(c["diag"]["attributes"], {"placeholder": 1})
        self.assertEqual(c["note"]["parents"]["excludes1"], 5)
        self.assertEqual(c["ICD10CM.tabular"]["parents"], {})


class ReferenceTests(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(find_references("congenital rubella (P35.0)"),
                         [Reference("P35.0", "P350", None, False)])
        self.assertEqual(find_references("aneurysm (Q28.-)"),
                         [Reference("Q28.-", "Q28", None, True)])
        self.assertEqual(find_references("laceration (S01.12-)"),
                         [Reference("S01.12-", "S0112", None, True)])
        self.assertEqual(find_references("infection (T82.6-T82.7, T85.7)"),
                         [Reference("T82.6-T82.7", "T826", "T827", False),
                          Reference("T85.7", "T857", None, False)])
        self.assertEqual(find_references("gout (M1A.-, M10.-)"),
                         [Reference("M1A.-", "M1A", None, True),
                          Reference("M10.-", "M10", None, True)])
        self.assertEqual(find_references("chapter (O00-O9A)"),
                         [Reference("O00-O9A", "O00", "O9A", False)])

    def test_sentence_end_dot_not_part_of_code(self):
        self.assertEqual(find_references("as bronchitis in J40."),
                         [Reference("J40", "J40", None, False)])

    def test_words_are_not_codes(self):
        self.assertEqual(find_references("HIV NOS AND HbA1c COVID-19 type 2"), [])
        self.assertEqual(find_references("free text only"), [])

    def test_resolves(self):
        prefixes = prefix_set({"U900", "U9001", "U911"})
        self.assertTrue(reference_resolves(Reference("U90.0", "U900", None, False), prefixes))
        self.assertTrue(reference_resolves(Reference("U90.-", "U90", None, True), prefixes))
        # a plain code that is only a prefix of stored codes still resolves
        self.assertTrue(reference_resolves(Reference("U91", "U91", None, False), prefixes))
        self.assertFalse(reference_resolves(Reference("U92", "U92", None, False), prefixes))
        self.assertTrue(reference_resolves(Reference("U90.0-U91.1", "U900", "U911", False),
                                           prefixes))
        self.assertFalse(reference_resolves(Reference("U90.0-U92", "U900", "U92", False),
                                            prefixes))

    def test_classify(self):
        prefixes = prefix_set({"U911"})
        self.assertEqual(classify_note("x (U91.1)", prefixes), "all")
        self.assertEqual(classify_note("x (U91.1, U98.7)", prefixes), "some")
        self.assertEqual(classify_note("x (U98.7)", prefixes), "none_unresolved")
        self.assertEqual(classify_note("free text", prefixes), "no_refs")


class SurveyTests(unittest.TestCase):
    """The survey on the fixture, against counts worked out by hand."""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tab.xml"
            path.write_text(FIXTURE_XML, encoding="utf-8")
            cls.s = tabular_survey.survey(path, STORED, BILLABLE)

    def test_note_kinds(self):
        k = self.s["notes"]
        self.assertEqual(k["excludes1"]["notes"], 5)
        self.assertEqual(k["excludes1"]["elements"], 2)
        self.assertEqual(k["excludes1"]["notes_by_level"], {"section": 1, "category": 4})
        self.assertEqual(k["excludes1"]["classes"],
                         {"all": 2, "some": 1, "none_unresolved": 1, "no_refs": 1})
        self.assertEqual(k["useAdditionalCode"]["notes_by_level"], {"subcategory": 1})
        self.assertEqual(k["useAdditionalCode"]["classes"]["all"], 1)
        self.assertEqual(k["excludes2"]["notes_by_level"], {"chapter": 1})
        # Q90-Q91 is not stored in the fixture
        self.assertEqual(k["excludes2"]["classes"]["none_unresolved"], 1)
        self.assertEqual(k["inclusionTerm"]["notes_by_level"], {"subcategory": 1})
        self.assertEqual(k["instruction"]["notes_by_level"], {"introduction": 1})
        self.assertEqual(k["sevenChrDef"]["elements"], 2)
        self.assertEqual(k["sevenChrDef"]["notes"], 1)

    def test_seventh(self):
        s = self.s["seventh"]
        self.assertEqual(s["defs"], 2)
        self.assertEqual(s["defs_with_def_on_ancestor"], 1)
        self.assertEqual(s["billable_7"], 5)
        self.assertEqual(s["billable_7_explained"], 3)
        self.assertEqual(s["billable_7_unexplained_count"], 2)
        self.assertEqual(s["billable_7_unexplained"],
                         [("U9001XZ", "char_not_listed"),
                          ("U911001", "tabular_diag_no_definition")])
        self.assertEqual(s["x6_codes"], 4)
        self.assertEqual(s["x6_explained"], 3)

    def test_order_vs_xml(self):
        o = self.s["order_vs_xml"]
        self.assertEqual(o["xml_only"], [])
        self.assertEqual(o["order_only_count"], 5)
        self.assertEqual(o["order_only_by_reason"],
                         {"7th character from a definition": 3, "other": 2})
        self.assertEqual(o["order_only_other_examples"], ["U9001XZ", "U99"])


if __name__ == "__main__":
    unittest.main()
