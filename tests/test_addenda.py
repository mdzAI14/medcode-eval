"""Tests for medcode_eval.addenda (order addenda text file).

Fixture rows use invented codes (prefix U9x). No network.
"""

import tempfile
import unittest
from pathlib import Path

from medcode_eval.addenda import (
    AddendaError,
    AddendaRecord,
    added_codes,
    changes,
    load,
    parse_line,
    parse_text,
    removed_codes,
)


def arow(action, flag, code, short, long):
    """Build one fixed-width addenda row (no line ending)."""
    return f"{action:<13}{flag} {code:<7} {short:<60} {long}"


FIXTURE = [
    arow("Add:", 1, "U9A1", "Invented added leaf", "Invented added leaf, long"),
    arow("Delete:", 1, "U9B", "Invented category", "Invented category"),
    arow("Add:", 0, "U9B", "Invented category", "Invented category"),
    arow("Add:", 1, "U9B1", "Invented new child", "Invented new child"),
    arow("Delete:", 0, "U9C1", "Invented removed header", "Invented removed header"),
    arow("Delete:", 1, "U9C1XXA", "Invented removed leaf", "Invented removed leaf, initial"),
    arow("Revise from:", 1, "U9D1", "Invented old title", "Invented old title"),
    arow("Revise to:", 1, "U9D1", "Invented new title", "Invented new title"),
    "",
    "Headers",
    "      2 headers in icd10cm_order_2026.txt",
    "      2 headers in icd10cm_order_2027.txt",
    "      1 additions",
    "      1 deletions",
    "      0 revisions",
    "of which",
    "      0 revisions to both long and short titles",
    "      0 revisions to long title only",
    "      0 revisions to short title only",
    "",
    "Codes",
    "      4 codes in icd10cm_order_2026.txt",
    "      5 codes in icd10cm_order_2027.txt",
    "      2 additions",
    "      2 deletions",
    "      1 revisions",
    "of which",
    "      1 revisions to both long and short titles",
    "      0 revisions to long title only",
    "      0 revisions to short title only",
]


class ParseLineTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(
            parse_line(FIXTURE[0]),
            AddendaRecord("add", True, "U9A1", "Invented added leaf",
                          "Invented added leaf, long"),
        )

    def test_delete_header(self):
        rec = parse_line(FIXTURE[4])
        self.assertEqual((rec.action, rec.billable, rec.code),
                         ("delete", False, "U9C1"))

    def test_seven_character_code(self):
        self.assertEqual(parse_line(FIXTURE[5]).code, "U9C1XXA")

    def test_revise_pair(self):
        self.assertEqual(parse_line(FIXTURE[6]).action, "revise_from")
        self.assertEqual(parse_line(FIXTURE[7]).action, "revise_to")
        self.assertEqual(parse_line(FIXTURE[7]).long, "Invented new title")

    def test_crlf_stripped(self):
        self.assertEqual(parse_line(FIXTURE[0] + "\r\n"), parse_line(FIXTURE[0]))

    def test_unknown_action(self):
        with self.assertRaises(AddendaError):
            parse_line(arow("Change:", 1, "U9A1", "S", "L"))

    def test_bad_flag(self):
        with self.assertRaises(AddendaError):
            parse_line(arow("Add:", 2, "U9A1", "S", "L"))

    def test_bad_code(self):
        with self.assertRaises(AddendaError):
            parse_line(arow("Add:", 1, "U9.1", "S", "L"))

    def test_too_short(self):
        with self.assertRaises(AddendaError):
            parse_line(FIXTURE[0][:60])


class ParseTextTests(unittest.TestCase):
    def setUp(self):
        self.result = parse_text(FIXTURE)

    def test_records(self):
        self.assertEqual(len(self.result.records), 8)
        self.assertEqual([r.action for r in self.result.records].count("delete"), 3)

    def test_summary(self):
        s = self.result.summary
        self.assertEqual(s[("Headers", "additions")], 1)
        self.assertEqual(s[("Codes", "deletions")], 2)
        self.assertEqual(s[("Codes", "codes in icd10cm_order_2027.txt")], 5)
        self.assertEqual(s[("Codes", "revisions to both long and short titles")], 1)

    def test_summary_consistent(self):
        # the summary counts match the record lines
        self.assertEqual(self.result.check_summary(), [])

    def test_summary_mismatch_reported(self):
        bad = list(FIXTURE)
        bad[bad.index("      2 deletions")] = "      3 deletions"
        self.assertNotEqual(parse_text(bad).check_summary(), [])

    def test_record_after_summary_rejected(self):
        with self.assertRaises(AddendaError):
            parse_text(FIXTURE + [FIXTURE[0]])

    def test_garbage_in_summary_rejected(self):
        with self.assertRaises(AddendaError):
            parse_text(FIXTURE[:12] + ["garbage line"])

    def test_error_names_line_number(self):
        with self.assertRaises(AddendaError) as cm:
            parse_text([FIXTURE[0], "Add:  garbage"])
        self.assertIn("line 2", str(cm.exception))


class RemovedCodesTests(unittest.TestCase):
    def test_removed_are_deleted_and_not_readded(self):
        result = parse_text(FIXTURE)
        # U9B is deleted and re-added (status change): not removed
        self.assertEqual(removed_codes(result.records), ["U9C1", "U9C1XXA"])


class ChangesTests(unittest.TestCase):
    def test_added_codes_any_add_line(self):
        result = parse_text(FIXTURE)
        self.assertEqual(added_codes(result.records), ["U9A1", "U9B", "U9B1"])

    def test_changes_classified_in_file_order(self):
        records = parse_text(FIXTURE).records + [
            parse_line(arow("Add:", 0, "U9E", "Invented new header", "Invented new header"))]
        self.assertEqual(changes(records), [
            ("U9A1", "added_billable"),
            ("U9B", "billable_to_header"),
            ("U9B1", "added_billable"),
            ("U9C1", "removed"),
            ("U9C1XXA", "removed"),
            ("U9E", "added_header"),
        ])

    def test_revisions_are_not_changes(self):
        records = [parse_line(FIXTURE[6]), parse_line(FIXTURE[7])]
        self.assertEqual(changes(records), [])

    def test_unexpected_combination_rejected(self):
        # deleted as a header and added as billable: not one of the four kinds
        records = [parse_line(arow("Delete:", 0, "U9F", "S", "L")),
                   parse_line(arow("Add:", 1, "U9F", "S", "L"))]
        with self.assertRaises(AddendaError):
            changes(records)

    def test_repeated_add_rejected(self):
        line = parse_line(arow("Add:", 1, "U9G1", "S", "L"))
        with self.assertRaises(AddendaError):
            changes([line, line])


class LoadTests(unittest.TestCase):
    def test_load_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "addenda.txt"
            path.write_bytes("".join(l + "\r\n" for l in FIXTURE).encode("ascii"))
            self.assertEqual(load(path), parse_text(FIXTURE))


if __name__ == "__main__":
    unittest.main()
