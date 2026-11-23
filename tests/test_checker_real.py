"""medcode_eval.checker against the real refdata files of
ICD-10-CM FY2027 (October 1, 2026 release).

Expected values are computed here from the order file, or frozen as
observed in task P4.2 (marked FROZEN). No network.
"""

import json
import unittest
from collections import Counter

from medcode_eval import checker, tabular
from medcode_eval.part_a.generate import REPO_ROOT

# FROZEN: header cases; P4.1 found 16,986 headers with a 7th character in
# scope and 6,538 without.
HEADER_CASES = {"seventh_character_needed": 16986, "more_specific_codes": 6538}
# FROZEN: billable codes whose long description has the phrase (P4.1: 163)
BILLABLE_WITH_PHRASE = 163
HEADER_WITH_PHRASE = 51
# FROZEN: references in excludes1 / codeFirst notes, inside parentheses and
# resolvable outside them
PAREN = {"excludes1": (5682, 32), "codeFirst": (737, 0)}


def setUpModule():
    global DATA
    DATA = checker.default_data()


def _phrase(rec):
    return checker.PHRASE in rec.long.lower()


class TestSingles(unittest.TestCase):
    def test_a_every_billable_alone(self):
        bill = [r for r in DATA.records.values() if r.billable]
        expected_mf = sum(_phrase(r) for r in bill)
        self.assertEqual(expected_mf, BILLABLE_WITH_PHRASE)
        seen = Counter()
        for r in bill:
            rules = [f["rule"] for f in checker.check([r.code])]
            want = ["manifestation_first"] if _phrase(r) else []
            self.assertEqual(rules, want, r.code)
            seen[tuple(rules)] += 1
        self.assertEqual(seen[("manifestation_first",)], BILLABLE_WITH_PHRASE)
        self.assertEqual(seen[()], len(bill) - BILLABLE_WITH_PHRASE)

    def test_b_every_header_alone(self):
        heads = [r for r in DATA.records.values() if not r.billable]
        cases, with_mf = Counter(), 0
        for r in heads:
            f = checker.check([r.code])
            hnb = [x for x in f if x["rule"] == "header_not_billable"]
            self.assertEqual(len(hnb), 1, r.code)
            cases[hnb[0]["details"]["case"]] += 1
            other = [x["rule"] for x in f if x["rule"] != "header_not_billable"]
            self.assertEqual(other, ["manifestation_first"] if _phrase(r) else [], r.code)
            with_mf += bool(other)
        self.assertEqual(dict(cases), HEADER_CASES)
        self.assertEqual(sum(cases.values()), len(heads))
        self.assertEqual(with_mf, HEADER_WITH_PHRASE)

    def test_c_probe_strings_not_in_code_set(self):
        n = 0
        for name, keep in (("probes_full.jsonl", lambda p: True),
                           ("probes_changes.jsonl", lambda p: p.get("change") == "removed")):
            with open(REPO_ROOT / "data" / "part_a" / name, encoding="utf-8") as fh:
                for line in fh:
                    p = json.loads(line)
                    if p["type"] != "status" or p["answer"] != "not_a_code" or not keep(p):
                        continue
                    rules = [f["rule"] for f in checker.check([p["code"]])]
                    self.assertIn("not_in_code_set", rules, p["code"])
                    n += 1
        self.assertGreater(n, 0)


def _picks(kind):
    """First, middle and last note of a kind (file order) with an exact
    parenthesised reference to a billable code; with a billable code in its
    scope that is not the referenced one."""
    cands = []
    for n in DATA.tree.notes:
        if n.kind != kind:
            continue
        inside, _ = tabular.split_by_parentheses(n.text)
        ref = next((r for r in inside if r.last is None and not r.wildcard
                    and r.first in DATA.records and DATA.records[r.first].billable), None)
        if ref is not None:
            cands.append((n, ref))
    picks = [cands[0], cands[len(cands) // 2], cands[-1]]
    out = []
    for n, ref in picks:
        owner = (n.owner_type, n.owner)
        a = next(c for c, r in DATA.records.items()
                 if r.billable and c != ref.first and owner in checker._owners(c, DATA.tree))
        out.append((n, a, ref.first))
    return out


class TestPairs(unittest.TestCase):
    def _assert_pair(self, rule, note, a, b):
        f = checker.check([a, b])
        hits = [x for x in f if x["rule"] == rule and x["source"][0]["text"] == note.text
                and x["codes"] == [a, b]]
        self.assertEqual(len(hits), 1, (a, b, note.text, f))

    def test_d_excludes1(self):
        for note, a, b in _picks("excludes1"):
            with self.subTest(a=a, b=b):
                self._assert_pair("excludes1_pair", note, a, b)

    def test_d_code_first(self):
        for note, a, b in _picks("codeFirst"):
            with self.subTest(a=a, b=b):
                self._assert_pair("code_first_order", note, a, b)
                rev = checker.check([b, a])
                self.assertFalse([x for x in rev if x["rule"] == "code_first_order"
                                  and x["source"][0]["text"] == note.text])

    def test_parenthesis_counts(self):
        c = checker.parenthesis_counts(DATA)
        self.assertEqual({k: (v["inside"], v["outside_resolvable"]) for k, v in c.items()},
                         PAREN)


if __name__ == "__main__":
    unittest.main()
