"""ICD-10-CM claim checker, v0, for ICD-10-CM FY2027 (October 1, 2026 release).

Usage (from the repo root):
    venv/bin/python -m medcode_eval.checker CODE [CODE ...]

Codes are in claim order; the first is first-listed. Dotted or undotted,
any case. stdout is one JSON object: the code-set release, the codes as
given and as normalised, and the findings. Exit 0 with no error-level
finding, 1 with any, 2 for a usage or setup problem.

check(codes) returns the findings; the reference data is loaded once per
process. Code facts come from refdata/icd10cm_fy2027/ only, read through
medcode_eval.orderfile and medcode_eval.tabular.

Rules in v0:
  not_in_code_set      error   the code is not in the order file
  header_not_billable  error   stored with flag 0
  manifestation_first  error   the first-listed code's long description
                               contains "in diseases classified elsewhere"
  excludes1_pair       review  an excludes1 note in scope of one code has a
                               reference that matches another code
  code_first_order     review  a codeFirst note in scope of one code has a
                               reference that matches a code listed after it
"In scope" means a note on the code's nearest diag, its ancestor diags, its
section or its chapter. For excludes1 and codeFirst only references inside
parentheses count.

Not in v0: excludes2, use additional code, code also, code first when the
other code is absent, includes and inclusion terms.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from medcode_eval import orderfile, tabular
from medcode_eval.part_a.generate import CODE_SET, DEFAULT_PATHS, REPO_ROOT

PHRASE = "in diseases classified elsewhere"
CHILD_LIMIT = 10
EXAMPLE_LIMIT = 5
_QUALIFIER = re.compile(r"except|character", re.IGNORECASE)
_DOTTED = re.compile(r"[A-Z0-9]{3}\.[A-Z0-9]{1,4}")
PAIR_RULES = {"excludes1": ("excludes1_pair", "review"),
              "codeFirst": ("code_first_order", "review")}


class UsageError(ValueError):
    pass


class SetupError(RuntimeError):
    pass


class RefData:
    """Order file and tabular tree, plus indexes the rules use."""

    def __init__(self, records, tree, paths):
        self.records = {r.code: r for r in records}
        self.tree = tree
        self.order_file = Path(paths["order"]).as_posix()
        self.tabular_file = Path(paths["tabular"]).as_posix()
        self.prefixes = tabular.prefix_set(self.records)
        # (owner_type, owner) -> {kind: [(note index, Note, refs inside parentheses)]}
        self.pair_notes = {}
        for i, n in enumerate(tree.notes):
            if n.kind in PAIR_RULES:
                inside, _ = tabular.split_by_parentheses(n.text)
                self.pair_notes.setdefault((n.owner_type, n.owner), {}) \
                    .setdefault(n.kind, []).append((i, n, inside))
        self.manifestation_instruction = next(
            (n for n in tree.notes if n.kind == "instruction"
             and PHRASE in n.text.lower() and "manifestation" in n.text.lower()), None)


def load(root=REPO_ROOT, paths=None):
    """Read the order and tabular files (paths relative to root)."""
    paths = paths or DEFAULT_PATHS
    root = Path(root)
    try:
        records = orderfile.load(root / paths["order"])
        tree = tabular.load_tree(root / paths["tabular"])
    except (OSError, ValueError, SyntaxError) as exc:
        raise SetupError(f"cannot load reference data: {exc}") from None
    return RefData(records, tree, paths)


_DEFAULT = None


def default_data():
    """The real FY2027 reference data, loaded on first use."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load()
    return _DEFAULT


def normalise(code):
    """Upper case, no surrounding space; a dot is removed only when it is
    the single dot after the third character. Other forms are kept as
    given (upper-cased), so they are not stored codes."""
    s = code.strip().upper()
    if not s:
        raise UsageError("an empty code was given")
    if _DOTTED.fullmatch(s):
        return s.replace(".", "")
    return s


def dotted(code):
    return code if len(code) <= 3 else f"{code[:3]}.{code[3:]}"


# ---------------------------------------------------------------------------
# sources

def _order_source(data, code, element="record", text=None):
    s = {"file": data.order_file, "element": element, "owner_type": "code",
         "owner": dotted(code) if code else None}
    if text is not None:
        s["text"] = text
    return s


