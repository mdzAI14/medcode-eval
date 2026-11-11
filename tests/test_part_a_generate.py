"""Tests for medcode_eval.part_a.generate on the invented fixture code set."""

import hashlib
import json
import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from medcode_eval.part_a.generate import (
    KINDS,
    ORIGIN,
    allocate,
    build_changes,
    build_full,
    build_lite,
    display,
    generate,
    load_codeset,
)
from tests import part_a_fixture as fx

ORDER_CODES = {c for c, _, _ in fx.CODES}
LONG = {c: l for c, _, l in fx.CODES}
BILLABLE = {c for c, b, _ in fx.CODES if b}


def undot(s):
    return s.replace(".", "")


class FixtureCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.paths = fx.write_inputs(self.dir)
        self.cs = load_codeset(self.paths, root=self.dir)

    def full(self, seed=1):
        return build_full(self.cs, fx.FULL, random.Random(seed))


class DisplayTests(unittest.TestCase):
    def test_display(self):
        self.assertEqual(display("U92"), "U92")
        self.assertEqual(display("U900"), "U90.0")
        self.assertEqual(display("U934XXA"), "U93.4XXA")


class AllocateTests(unittest.TestCase):
    def alloc(self, total, caps, seed):
        return allocate(total, caps, random.Random(seed))

    def test_equal_with_seeded_remainder(self):
        seen = set()
        for seed in range(30):
            out = self.alloc(10, [(1, 5), (2, 5), (3, 5)], seed)
            self.assertEqual(sorted(out.values()), [3, 3, 4])
            seen.add(max(out, key=out.get))
        # the extra probe does not always go to the first chapter
        self.assertEqual(seen, {1, 2, 3})

    def test_shortfall_spread_seeded(self):
        seen = set()
        for seed in range(30):
            out = self.alloc(10, [(1, 1), (2, 10), (3, 10)], seed)
            self.assertEqual(out[1], 1)
            self.assertEqual(sorted((out[2], out[3])), [4, 5])
            seen.add((out[2], out[3]))
        self.assertEqual(seen, {(4, 5), (5, 4)})

    def test_same_seed_same_result(self):
        caps = [(k, 9) for k in range(1, 8)]
        self.assertEqual(self.alloc(25, caps, 4), self.alloc(25, caps, 4))

    def test_empty_chapter(self):
        self.assertEqual(self.alloc(3, [(1, 0), (2, 5)], 1), {1: 0, 2: 3})

    def test_cascading_shortfall(self):
        self.assertEqual(self.alloc(9, [(1, 1), (2, 2), (3, 10)], 1), {1: 1, 2: 2, 3: 6})

    def test_over_capacity(self):
        with self.assertRaises(ValueError):
            self.alloc(5, [(1, 2), (2, 2)], 1)


class CodeSetTests(FixtureCase):
    def test_deleted_only_absent_codes(self):
        # U934 is deleted and re-added; only U958 is absent from the order file
        self.assertEqual(self.cs.deleted, ["U958"])

    def test_added_codes(self):
        self.assertEqual(self.cs.added, fx.ADDED)

    def test_chapters(self):
        self.assertEqual(self.cs.chapter_of_code("U934XXA"), 1)
        self.assertEqual(self.cs.chapter_of_code("U958"), 2)
        self.assertEqual(self.cs.chapters, [1, 2])

    def test_sources_relative(self):
        self.assertEqual(self.cs.sources["order"], "order.txt")


