"""Part A against the real ICD-10-CM FY2027 refdata files.

Counts are those observed in task P3.1 (step 1 to 3 findings). The probe
answers are derived again from the order file, independently of the
generator's sampling. No network.
"""

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from medcode_eval import addenda, orderfile, tabular
from medcode_eval.part_a.generate import CODE_SET, DEFAULT_OUT, generate
from medcode_eval.part_a.responders import chance_rate, constant, oracle
from medcode_eval.part_a.score import score

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "refdata" / "icd10cm_fy2027"
ORDER = REF / "icd10cm_order_2027.txt"
ADDENDA = REF / "icd10cm_order_addenda_2027.txt"
TABULAR = REF / "icd10cm_tabular_2027.xml"
OUT = ROOT / DEFAULT_OUT
OUTPUTS = ("probes_full.jsonl", "probes_lite.jsonl", "manifest.json")

# chapter: (first, last, stored 3-character categories, billable codes)
CHAPTERS = {
    1: ("A00", "B99", 167, 1068), 2: ("C00", "D49", 141, 1730),
    3: ("D50", "D89", 35, 324), 4: ("E00", "E89", 73, 973),
    5: ("F01", "F99", 72, 872), 6: ("G00", "G99", 68, 700),
    7: ("H00", "H59", 40, 2677), 8: ("H60", "H95", 24, 653),
    9: ("I00", "I99", 80, 1433), 10: ("J00", "J99", 65, 366),
    11: ("K00", "K95", 73, 863), 12: ("L00", "L99", 74, 1001),
    13: ("M00", "M99", 79, 6687), 14: ("N00", "N99", 85, 838),
    15: ("O00", "O9A", 72, 2481), 16: ("P00", "P96", 59, 463),
    17: ("Q00", "QA1", 89, 900), 18: ("R00", "R99", 89, 774),
    19: ("S00", "T88", 171, 41187), 20: ("V00", "Y99", 273, 7461),
    21: ("Z00", "Z99", 90, 1425), 22: ("U00", "U85", 2, 3),
}


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="ascii").splitlines()]


class RealInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = orderfile.load(ORDER)
        cls.codes = {r.code for r in cls.records}
        cls.addenda = addenda.load(ADDENDA)

    def test_addenda_counts(self):
        c = Counter((r.action, r.billable) for r in self.addenda.records)
        self.assertEqual(c, {("add", True): 190, ("add", False): 63,
                             ("delete", True): 30, ("delete", False): 6,
                             ("revise_from", True): 4, ("revise_to", True): 4})
        self.assertEqual(self.addenda.check_summary(), [])

    def test_deleted_absent_and_present(self):
        deleted = []
        for r in self.addenda.records:
            if r.action == "delete" and r.code not in deleted:
                deleted.append(r.code)
        absent = [c for c in deleted if c not in self.codes]
        self.assertEqual(len(deleted), 36)
        self.assertEqual(len(absent), 21)
        self.assertEqual(len(deleted) - len(absent), 15)
        self.assertEqual(addenda.removed_codes(self.addenda.records), absent)

    def test_chapters(self):
        chapters = tabular.load_chapters(TABULAR)
        self.assertEqual({c.number: (c.first, c.last) for c in chapters},
                         {n: v[:2] for n, v in CHAPTERS.items()})
        cats = Counter(); bill = Counter()
        for r in self.records:
            ch = tabular.chapter_of(r.code[:3], chapters)
            self.assertIsNotNone(ch)
            if len(r.code) == 3:
                cats[ch] += 1
            bill[ch] += r.billable
        self.assertEqual({n: (cats[n], bill[n]) for n in CHAPTERS},
                         {n: v[2:] for n, v in CHAPTERS.items()})

    def test_no_shared_billable_long_descriptions(self):
        c = Counter(r.long for r in self.records if r.billable)
        self.assertEqual([d for d, n in c.items() if n > 1], [])


class RealProbesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = orderfile.load(ORDER)
        cls.by_code = {r.code: r for r in cls.records}
        cls.parents = orderfile.parent_map(cls.records)
        cls.chapters = tabular.load_chapters(TABULAR)
        cls.removed = addenda.removed_codes(addenda.load(ADDENDA).records)
        cls.full = load_jsonl(OUT / "probes_full.jsonl")
        cls.lite = load_jsonl(OUT / "probes_lite.jsonl")
        billable = [r for r in cls.records if r.billable]
        cls.code_of_long = {r.long: r.code for r in billable}

    def test_determinism_and_committed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = []
            for name in ("a", "b"):
                generate(Path(tmp) / name)
                runs.append({f: (Path(tmp) / name / f).read_bytes() for f in OUTPUTS})
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[0], {f: (OUT / f).read_bytes() for f in OUTPUTS})

    def test_sizes(self):
        self.assertEqual(Counter(p["type"] for p in self.full),
                         {"code_to_description": 500, "description_to_code": 500,
                          "status": 501})
        self.assertEqual(Counter(p["type"] for p in self.lite),
                         {"code_to_description": 50, "description_to_code": 50,
                          "status": 51})
        for probes, q in ((self.full, 167), (self.lite, 17)):
            self.assertEqual(Counter(p["answer"] for p in probes if p["type"] == "status"),
                             {"billable": q, "header": q, "not_a_code": q})
        self.assertEqual(Counter(p["kind"] for p in self.full if "kind" in p),
                         {"deleted": 21, "substituted": 49, "extended": 49,
                          "placeholder_prefix": 48})
        self.assertEqual(Counter(p["kind"] for p in self.lite if "kind" in p),
                         {"deleted": 8, "substituted": 3, "extended": 3,
                          "placeholder_prefix": 3})

    def test_lite_is_subset(self):
        by_id = {p["id"]: p for p in self.full}
        for p in self.lite:
            self.assertEqual(p, by_id[p["id"]])

    def test_every_answer_rederived(self):
        for p in self.full:
            self.assertEqual(p["code_set"], CODE_SET)
            t = p["type"]
            if t == "description_to_code":
                code = self.code_of_long[p["description"]]
                self.assertEqual(p["answer"], code)
                self.assertTrue(self.by_code[code].billable)
                self.assertEqual(p["chapter"], tabular.chapter_of(code[:3], self.chapters))
                continue
            shown = p["code"]
            if len(shown) > 3:
                self.assertEqual(shown[3], ".")
            code = shown.replace(".", "")
            if t == "code_to_description":
                rec = self.by_code[code]
                self.assertTrue(rec.billable)
                opts = p["options"]
                self.assertEqual(len(set(opts)), 4)
                self.assertEqual([i for i, o in enumerate(opts) if o == rec.long],
                                 ["ABCD".index(p["answer"])])
                for o in opts:
                    self.assertIn(o, self.code_of_long)  # a billable code's text
                self.assertEqual(p["chapter"], tabular.chapter_of(code[:3], self.chapters))
                continue
            self.assertEqual(t, "status")
            if code in self.by_code:
                want = "billable" if self.by_code[code].billable else "header"
            else:
                want = "not_a_code"
            self.assertEqual(p["answer"], want, p["id"])
            if want != "not_a_code":
                self.assertEqual(p["chapter"], tabular.chapter_of(code[:3], self.chapters))
                continue
            kind = p["kind"]
            if kind == "deleted":
                self.assertIn(code, self.removed)
                self.assertEqual(p["chapter"], tabular.chapter_of(code[:3], self.chapters))
                continue
            self.assertNotIn(code, self.removed)
            src = p["derived_from"]
            self.assertEqual(p["chapter"], tabular.chapter_of(src[:3], self.chapters))
            if kind == "substituted":
                self.assertTrue(self.by_code[src].billable)
                self.assertEqual((len(code), code[:-1]), (len(src), src[:-1]))
            elif kind == "extended":
                self.assertTrue(self.by_code[src].billable)
                self.assertEqual(code[:-1], src)
            else:
                self.assertEqual(kind, "placeholder_prefix")
                self.assertEqual(code, src[:-1])
                self.assertNotEqual(self.parents[src], code)

    def test_fake_responders(self):
        for probes in (self.full, self.lite):
            self.assertEqual(score(probes, oracle(probes))["overall"]["accuracy"], 1.0)
            r = score(probes, constant(probes))
            for t, g in r["by_type"].items():
                self.assertAlmostEqual(g["accuracy"], chance_rate(probes, t))
            self.assertEqual(r["overall"]["invalid"], 0)


if __name__ == "__main__":
    unittest.main()