def _owner_label(data, owner_type, owner):
    return data.tree.diags[owner].name if owner_type == "diag" else owner


def _note_source(data, note):
    return {"file": data.tabular_file, "element": note.kind, "owner_type": note.owner_type,
            "owner": _owner_label(data, note.owner_type, note.owner), "text": note.text}


def _seven_source(data, diag):
    return {"file": data.tabular_file, "element": "sevenChrDef", "owner_type": "diag",
            "owner": diag.name, "extensions": [list(e) for e in diag.seven_chr]}


def _owners(code, tree):
    sc = tabular.scope_of(code, tree)
    if not sc.diags:
        return []
    return ([("diag", d) for d in sc.diags]
            + [("section", sc.section), ("chapter", str(sc.chapter))])


def _scope_notes(data, code, kind):
    out = []
    for o in _owners(code, data.tree):
        out.extend(data.pair_notes.get(o, {}).get(kind, []))
    return out


def _finding(rule, level, codes, message, source, **extra):
    f = {"rule": rule, "level": level, "codes": list(codes), "message": message,
         "source": source}
    f.update(extra)
    return f


# ---------------------------------------------------------------------------
# rules

def _not_in_code_set(data, code):
    details, source = {}, [_order_source(data, None)]
    prefix = next((code[:n] for n in range(len(code) - 1, 2, -1)
                   if code[:n] in data.records), None)
    if prefix is None:
        details["longest_stored_prefix"] = None
        msg = f"{code} is not a code in the code set; no stored code is a prefix of it."
    else:
        rec = data.records[prefix]
        details["longest_stored_prefix"] = {"code": dotted(prefix), "billable": rec.billable}
        msg = (f"{code} is not a code in the code set. The longest stored prefix is "
               f"{dotted(prefix)} ({'billable' if rec.billable else 'header'}).")
        source.append(_order_source(data, prefix))
    tree = data.tree
    if len(code) == 7 and code.isalnum():
        src = tabular.seven_chr_source(code, tree)
        if src is not None:
            allowed = [c for c, _ in src.seven_chr]
            if code[6] not in allowed:
                details["allowed_7th_characters"] = allowed
                msg += (f" Its 7th character {code[6]} is not allowed by the definition at "
                        f"{src.name}; allowed: {', '.join(allowed)}.")
                source.append(_seven_source(data, src))
    base = code[:-1]
    if 3 <= len(base) < 6 and base in tree.diags:
        src = tabular.seven_chr_source(base, tree)
        if src is not None and code[-1] in {c for c, _ in src.seven_chr}:
            padded = base.ljust(6, "X") + code[-1]
            if padded in data.records:
                details["padded_code"] = dotted(padded)
                msg += (f" With the placeholder X it is {dotted(padded)}, a stored code.")
                source.append(_seven_source(data, src))
                source.append(_order_source(data, padded))
    return _finding("not_in_code_set", "error", [code], msg, source, details=details)


def _header(data, code):
    tree = data.tree
    d = tree.diags.get(code)
    kids = [tree.diags[c].name for c in d.children] if d else []
    source = [_order_source(data, code)]
    src = tabular.seven_chr_source(code, tree)
    details = {}
    if src is not None:
        allowed = [c for c, _ in src.seven_chr]
        base = code.ljust(6, "X")
        pad = len(code) < 6 and any(base + c in data.records for c in allowed)
        details.update(case="seventh_character_needed", allowed_7th_characters=allowed,
                       seventh_character_from=src.name, x_padding_needed=pad)
        msg = (f"{dotted(code)} is a header, not billable. A 7th character is needed "
               f"(definition at {src.name}): {', '.join(allowed)}.")
        if pad:
            details["padded_base"] = dotted(base)
            msg += f" Pad with X to 6 characters first: {dotted(base)} plus the 7th character."
        source.append(_seven_source(data, src))
        if kids:
            details["children"] = kids[:CHILD_LIMIT]
            details["children_total"] = len(kids)
            msg += f" More specific codes below it: {', '.join(kids[:CHILD_LIMIT])}."
    else:
        details.update(case="more_specific_codes", children=kids[:CHILD_LIMIT],
                       children_total=len(kids))
        more = f" (first {CHILD_LIMIT} of {len(kids)})" if len(kids) > CHILD_LIMIT else ""
        msg = (f"{dotted(code)} is a header, not billable. More specific codes exist"
               f"{more}: {', '.join(kids[:CHILD_LIMIT])}.")
        if d is not None:
            source.append({"file": data.tabular_file, "element": "diag", "owner_type": "diag",
                           "owner": d.name})
    return _finding("header_not_billable", "error", [code], msg, source, details=details)


