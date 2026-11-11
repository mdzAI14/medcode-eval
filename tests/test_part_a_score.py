"""Tests for medcode_eval.part_a.score and the fake responders.

Probes here are hand-made with invented codes (U9x). No network.
"""

import json
import random
import tempfile
import unittest
from pathlib import Path

from medcode_eval.part_a.generate import build_full, load_codeset
from medcode_eval.part_a.responders import CONSTANT, chance_rate, constant, oracle
from medcode_eval.part_a.score import main, parse_response, score, to_markdown
from tests import part_a_fixture as fx


def probe(pid, type_, chapter, answer, kind=None, **fields):
    p = {"id": pid, "type": type_, "chapter": chapter, "answer": answer,
         "source": "order.txt", "code_set": "ICD-10-CM FY2027 (October 1, 2026 release)"}
    if kind:
        p["kind"] = kind
    p.update(fields)
    return p


C2D = probe("c1", "code_to_description", 1, "B", code="U90.0",
            options=["w", "x", "y", "z"])
D2C = probe("d1", "description_to_code", 1, "U9312", description="Invented")
ST_B = probe("s1", "status", 2, "billable", code="U90.0")
ST_N = probe("s2", "status", 2, "not_a_code", kind="extended", code="U90.01",
             derived_from="U900")
ST_D = probe("s3", "status", None, "not_a_code", kind="deleted", code="U95.8")


class ParseResponseTests(unittest.TestCase):
    def test_letter(self):
        self.assertEqual(parse_response(C2D, " b "), "B")
        self.assertEqual(parse_response(C2D, "B."), "B")
        self.assertIsNone(parse_response(C2D, "E"))
        self.assertIsNone(parse_response(C2D, "AB"))
        self.assertIsNone(parse_response(C2D, ""))

    def test_letter_with_text(self):
        self.assertEqual(parse_response(C2D, "B. Invented second option"), "B")
        self.assertEqual(parse_response(C2D, "C) something"), "C")
        self.assertEqual(parse_response(C2D, "D: text"), "D")
        self.assertEqual(parse_response(C2D, "A.x"), "A")
        self.assertEqual(parse_response(C2D, "A)"), "A")
        self.assertEqual(parse_response(C2D, "a) lower case"), "A")
        self.assertIsNone(parse_response(C2D, "E. no such option"))
        self.assertIsNone(parse_response(C2D, "B - text"))
        self.assertIsNone(parse_response(C2D, "B text"))
        self.assertIsNone(parse_response(C2D, "AB. text"))
        self.assertIsNone(parse_response(C2D, "Option B. text"))
        # other probe types are not affected
        self.assertIsNone(parse_response(ST_B, "B. billable"))

    def test_code(self):
        self.assertEqual(parse_response(D2C, "u93.12"), "U9312")
        self.assertEqual(parse_response(D2C, " U9312\n"), "U9312")
        self.assertEqual(parse_response(D2C, "U93 .12"), "U9312")
        self.assertIsNone(parse_response(D2C, "U9"))
        self.assertIsNone(parse_response(D2C, "U9312 is the code"))

    def test_status(self):
        self.assertEqual(parse_response(ST_B, "Billable"), "billable")
        self.assertEqual(parse_response(ST_B, " HEADER. "), "header")
        self.assertEqual(parse_response(ST_B, "not a code"), "not_a_code")
        self.assertEqual(parse_response(ST_B, "Not_A_Code"), "not_a_code")
        self.assertIsNone(parse_response(ST_B, "valid"))

    def test_non_string(self):
        self.assertIsNone(parse_response(ST_B, None))
        self.assertIsNone(parse_response(ST_B, 3))


