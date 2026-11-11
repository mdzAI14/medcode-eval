"""Part A against the real ICD-10-CM FY2027 refdata files.

Input counts are those observed in task P3.1 (step 1 to 3 findings);
probe counts follow the P3.2 rules. The probe answers are derived again
from the order and addenda files, independently of the generator. No
network.
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
OUTPUTS = ("probes_full.jsonl", "probes_lite.jsonl", "probes_changes.jsonl",
           "manifest.json")

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

    def test_billable_long_descriptions_shared_with_any_row(self):
        c = Counter(r.long for r in self.records)
        shared = [r for r in self.records if r.billable and c[r.long] > 1]
        self.assertEqual(len(shared), 342)

    def test_changes(self):
        got = Counter(ch for _, ch in addenda.changes(self.addenda.records))
        self.assertEqual(got, {"added_billable": 190, "added_header": 48,
                               "billable_to_header": 15, "removed": 21})


class RealProbesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = orderfile.load(ORDER)
        cls.by_code = {r.code: r for r in cls.records}
        cls.parents = orderfile.parent_map(cls.records)
        cls.chapters = tabular.load_chapters(TABULAR)
        add = addenda.load(ADDENDA).records
        cls.removed = addenda.removed_codes(add)
        cls.added = set(addenda.added_codes(add))
        cls.changes = dict(addenda.changes(add))
        cls.full = load_jsonl(OUT / "probes_full.jsonl")
        cls.lite = load_jsonl(OUT / "probes_lite.jsonl")
        cls.changes_probes = load_jsonl(OUT / "probes_changes.jsonl")
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
                         {"substituted": 56, "extended": 56, "placeholder_prefix": 55})
        self.assertEqual(Counter(p["kind"] for p in self.lite if "kind" in p),
                         {"substituted": 6, "extended": 6, "placeholder_prefix": 5})
        c2d = Counter(p["answer"] for p in self.full if p["type"] == "code_to_description")
        self.assertEqual(c2d, {x: 125 for x in "ABCD"})
        c2d = Counter(p["answer"] for p in self.lite if p["type"] == "code_to_description")
        self.assertEqual(sum(c2d.values()), 50)
        self.assertTrue(set(c2d.values()) <= {12, 13}, c2d)

    def test_no_changed_code_in_main_sets(self):
        for p in self.full:
            code = p["answer"] if p["type"] == "description_to_code" else p["code"]
            self.assertNotIn(code.replace(".", ""), self.added, p["id"])
            self.assertNotIn(p.get("derived_from"), self.added, p["id"])
            self.assertNotIn(code.replace(".", ""), self.removed, p["id"])

    def test_changes_set(self):
        probes = self.changes_probes
        self.assertEqual(Counter((p["type"], p["change"]) for p in probes), {
            ("status", "added_billable"): 190, ("status", "added_header"): 48,
            ("status", "billable_to_header"): 15, ("status", "removed"): 21,
            ("description_to_code", "added_billable"): 188})
        status = {p["code"].replace(".", ""): p for p in probes if p["type"] == "status"}
        self.assertEqual(set(status), set(self.changes))
        long_count = Counter(r.long for r in self.records)
        for code, p in status.items():
            self.assertEqual(p["change"], self.changes[code])
            if code in self.by_code:
                want = "billable" if self.by_code[code].billable else "header"
            else:
                want = "not_a_code"
            self.assertEqual(p["answer"], want)
            self.assertEqual(p["chapter"], tabular.chapter_of(code[:3], self.chapters))
        d2c = [p for p in probes if p["type"] == "description_to_code"]
        want = {c for c, ch in self.changes.items()
                if ch == "added_billable" and long_count[self.by_code[c].long] == 1}
        self.assertEqual({p["answer"] for p in d2c}, want)
        for p in d2c:
            self.assertEqual(p["description"], self.by_code[p["answer"]].long)

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
        for probes in (self.full, self.lite, self.changes_probes):
            self.assertEqual(score(probes, oracle(probes))["overall"]["accuracy"], 1.0)
            r = score(probes, constant(probes))
            for t, g in r["by_type"].items():
                self.assertAlmostEqual(g["accuracy"], chance_rate(probes, t))
            self.assertEqual(r["overall"]["invalid"], 0)


if __name__ == "__main__":
    unittest.main()
