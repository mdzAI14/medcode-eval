"""Tests for medcode_eval.tabular (chapter of a 3-character category).

The fixture XML is invented (codes U9x, chapter titles made up). No network.
"""

import tempfile
import unittest
from pathlib import Path

from medcode_eval.tabular import Chapter, TabularError, chapter_of, load_chapters

FIXTURE_XML = """<?xml version="1.0" encoding="utf-8"?>
<ICD10CM.tabular>
  <version>2099</version>
  <chapter>
    <name>1</name>
    <desc>Invented first chapter (U90-U94)</desc>
    <sectionIndex>
      <sectionRef first="U90" last="U92" id="U90-U92">Invented</sectionRef>
      <sectionRef first="U94" last="U94" id="U94">Invented</sectionRef>
    </sectionIndex>
    <section id="U90-U92"><desc>s</desc>
      <diag><name>U90</name><desc>Invented</desc></diag>
    </section>
  </chapter>
  <chapter>
    <name>2</name>
    <desc>Invented second chapter, with comma (U95-U9A)</desc>
    <section id="U95-U9A"><desc>s</desc>
      <diag><name>U9A</name><desc>Invented</desc></diag>
    </section>
  </chapter>
</ICD10CM.tabular>
"""


class TabularTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "tab.xml"
        self.path.write_text(FIXTURE_XML, encoding="utf-8")

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def test_load(self):
        self.assertEqual(
            load_chapters(self.path),
            [
                Chapter(1, "Invented first chapter", "U90", "U94"),
                Chapter(2, "Invented second chapter, with comma", "U95", "U9A"),
            ],
        )

    def test_chapter_of(self):
        chapters = load_chapters(self.path)
        self.assertEqual(chapter_of("U90", chapters), 1)
        self.assertEqual(chapter_of("U94", chapters), 1)
        self.assertEqual(chapter_of("U95", chapters), 2)
        # letters sort after digits: U9A is the end of chapter 2
        self.assertEqual(chapter_of("U9A", chapters), 2)
        self.assertIsNone(chapter_of("U9B", chapters))
        self.assertIsNone(chapter_of("A00", chapters))

    def test_chapter_of_rejects_non_category(self):
        chapters = load_chapters(self.path)
        with self.assertRaises(ValueError):
            chapter_of("U901", chapters)

    def test_overlap_raises(self):
        chapters = [Chapter(1, "a", "U90", "U95"), Chapter(2, "b", "U95", "U99")]
        with self.assertRaises(TabularError):
            chapter_of("U95", chapters)

    def test_missing_range_raises(self):
        with self.assertRaises(TabularError):
            load_chapters(self.write(FIXTURE_XML.replace(" (U90-U94)", "")))

    def test_reversed_range_raises(self):
        with self.assertRaises(TabularError):
            load_chapters(self.write(FIXTURE_XML.replace("(U90-U94)", "(U94-U90)")))


if __name__ == "__main__":
    unittest.main()