class CodeToDescriptionTests(FixtureCase):
    def test_distractors_same_category(self):
        texts = self.cs.distractors("U900", random.Random(3))
        self.assertEqual(sorted(texts), sorted(LONG[c] for c in ("U901", "U902", "U903")))

    def test_distractors_filled_from_nearest_category(self):
        # U91 has one other billable code; nearest is U90 (before, distance 1)
        texts = self.cs.distractors("U910", random.Random(3))
        self.assertEqual(len(texts), 3)
        self.assertIn(LONG["U911"], texts)
        u90 = {LONG[c] for c in ("U900", "U901", "U902", "U903")}
        self.assertEqual(len([t for t in texts if t in u90]), 2)

    def test_distractors_skip_answer_text(self):
        # U971 shares its text with U9312; U9312's text is never a distractor
        for seed in range(20):
            texts = self.cs.distractors("U971", random.Random(seed))
            self.assertNotIn(LONG["U971"], texts)
            self.assertEqual(len(set(texts)), 3)

    def test_probes(self):
        probes = [p for p in self.full() if p["type"] == "code_to_description"]
        self.assertEqual(len(probes), 6)
        for p in probes:
            code = undot(p["code"])
            self.assertIn(code, BILLABLE)
            self.assertEqual(len(p["options"]), 4)
            self.assertEqual(len(set(p["options"])), 4)
            self.assertEqual(p["options"]["ABCD".index(p["answer"])], LONG[code])

    def test_answer_positions_balanced(self):
        sizes = dict(fx.FULL, code_to_description=8)
        orders = set()
        for seed in range(10):
            probes = [p for p in build_full(self.cs, sizes, random.Random(seed))
                      if p["type"] == "code_to_description"]
            self.assertEqual(Counter(p["answer"] for p in probes),
                             {"A": 2, "B": 2, "C": 2, "D": 2})
            orders.add(tuple(p["answer"] for p in probes))
        self.assertGreater(len(orders), 1)

    def test_answer_positions_with_remainder(self):
        for seed in range(10):
            c = Counter(p["answer"] for p in self.full(seed)
                        if p["type"] == "code_to_description")
            self.assertEqual(sum(c.values()), 6)
            self.assertLessEqual(max(c.values()) - min(c[x] for x in "ABCD"), 1)


class DescriptionToCodeTests(FixtureCase):
    def test_shared_descriptions_left_out(self):
        # U9312 shares its text with U971; U952 with the header U96
        for seed in range(20):
            answers = {p["answer"] for p in self.full(seed)
                       if p["type"] == "description_to_code"}
            self.assertFalse(answers & {"U9312", "U971", "U952"})

    def test_probe(self):
        for p in self.full():
            if p["type"] == "description_to_code":
                self.assertIn(p["answer"], BILLABLE)
                self.assertNotIn(".", p["answer"])
                self.assertEqual(p["description"], LONG[p["answer"]])


class StatusTests(FixtureCase):
    def status(self, seed=1):
        return [p for p in self.full(seed) if p["type"] == "status"]

    def test_answer_counts(self):
        self.assertEqual(Counter(p["answer"] for p in self.status()),
                         {"billable": 6, "header": 6, "not_a_code": 6})

    def test_kind_counts(self):
        kinds = Counter(p["kind"] for p in self.status() if p["answer"] == "not_a_code")
        self.assertEqual(kinds, {"substituted": 2, "extended": 2, "placeholder_prefix": 2})
        self.assertEqual(KINDS, ("substituted", "extended", "placeholder_prefix"))

    def test_no_deleted_kind(self):
        for seed in range(10):
            for p in self.status(seed):
                self.assertNotEqual(p.get("kind"), "deleted")
                self.assertNotIn("U95.8", p["code"])

    def test_kind_only_on_not_a_code(self):
        for p in self.status():
            self.assertEqual("kind" in p, p["answer"] == "not_a_code")

    def test_not_a_code_strings(self):
        for seed in range(10):
            seen = set()
            for p in self.status(seed):
                code = undot(p["code"])
                if p["answer"] == "billable":
                    self.assertIn(code, BILLABLE)
                elif p["answer"] == "header":
                    self.assertIn(code, ORDER_CODES - BILLABLE)
                else:
                    self.assertNotIn(code, ORDER_CODES)
                    self.assertNotIn(code, seen)
                    seen.add(code)
                    kind = p["kind"]
                    src = p["derived_from"]
                    self.assertNotIn(src, fx.ADDED)
                    self.assertNotIn(code, self.cs.deleted)
                    self.assertEqual(p["chapter"], self.cs.chapter_of_code(src))
                    if kind == "substituted":
                        self.assertIn(src, BILLABLE)
                        self.assertEqual(len(code), len(src))
                        self.assertEqual(code[:-1], src[:-1])
                        self.assertNotEqual(code[-1], src[-1])
                    elif kind == "extended":
                        self.assertIn(src, BILLABLE)
                        self.assertLess(len(src), 7)
                        self.assertEqual(code[:-1], src)
                    else:
                        self.assertEqual(kind, "placeholder_prefix")
                        self.assertEqual(code, src[:-1])
                        self.assertIn(code, {"U934XX", "U961XX"})



