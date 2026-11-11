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
    def test_equal_with_remainder_in_chapter_order(self):
        self.assertEqual(allocate(10, [(1, 5), (2, 5), (3, 5)]), {1: 4, 2: 3, 3: 3})

    def test_shortfall_spread_in_chapter_order(self):
        self.assertEqual(allocate(10, [(1, 1), (2, 10), (3, 10)]), {1: 1, 2: 5, 3: 4})

    def test_empty_chapter(self):
        self.assertEqual(allocate(3, [(1, 0), (2, 5)]), {1: 0, 2: 3})

    def test_cascading_shortfall(self):
        self.assertEqual(allocate(9, [(1, 1), (2, 2), (3, 10)]), {1: 1, 2: 2, 3: 6})

    def test_over_capacity(self):
        with self.assertRaises(ValueError):
            allocate(5, [(1, 2), (2, 2)])


class CodeSetTests(FixtureCase):
    def test_deleted_only_absent_codes(self):
        # U92 is deleted and re-added; only U958 is absent from the order file
        self.assertEqual(self.cs.deleted, ["U958"])

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

    def test_answer_position_varies(self):
        letters = set()
        for seed in range(10):
            letters |= {p["answer"] for p in self.full(seed)
                        if p["type"] == "code_to_description"}
        self.assertGreater(len(letters), 1)


class DescriptionToCodeTests(FixtureCase):
    def test_shared_descriptions_left_out(self):
        for seed in range(20):
            answers = {p["answer"] for p in self.full(seed)
                       if p["type"] == "description_to_code"}
            self.assertFalse(answers & {"U9312", "U971"})

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
                         {"billable": 8, "header": 8, "not_a_code": 8})

    def test_kind_counts(self):
        kinds = Counter(p["kind"] for p in self.status() if p["answer"] == "not_a_code")
        # 1 deleted (all of them); 7 left shared 3, 2, 2 in kind order
        self.assertEqual(kinds, {"deleted": 1, "substituted": 3, "extended": 2,
                                 "placeholder_prefix": 2})

    def test_deleted_capped_at_half_quota(self):
        self.cs.deleted = ["U9" + c for c in "ABCDEF"]  # invented, absent
        probes = build_full(self.cs, fx.FULL, random.Random(1))
        kinds = Counter(p.get("kind") for p in probes if p.get("answer") == "not_a_code")
        self.assertEqual(kinds["deleted"], 4)
        self.assertEqual(sum(kinds.values()), 8)

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
                    if kind == "deleted":
                        self.assertIn(code, self.cs.deleted)
                        self.assertNotIn("derived_from", p)
                        continue
                    src = p["derived_from"]
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

    def test_deleted_chapter_from_ranges(self):
        p = [p for p in self.status() if p.get("kind") == "deleted"][0]
        self.assertEqual((p["code"], p["chapter"], p["source"]),
                         ("U95.8", 2, "addenda.txt"))


class BalanceTests(FixtureCase):
    def test_chapter_balance(self):
        probes = self.full()
        for t in ("code_to_description", "description_to_code"):
            self.assertEqual(Counter(p["chapter"] for p in probes if p["type"] == t),
                             {1: 3, 2: 3})
        for a in ("billable", "header"):
            self.assertEqual(Counter(p["chapter"] for p in probes
                                     if p.get("answer") == a), {1: 4, 2: 4})


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
                         {"code_to_description": 3, "description_to_code": 3, "status": 12})
        self.assertEqual(Counter(p["answer"] for p in lite if p["type"] == "status"),
                         {"billable": 4, "header": 4, "not_a_code": 4})
        self.assertEqual(Counter(p.get("kind") for p in lite if "kind" in p),
                         {k: 1 for k in KINDS})


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
                     ("probes_full.jsonl", "probes_lite.jsonl", "manifest.json")}
            outs.append(files)
            for f in ("probes_full.jsonl", "probes_lite.jsonl"):
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
        self.assertEqual(m["counts"]["full"]["by_type"]["status"], 24)
        self.assertEqual(m["counts"]["lite"]["not_a_code_by_kind"]["deleted"], 1)
        self.assertIn("python_version", m)
        self.assertNotIn("time", json.dumps(m).lower())


if __name__ == "__main__":
    unittest.main()