def _manifestation(data, code):
    rec = data.records[code]
    source = [_order_source(data, code, "long description", rec.long)]
    if data.manifestation_instruction is not None:
        source.append(_note_source(data, data.manifestation_instruction))
    for _, note, _ in _scope_notes(data, code, "codeFirst"):
        source.append(_note_source(data, note))
    msg = (f"{dotted(code)} is first-listed, and its title contains '{PHRASE}': "
           "such manifestation codes are not first-listed.")
    return _finding("manifestation_first", "error", [code], msg, source)


def _pairs(data, norm):
    out, seen = [], set()
    for i, a in enumerate(norm):
        if a not in data.records:
            continue
        for kind, (rule, level) in PAIR_RULES.items():
            for idx, note, refs in _scope_notes(data, a, kind):
                for j, b in enumerate(norm):
                    if b == a or b not in data.records:
                        continue
                    if kind == "codeFirst" and j < i:
                        continue
                    ref = next((r for r in refs if tabular.reference_matches(r, b)), None)
                    if ref is None:
                        continue
                    key = (frozenset((a, b)), idx)
                    if key in seen:
                        continue
                    seen.add(key)
                    extra = {"details": {"reference": ref.text, "note_in_scope_of": dotted(a)}}
                    if kind == "excludes1":
                        extra["qualified"] = bool(_QUALIFIER.search(note.text))
                        msg = (f"{dotted(b)} matches {ref.text} in an excludes1 note in scope "
                               f"of {dotted(a)}; check whether both belong on the claim.")
                    else:
                        msg = (f"{dotted(b)} matches {ref.text} in a codeFirst note in scope "
                               f"of {dotted(a)} but is listed after it.")
                    out.append(_finding(rule, level, [a, b], msg,
                                        [_note_source(data, note)], **extra))
    return out


def check(codes, data=None):
    """Findings for codes in claim order (first is first-listed)."""
    data = data or default_data()
    norm = [normalise(c) for c in codes]
    findings = []
    for code in norm:
        rec = data.records.get(code)
        if rec is None:
            findings.append(_not_in_code_set(data, code))
        elif not rec.billable:
            findings.append(_header(data, code))
    if norm and norm[0] in data.records and PHRASE in data.records[norm[0]].long.lower():
        findings.append(_manifestation(data, norm[0]))
    findings.extend(_pairs(data, norm))
    return findings


def parenthesis_counts(data=None):
    """For excludes1 and codeFirst notes: references inside parentheses, and
    the resolvable references outside them (left out by v0)."""
    data = data or default_data()
    out = {}
    for kind in PAIR_RULES:
        inside = outside = resolvable = 0
        examples = []
        for n in data.tree.notes:
            if n.kind != kind:
                continue
            ins, outs = tabular.split_by_parentheses(n.text)
            inside += len(ins)
            outside += len(outs)
            for r in outs:
                if tabular.reference_resolves(r, data.prefixes):
                    resolvable += 1
                    if len(examples) < EXAMPLE_LIMIT:
                        examples.append({"owner": _owner_label(data, n.owner_type, n.owner),
                                         "reference": r.text, "note": n.text})
        out[kind] = {"inside": inside, "outside": outside,
                     "outside_resolvable": resolvable, "examples": examples}
    return out


def main(argv=None, data=None, root=REPO_ROOT, paths=None):
    ap = argparse.ArgumentParser(prog="python -m medcode_eval.checker",
                                 description="Check ICD-10-CM codes in claim order.")
    ap.add_argument("codes", nargs="+", metavar="CODE")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        norm = [normalise(c) for c in args.codes]
        if data is None:
            data = load(root, paths) if (paths or Path(root) != REPO_ROOT) else default_data()
        findings = check(args.codes, data=data)
    except (UsageError, SetupError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"code_set": CODE_SET, "tabular_version": data.tree.version,
                      "codes_given": list(args.codes), "codes_normalised": norm,
                      "findings": findings}, indent=2))
    return 1 if any(f["level"] == "error" for f in findings) else 0