class ScoreTests(unittest.TestCase):
    def test_counts_and_means(self):
        probes = [C2D, D2C, ST_B, ST_N, ST_D]
        responses = [
            {"id": "c1", "response": "b"},           # right
            {"id": "d1", "response": "U93.12"},      # right
            {"id": "s1", "response": "header"},      # wrong, valid
            {"id": "s2", "response": "maybe"},       # wrong, invalid
            # s3 missing
            {"id": "zz", "response": "x"},           # unknown id
        ]
        r = score(probes, responses)
        o = r["overall"]
        self.assertEqual((o["n"], o["correct"], o["missing"], o["invalid"]), (5, 2, 1, 1))
        self.assertAlmostEqual(o["accuracy"], 0.4)
        # chapters: 1 -> 2/2, 2 -> 0/2, none -> 0/1
        self.assertAlmostEqual(o["chapter_mean_accuracy"], 1 / 3)
        self.assertEqual(r["unknown_response_ids"], 1)
        self.assertEqual(r["by_chapter"]["1"]["accuracy"], 1.0)
        self.assertEqual(r["by_chapter"]["none"]["n"], 1)
        st = r["by_type"]["status"]
        self.assertEqual((st["n"], st["correct"], st["missing"], st["invalid"]), (3, 0, 1, 1))
        self.assertEqual(set(r["by_kind"]), {"deleted", "extended"})
        self.assertEqual(r["by_kind"]["deleted"]["missing"], 1)

    def test_by_change(self):
        probes = [probe("x1", "status", 1, "billable", code="U90.0", change="added_billable"),
                  probe("x2", "description_to_code", 1, "U900", description="d",
                        change="added_billable"),
                  probe("x3", "status", 2, "not_a_code", code="U95.8", change="removed")]
        r = score(probes, [{"id": "x1", "response": "billable"},
                           {"id": "x3", "response": "header"}])
        self.assertEqual(list(r["by_change"]), ["added_billable", "removed"])
        self.assertEqual((r["by_change"]["added_billable"]["n"],
                          r["by_change"]["added_billable"]["correct"]), (2, 1))
        self.assertEqual(r["by_change"]["removed"]["correct"], 0)
        self.assertIn("| change | removed |", to_markdown(r))

    def test_no_change_group_without_field(self):
        r = score([C2D], [{"id": "c1", "response": "B"}])
        self.assertEqual(r["by_change"], {})
        self.assertNotIn("| change |", to_markdown(r))

    def test_status_table(self):
        probes = [ST_B, ST_N, ST_D,
                  probe("s4", "status", 1, "header", code="U91"),
                  probe("s5", "status", 1, "billable", code="U92.0"),
                  probe("s6", "status", 1, "billable", code="U92.1"), C2D]
        responses = [{"id": "s1", "response": "billable"},
                     {"id": "s2", "response": "header"},
                     {"id": "s3", "response": "who knows"},
                     {"id": "s4", "response": "not a code"},
                     {"id": "s5", "response": "Header"},
                     {"id": "c1", "response": "B"}]
        t = score(probes, responses)["status_table"]
        cols = ["billable", "header", "not_a_code", "invalid", "missing"]
        self.assertEqual(list(t), ["billable", "header", "not_a_code"])
        for row in t.values():
            self.assertEqual(list(row), cols)
        self.assertEqual(t["billable"], {"billable": 1, "header": 1, "not_a_code": 0,
                                         "invalid": 0, "missing": 1})
        self.assertEqual(t["header"], {"billable": 0, "header": 0, "not_a_code": 1,
                                       "invalid": 0, "missing": 0})
        self.assertEqual(t["not_a_code"], {"billable": 0, "header": 1, "not_a_code": 0,
                                           "invalid": 1, "missing": 0})

    def test_status_table_markdown(self):
        md = to_markdown(score([ST_B], [{"id": "s1", "response": "header"}]))
        self.assertIn("| Answer \\ response | billable | header | not_a_code "
                      "| invalid | missing |", md)
        self.assertIn("| billable | 0 | 1 | 0 | 0 | 0 |", md)
        self.assertIn("| header | 0 | 0 | 0 | 0 | 0 |", md)

    def test_status_table_without_status_probes(self):
        r = score([C2D], [{"id": "c1", "response": "B"}])
        self.assertEqual(sum(sum(v.values()) for v in r["status_table"].values()), 0)

    def test_duplicate_response_rejected(self):
        with self.assertRaises(ValueError):
            score([C2D], [{"id": "c1", "response": "B"}, {"id": "c1", "response": "A"}])

    def test_markdown(self):
        md = to_markdown(score([C2D, ST_D], [{"id": "c1", "response": "B"}]))
        self.assertIn("| overall |", md)
        self.assertIn("| code_to_description |", md)
        self.assertIn("| deleted |", md)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "p.jsonl").write_text(json.dumps(C2D) + "\n")
            (d / "r.jsonl").write_text(json.dumps({"id": "c1", "response": "B"}) + "\n")
            main(["--probes", str(d / "p.jsonl"), "--responses", str(d / "r.jsonl"),
                  "--out-json", str(d / "s.json"), "--out-md", str(d / "s.md")])
            self.assertEqual(json.loads((d / "s.json").read_text())["overall"]["accuracy"], 1.0)
            self.assertIn("| overall |", (d / "s.md").read_text())


class ResponderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            paths = fx.write_inputs(tmp)
            cs = load_codeset(paths, root=Path(tmp))
            cls.probes = build_full(cs, fx.FULL, random.Random(1))

    def test_oracle_scores_100(self):
        r = score(self.probes, oracle(self.probes))
        self.assertEqual(r["overall"]["accuracy"], 1.0)
        self.assertEqual(r["overall"]["invalid"], 0)

    def test_oracle_shows_codes_with_dot(self):
        resp = {x["id"]: x["response"] for x in oracle(self.probes)}
        d2c = [p for p in self.probes if p["type"] == "description_to_code"]
        self.assertTrue(any("." in resp[p["id"]] for p in d2c))

    def test_constant_scores_chance(self):
        r = score(self.probes, constant(self.probes))
        for t in CONSTANT:
            self.assertAlmostEqual(r["by_type"][t]["accuracy"], chance_rate(self.probes, t))
        self.assertAlmostEqual(chance_rate(self.probes, "status"), 1 / 3)
        self.assertEqual(r["overall"]["invalid"], 0)

    def test_chance_rate_counts_answers(self):
        ps = [probe("a", "code_to_description", 1, "A"), probe("b", "code_to_description", 1, "C")]
        self.assertEqual(chance_rate(ps, "code_to_description"), 0.5)


if __name__ == "__main__":
    unittest.main()
