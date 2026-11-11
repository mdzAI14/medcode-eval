"""Validate the Part B folders (ICD-10-CM FY2027, October 1, 2026 release).

Usage (from the repo root):
    venv/bin/python -m medcode_eval.part_b.validate [--data-dir DIR]

DIR (default data/) holds specs/, cases/ and gold/. Each case is three
files with the same id: specs/<id>.md, cases/<id>.md, gold/<id>.json.
The fields are described in docs/part_b_schema.md. README.md and .gitkeep
in those folders are ignored.

The validator reports and never changes a file. Exit 0 with no problem
(warnings and checker review findings do not count), 1 with any problem,
2 for a usage or setup problem.

Code facts come from refdata/icd10cm_fy2027/ only, through
medcode_eval.checker (which reads medcode_eval.orderfile and
medcode_eval.tabular).
"""

import argparse
import datetime
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from medcode_eval import checker, tabular
from medcode_eval.part_a.generate import CODE_SET, REPO_ROOT

ID_RE = re.compile(r"^[a-z0-9-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPECIALTIES = ("ortho", "ophtho", "gi", "ent", "ed")
TRAPS = ("laterality", "seventh_character", "excludes1", "combination", "sequencing")
METHODS = ("ai_assisted_coder_verified", "coder_unassisted")
IGNORED = {"README.md", ".gitkeep"}
FOLDERS = {"spec": ("specs", ".md"), "case": ("cases", ".md"), "gold": ("gold", ".json")}
SPEC_FIELDS = ("id", "specialty", "setting", "author", "date")
CASE_FIELDS = ("id", "specialty", "setting", "origin", "drafter", "draft_date")
GOLD_FIELDS = ("id", "codes", "citations", "target_trap", "coder_notes", "method",
               "method_detail", "code_set", "date_coded")
DATE_FIELDS = {"date", "draft_date", "date_coded"}
CASE_CITATION = "case"
_LIST_ITEM = re.compile(r"^\s*[-*]\s+\S")


class SetupError(RuntimeError):
    pass


@dataclass
class Item:
    kind: str
    file: str
    message: str
    rule: str = None


@dataclass
class Result:
    case_ids: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    reviews: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# files

def _scan_folder(root, role, result):
    """{id: Path} for one folder; stray entries are problems."""
    folder, ext = FOLDERS[role]
    found = {}
    for p in sorted((root / folder).iterdir()):
        rel = f"{folder}/{p.name}"
        if p.name in IGNORED:
            continue
        if not p.is_file() or p.suffix != ext:
            result.problems.append(Item("stray_file", rel,
                                        f"not a {ext} file; only <id>{ext}, README.md "
                                        "and .gitkeep belong here"))
            continue
        if not ID_RE.match(p.stem):
            result.problems.append(Item("bad_id", rel,
                                        f"file name id {p.stem!r} does not match "
                                        f"{ID_RE.pattern}"))
        found[p.stem] = p
    return found


def parse_front_matter(text):
    """(fields, duplicates, body, body_first_line) or None when the text
    does not open with a --- ... --- block of key: value lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    fields, dups = {}, []
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            return None
        key = key.strip()
        if key in fields:
            dups.append(key)
        fields[key] = value.strip()
    return fields, dups, "\n".join(lines[end + 1:]), end + 2


def _check_date(value, name, rel, result):
    ok = isinstance(value, str) and DATE_RE.match(value)
    if ok:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            ok = False
    if not ok:
        result.problems.append(Item("bad_date", rel, f"{name} {value!r} is not a YYYY-MM-DD date"))


def _check_fields(present, required, rel, result):
    for k in required:
        v = present.get(k)
        if k not in present or (isinstance(v, str) and not v.strip() and k != "coder_notes"):
            result.problems.append(Item("missing_field", rel, f"required field {k} is missing "
                                                              "or empty"))
    for k in present:
        if k not in required:
            result.problems.append(Item("unknown_field", rel, f"field {k} is not in the schema"))


def _check_id(value, case_id, rel, result):
    if value is not None and value != case_id:
        result.problems.append(Item("id_mismatch", rel,
                                    f"id field {value!r} does not match the file name "
                                    f"{case_id!r}"))


def _check_markdown(path, role, case_id, rel, result):
    """Front matter fields of a spec or case, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        result.problems.append(Item("bad_encoding", rel, f"not UTF-8 text: {exc}"))
        return None, ""
    parsed = parse_front_matter(text)
    if parsed is None:
        result.problems.append(Item("front_matter", rel,
                                    "no front matter: the file must open with a --- line, "
                                    "key: value lines and a closing --- line"))
        return None, text
    fields, dups, body, _ = parsed
    for k in dups:
        result.problems.append(Item("duplicate_field", rel, f"field {k} appears more than once"))
    _check_fields(fields, SPEC_FIELDS if role == "spec" else CASE_FIELDS, rel, result)
    _check_id(fields.get("id"), case_id, rel, result)
    sp = fields.get("specialty")
    if sp and sp not in SPECIALTIES:
        result.problems.append(Item("bad_enum", rel, f"specialty {sp!r} is not one of "
                                                     f"{', '.join(SPECIALTIES)}"))
    for k in DATE_FIELDS & fields.keys():
        if fields[k]:
            _check_date(fields[k], k, rel, result)
    if role == "spec" and not any(_LIST_ITEM.match(l) for l in body.splitlines()):
        result.problems.append(Item("empty_body", rel,
                                    "no clinical facts: the body needs a list (lines "
                                    "starting with '- ')"))
    if role == "case" and not body.strip():
        result.problems.append(Item("empty_body", rel, "no note text after the front matter"))
    return fields, text


# ---------------------------------------------------------------------------
# codes in text

def _scan_text(text, rel, data, result):
    """Dotted stored codes or prefixes are problems; undotted stored
    categories are warnings."""
    for n, line in enumerate(text.splitlines(), start=1):
        for ref in tabular.find_references(line.upper()):
            ends = [ref.first] + ([ref.last] if ref.last else [])
            if "." in ref.text:
                if any(e in data.prefixes for e in ends):
                    result.problems.append(Item(
                        "code_in_text", rel,
                        f"line {n}: {ref.text} is a stored code or a prefix of stored codes"))
            elif any(len(e) == 3 and e in data.records for e in ends):
                result.warnings.append(Item(
                    "category_in_text", rel,
                    f"line {n}: {ref.text} is (or holds) a stored category; check it is not "
                    "a code"))


# ---------------------------------------------------------------------------
# gold

def _check_gold(path, case_id, rel, data, result):
    try:
        g = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        result.problems.append(Item("bad_json", rel, f"not valid JSON: {exc}"))
        return
    if not isinstance(g, dict):
        result.problems.append(Item("bad_json", rel, "the top level is not a JSON object"))
        return
    _check_fields(g, GOLD_FIELDS, rel, result)
    _check_id(g.get("id"), case_id, rel, result)
    for k in ("id", "target_trap", "coder_notes", "method", "method_detail", "code_set",
              "date_coded"):
        if k in g and not isinstance(g[k], str):
            result.problems.append(Item("bad_type", rel, f"{k} is not a string"))
    trap = g.get("target_trap")
    if isinstance(trap, str) and trap.strip() and trap not in TRAPS:
        result.problems.append(Item("bad_enum", rel, f"target_trap {trap!r} is not one of "
                                                     f"{', '.join(TRAPS)}"))
    method = g.get("method")
    if isinstance(method, str) and method.strip() and method not in METHODS:
        result.problems.append(Item("bad_enum", rel, f"method {method!r} is not one of "
                                                     f"{', '.join(METHODS)}"))
    cs = g.get("code_set")
    if isinstance(cs, str) and cs.strip() and cs != CODE_SET:
        result.problems.append(Item("bad_code_set", rel,
                                    f"code_set {cs!r} is not {CODE_SET!r}"))
    if isinstance(g.get("date_coded"), str) and g["date_coded"].strip():
        _check_date(g["date_coded"], "date_coded", rel, result)

    codes = g.get("codes")
    norm = None
    if "codes" in g:
        norm = _check_codes(codes, rel, result)
    if "citations" in g:
        _check_citations(g["citations"], codes, norm, rel, result)
    if norm:
        for f in checker.check(codes, data=data):
            item = Item("checker_" + f["level"], rel, f["message"], rule=f["rule"])
            (result.problems if f["level"] == "error" else result.reviews).append(item)


def _check_codes(codes, rel, result):
    """Normalised codes, or None when the list is malformed."""
    if not isinstance(codes, list) or not codes:
        result.problems.append(Item("bad_codes", rel, "codes must be a non-empty list"))
        return None
    norm = []
    for c in codes:
        if not isinstance(c, str):
            result.problems.append(Item("bad_codes", rel, f"code {c!r} is not a string"))
            return None
        try:
            norm.append(checker.normalise(c))
        except checker.UsageError:
            result.problems.append(Item("bad_codes", rel, "codes holds an empty string"))
            return None
    dups = sorted({checker.dotted(c) for c in norm if norm.count(c) > 1})
    if dups:
        result.problems.append(Item("bad_codes", rel, f"codes listed more than once: "
                                                      f"{', '.join(dups)}"))
    return norm


def _check_citations(cit, codes, norm, rel, result):
    def bad(msg):
        result.problems.append(Item("bad_citation", rel, msg))

    if not isinstance(cit, dict) or not cit:
        bad("citations must be a non-empty object: {\"case\": ...} or one key per code")
        return
    by_norm = {}
    for k, v in cit.items():
        if not isinstance(v, str) or not v.strip():
            bad(f"citation for {k!r} is empty or not a string")
        if k == CASE_CITATION:
            continue
        try:
            nk = checker.normalise(k)
        except checker.UsageError:
            nk = k
        if norm is not None and nk not in norm:
            bad(f"citation key {k!r} is not one of the codes")
        by_norm[nk] = k
    if CASE_CITATION not in cit and norm is not None:
        missing = [c for c, n in zip(codes, norm) if n not in by_norm]
        if missing:
            bad(f"no citation for {', '.join(missing)} and no case citation")


# ---------------------------------------------------------------------------

def validate(root, data=None):
    """Result for a data folder holding specs/, cases/ and gold/."""
    root = Path(root)
    for folder, _ in FOLDERS.values():
        if not (root / folder).is_dir():
            raise SetupError(f"folder {folder}/ is missing under {root}")
    data = data or checker.default_data()
    result = Result()
    found = {role: _scan_folder(root, role, result) for role in FOLDERS}
    result.counts = {role: len(v) for role, v in found.items()}
    for role, (folder, ext) in FOLDERS.items():
        for case_id in found[role]:
            rel = f"{folder}/{case_id}{ext}"
            if role == "case":
                for other in ("spec", "gold"):
                    if case_id not in found[other]:
                        result.problems.append(Item(f"missing_{other}", rel,
                                                    f"no {FOLDERS[other][0]}/{case_id}"
                                                    f"{FOLDERS[other][1]}"))
            elif case_id not in found["case"]:
                result.problems.append(Item("missing_case", rel, f"no cases/{case_id}.md"))
    result.case_ids = sorted(found["case"])

    for case_id in sorted(set().union(*found.values())):
        fm = {}
        for role in ("spec", "case"):
            p = found[role].get(case_id)
            if p is None:
                continue
            rel = f"{FOLDERS[role][0]}/{p.name}"
            fields, text = _check_markdown(p, role, case_id, rel, result)
            fm[role] = fields
            _scan_text(text, rel, data, result)
        if fm.get("spec") and fm.get("case"):
            for k in ("specialty", "setting"):
                a, b = fm["spec"].get(k), fm["case"].get(k)
                if a and b and a != b:
                    result.problems.append(Item("spec_case_mismatch", f"cases/{case_id}.md",
                                                f"{k} {b!r} differs from the spec's {a!r}"))
        p = found["gold"].get(case_id)
        if p is not None:
            _check_gold(p, case_id, f"gold/{p.name}", data, result)
    return result


def _section(title, items, show_rule=False):
    lines = [f"{title}: {len(items)}"]
    for it in items:
        tag = f"{it.kind}:{it.rule}" if show_rule and it.rule else it.kind
        lines.append(f"  {it.file}  [{tag}]  {it.message}")
    return lines


def report(result, data_dir):
    c = result.counts
    lines = [f"Part B validation: {CODE_SET}",
             f"data folder: {data_dir}",
             f"files: specs {c.get('spec', 0)}, cases {c.get('case', 0)}, "
             f"gold {c.get('gold', 0)}",
             ""]
    lines += _section("Problems", result.problems, show_rule=True) + [""]
    lines += _section("Warnings", result.warnings) + [""]
    lines += _section("Checker review findings (not problems)", result.reviews,
                      show_rule=True) + [""]
    lines.append("Result: " + ("FAIL" if result.problems else "PASS"))
    return "\n".join(lines)


def main(argv=None, data=None, ref_root=None):
    ap = argparse.ArgumentParser(prog="python -m medcode_eval.part_b.validate",
                                 description="Validate Part B specs, cases and gold.")
    ap.add_argument("--data-dir", default=None,
                    help="folder holding specs/, cases/ and gold/ (default: data/)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    data_dir = Path(args.data_dir) if args.data_dir else REPO_ROOT / "data"
    try:
        if data is None:
            data = checker.load(root=ref_root) if ref_root else checker.default_data()
        result = validate(data_dir, data=data)
    except (SetupError, checker.SetupError, OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        shown = data_dir.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        shown = str(data_dir)
    print(report(result, shown))
    return 1 if result.problems else 0


if __name__ == "__main__":
    sys.exit(main())