class ChangedCodesLeaveMainSetsTests(FixtureCase):
    def test_no_added_code_sampled(self):
        for seed in range(20):
            for p in self.full(seed):
                code = p.get("answer") if p["type"] == "description_to_code" else p["code"]
                self.assertNotIn(undot(code), fx.ADDED, p)
                self.assertNotIn(p.get("derived_from"), fx.ADDED)


class ChangesTests(FixtureCase):
    def changes(self, seed=1):
        return build_changes(self.cs, random.Random(seed))

    def test_every_change_used(self):
        got = Counter((p["type"], p["change"]) for p in self.changes())
        self.assertEqual(got, {
            ("status", "added_billable"): 3,
            ("status", "added_header"): 1,
            ("status", "billable_to_header"): 1,
            ("status", "removed"): 1,
            ("description_to_code", "added_billable"): 2,
        })

    def test_answers(self):
        want = {"U911": "billable", "U970": "billable", "U971": "billable",
                "U961": "header", "U934": "header", "U958": "not_a_code"}
        status = [p for p in self.changes() if p["type"] == "status"]
        self.assertEqual({undot(p["code"]): p["answer"] for p in status}, want)
        d2c = [p for p in self.changes() if p["type"] == "description_to_code"]
        # U971 shares its text with U9312, so rule 5 leaves it out
        self.assertEqual({p["answer"]: p["description"] for p in d2c},
                         {"U911": LONG["U911"], "U970": LONG["U970"]})

    def test_chapters_and_fields(self):
        probes = self.changes()
        self.assertEqual(len({p["id"] for p in probes}), len(probes))
        for p in probes:
            code = p["answer"] if p["type"] == "description_to_code" else undot(p["code"])
            self.assertEqual(p["chapter"], self.cs.chapter_of_code(code))
            self.assertEqual(p["code_set"], "ICD-10-CM FY2027 (October 1, 2026 release)")
            self.assertEqual(p["origin"], ORIGIN)
            self.assertNotIn("kind", p)
            self.assertNotIn("derived_from", p)
        removed = [p for p in probes if p["change"] == "removed"][0]
        self.assertEqual((removed["code"], removed["chapter"], removed["source"]),
                         ("U95.8", 2, "addenda.txt"))
        added = [p for p in probes if p["change"] == "added_header"][0]
        self.assertEqual(added["source"], "order.txt")

    def test_ids_distinct_from_main(self):
        main_ids = {p["id"] for p in self.full()}
        self.assertFalse(main_ids & {p["id"] for p in self.changes()})

    def test_flag_disagreement_rejected(self):
        # the Add line says header but the order file says billable
        self.cs.changes = [("U900", "added_header")]
        with self.assertRaises(ValueError):
            self.changes()


class BalanceTests(FixtureCase):
    def test_chapter_balance(self):
        probes = self.full()
        for t in ("code_to_description", "description_to_code"):
            self.assertEqual(Counter(p["chapter"] for p in probes if p["type"] == t),
                             {1: 3, 2: 3})
        for a in ("billable", "header"):
            self.assertEqual(Counter(p["chapter"] for p in probes
                                     if p.get("answer") == a), {1: 3, 2: 3})


