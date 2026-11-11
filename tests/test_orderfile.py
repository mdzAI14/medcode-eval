"""Tests for medcode_eval.orderfile.

Fixture tests use invented codes (prefix U9Y / U9Z, absent from the FY2027
order file) and build their files with tempfile. No network.
"""

import tempfile
import unittest
from pathlib import Path

from medcode_eval.orderfile import (
    OrderFileError,
    OrderRecord,
    load,
    parent_map,
    parse_line,
    parse_lines,
)


def row(order, code, flag, short, long):
    """Build one fixed-width order-file row (no line ending)."""
    return f"{order:05d} {code:<7} {flag} {short:<60} {long}"


FIXTURE = [
    row(1, "U9Z", 0, "Invented category", "Invented category long"),
    row(2, "U9Z1", 1, "Invented leaf one", "Invented leaf one, long"),
    row(3, "U9Z9", 0, "Invented header", "Invented header long"),
    row(4, "U9Z9A", 1, "Invented deep leaf", "Invented deep leaf long"),
    row(5, "U9Y", 0, "Invented second category", "Invented second category"),
    row(6, "U9YXXXA", 1, "Invented placeholder leaf", "Invented placeholder leaf"),
]


class ParseLineTests(unittest.TestCase):
    def test_fields(self):
        rec = parse_line(FIXTURE[1])
        self.assertEqual(
            rec,
            OrderRecord(2, "U9Z1", True, "Invented leaf one", "Invented leaf one, long"),
        )

    def test_header_flag(self):
        rec = parse_line(FIXTURE[0])
        self.assertFalse(rec.billable)
        self.assertEqual(rec.code, "U9Z")

    def test_seven_character_code(self):
        rec = parse_line(FIXTURE[5])
        self.assertEqual(rec.code, "U9YXXXA")
        self.assertTrue(rec.billable)

    def test_line_endings_stripped(self):
        self.assertEqual(parse_line(FIXTURE[1] + "\r\n"), parse_line(FIXTURE[1]))
        self.assertEqual(parse_line(FIXTURE[1] + "\n"), parse_line(FIXTURE[1]))

    def test_short_description_full_width(self):
        short = "S" * 60
        rec = parse_line(row(7, "U9Z2", 1, short, "Long text"))
        self.assertEqual(rec.short, short)
        self.assertEqual(rec.long, "Long text")

    def test_long_description_with_inner_spaces(self):
        rec = parse_line(row(8, "U9Z3", 1, "Short", "Long  with   spaces"))
        self.assertEqual(rec.long, "Long  with   spaces")

    def test_bad_flag(self):
        with self.assertRaises(OrderFileError):
            parse_line(row(9, "U9Z4", 2, "Short", "Long"))

    def test_bad_order_number(self):
        bad = "0000A" + FIXTURE[1][5:]
        with self.assertRaises(OrderFileError):
            parse_line(bad)

    def test_too_short(self):
        with self.assertRaises(OrderFileError):
            parse_line(FIXTURE[1][:70])

    def test_missing_separator(self):
        bad = FIXTURE[1][:5] + "X" + FIXTURE[1][6:]
        with self.assertRaises(OrderFileError):
            parse_line(bad)

    def test_bad_code_characters(self):
        with self.assertRaises(OrderFileError):
            parse_line(row(10, "U9.1", 1, "Short", "Long"))

    def test_code_too_short(self):
        with self.assertRaises(OrderFileError):
            parse_line(row(11, "U9", 0, "Short", "Long"))

    def test_empty_long_description(self):
        line = f"{12:05d} {'U9Z5':<7} 1 {'Short':<60}  "
        self.assertEqual(len(line), 78)
        with self.assertRaises(OrderFileError):
            parse_line(line)

    def test_error_names_line_number(self):
        with self.assertRaises(OrderFileError) as cm:
            parse_lines([FIXTURE[0], "garbage"])
        self.assertIn("line 2", str(cm.exception))


class LoadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, lines, ending="\r\n"):
        path = self.dir / "order.txt"
        path.write_bytes("".join(l + ending for l in lines).encode("ascii"))
        return path

    def test_load_crlf(self):
        recs = load(self.write(FIXTURE))
        self.assertEqual([r.code for r in recs],
                         ["U9Z", "U9Z1", "U9Z9", "U9Z9A", "U9Y", "U9YXXXA"])
        self.assertEqual([r.order for r in recs], [1, 2, 3, 4, 5, 6])

    def test_load_lf(self):
        self.assertEqual(load(self.write(FIXTURE, "\n")),
                         load(self.write(FIXTURE)))

    def test_non_ascii_rejected(self):
        path = self.dir / "order.txt"
        path.write_bytes(FIXTURE[1].encode("ascii") + b"\xe9\r\n")
        with self.assertRaises(OrderFileError):
            load(path)

    def test_blank_line_rejected(self):
        with self.assertRaises(OrderFileError):
            load(self.write([FIXTURE[0], "", FIXTURE[1]]))


class ParentMapTests(unittest.TestCase):
    def test_parents(self):
        recs = parse_lines(FIXTURE)
        self.assertEqual(
            parent_map(recs),
            {
                "U9Z": None,
                "U9Z1": "U9Z",
                "U9Z9": "U9Z",
                "U9Z9A": "U9Z9",
                "U9Y": None,
                # longest stored proper prefix, not the immediate prefix
                "U9YXXXA": "U9Y",
            },
        )


REAL = (Path(__file__).resolve().parents[1]
        / "refdata" / "icd10cm_fy2027" / "icd10cm_order_2027.txt")


class RealOrderFileFY2027Tests(unittest.TestCase):
    """ICD-10-CM FY2027 order file: counts and rules as observed in P2.1."""

    @classmethod
    def setUpClass(cls):
        cls.records = load(REAL)
        cls.parents = parent_map(cls.records)

    def test_counts(self):
        recs = self.records
        self.assertEqual(len(recs), 98403)
        self.assertEqual(sum(r.billable for r in recs), 74879)
        self.assertEqual(sum(not r.billable for r in recs), 23524)

    def test_no_duplicate_codes(self):
        codes = [r.code for r in self.records]
        self.assertEqual(len(set(codes)), len(codes))

    def test_order_numbers_contiguous(self):
        self.assertEqual([r.order for r in self.records],
                         list(range(1, len(self.records) + 1)))

    def test_no_orphans(self):
        orphans = [c for c, p in self.parents.items()
                   if p is None and len(c) != 3]
        self.assertEqual(orphans, [])

    def test_non_immediate_parents(self):
        gaps = [(c, p) for c, p in self.parents.items()
                if p is not None and len(p) != len(c) - 1]
        self.assertEqual(len(gaps), 11153)
        # every skipped position is the placeholder X
        self.assertEqual([g for g in gaps if set(g[0][len(g[1]):-1]) != {"X"}], [])

    def test_billable_iff_leaf(self):
        has_child = {p for p in self.parents.values() if p is not None}
        exceptions = [r.code for r in self.records
                      if r.billable == (r.code in has_child)]
        self.assertEqual(exceptions, [])


if __name__ == "__main__":
    unittest.main()