class FieldsAndIdsTests(FixtureCase):
    def test_common_fields(self):
        probes = self.full()
        self.assertEqual(len({p["id"] for p in probes}), len(probes))
        for p in probes:
            self.assertEqual(p["code_set"], "ICD-10-CM FY2027 (October 1, 2026 release)")
            self.assertIn(p["source"], ("order.txt", "addenda.txt"))
            self.assertEqual(p["origin"], ORIGIN)
            for key in ("id", "type", "chapter", "answer"):
                self.assertIn(key, p)


class LiteTests(FixtureCase):
    def test_lite_subset(self):
        full = self.full()
        lite = build_lite(full, fx.LITE, random.Random(2))
        by_id = {p["id"]: p for p in full}
        for p in lite:
            self.assertEqual(p, by_id[p["id"]])
        self.assertEqual(Counter(p["type"] for p in lite),
                         {"code_to_description": 3, "description_to_code": 3, "status": 9})
        self.assertEqual(Counter(p["answer"] for p in lite if p["type"] == "status"),
                         {"billable": 3, "header": 3, "not_a_code": 3})
        self.assertEqual(Counter(p.get("kind") for p in lite if "kind" in p),
                         {k: 1 for k in KINDS})

    def test_lite_answer_positions_balanced(self):
        sizes = dict(fx.FULL, code_to_description=8)
        for seed in range(10):
            full = build_full(self.cs, sizes, random.Random(seed))
            lite = build_lite(full, dict(fx.LITE, code_to_description=4),
                              random.Random(seed))
            self.assertEqual(Counter(p["answer"] for p in lite
                                     if p["type"] == "code_to_description"),
                             {"A": 1, "B": 1, "C": 1, "D": 1})


class DeterminismTests(FixtureCase):
    def test_same_seed_same_probes(self):
        self.assertEqual(self.full(5), self.full(5))
        self.assertNotEqual(self.full(5), self.full(6))

    def test_generate_byte_identical(self):
        outs = []
        for name in ("a", "b"):
            out = self.dir / name
            manifest = generate(out, paths=self.paths, root=self.dir,
                                full_sizes=fx.FULL, lite_sizes=fx.LITE)
            files = {f: (out / f).read_bytes() for f in
                     ("probes_full.jsonl", "probes_lite.jsonl", "probes_changes.jsonl",
                      "manifest.json")}
            outs.append(files)
            for f in ("probes_full.jsonl", "probes_lite.jsonl", "probes_changes.jsonl"):
                self.assertEqual(manifest["outputs_sha256"][f],
                                 hashlib.sha256(files[f]).hexdigest())
            self.assertEqual(json.loads(files["manifest.json"]), manifest)
        self.assertEqual(outs[0], outs[1])

    def test_manifest_contents(self):
        m = generate(self.dir / "o", paths=self.paths, root=self.dir,
                     full_sizes=fx.FULL, lite_sizes=fx.LITE)
        self.assertIsInstance(m["seed"], int)
        self.assertEqual(set(m["refdata_sha256"]), {"order.txt", "addenda.txt", "tabular.xml"})
        self.assertEqual(m["refdata_sha256"]["order.txt"],
                         hashlib.sha256(self.paths["order"].read_bytes()).hexdigest())
        self.assertEqual(m["counts"]["full"]["by_type"]["status"], 18)
        self.assertNotIn("deleted", m["counts"]["lite"]["not_a_code_by_kind"])
        self.assertEqual(m["counts"]["changes"]["by_change"],
                         {"added_billable": 5, "added_header": 1,
                          "billable_to_header": 1, "removed": 1})
        self.assertEqual(sum(m["counts"]["full"]["code_to_description_by_answer"].values()), 6)
        self.assertIn("python_version", m)
        self.assertNotIn("time", json.dumps(m).lower())


if __name__ == "__main__":
    unittest.main()
