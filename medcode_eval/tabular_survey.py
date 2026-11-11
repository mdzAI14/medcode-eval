"""Survey of the ICD-10-CM tabular XML: what a checker could read from it.

All counts are computed from the tabular file and the order file through
medcode_eval.tabular and medcode_eval.orderfile. Definitions used:

  level        where a note sits: introduction, chapter, section, or for a
               diag: category (3 characters), code (billable in the order
               file) or subcategory (any other diag)
  stored code  a code in the order file (billable or header)
  resolves     a reference resolves when each code in it is a stored code or
               a prefix of stored codes (tabular.reference_resolves)
  note class   all / some / none_unresolved by how many of a note's
               references resolve; no_refs when it has none
               (tabular.classify_note); "none" in the report is
               none_unresolved plus no_refs
  explained    a 7-character billable code whose nearest diag at or above it
               with a sevenChrDef lists its 7th character; the rest are
               tabular_diag_no_definition (the code is itself a diag in the
               XML), no_definition, or char_not_listed
  in scope     a note is in scope of a code when it sits on the code's
               nearest diag, an ancestor diag, its section or its chapter
               (an assumption about inheritance; the XSD does not state it)

Usage (from the repo root):
    venv/bin/python -m medcode_eval.tabular_survey [--json OUT.json]
prints the markdown tables; --json also writes every count.
"""

import argparse
import json
from collections import Counter, defaultdict

from medcode_eval import orderfile, tabular
from medcode_eval.part_a.generate import CODE_SET, DEFAULT_PATHS, REPO_ROOT

CLASSES = ("all", "some", "none_unresolved", "no_refs")
LEVELS = ("introduction", "chapter", "section", "category", "subcategory", "code")
REPORT_KINDS = tabular.NOTE_KINDS + ("sevenChrDef", "instruction")
RULE_KINDS = ("excludes1", "excludes2", "codeFirst", "useAdditionalCode", "codeAlso")
LIMIT = 20
DEF_REASON = "7th character from a definition"


def _spread(items, n=3):
    """Up to n items spread evenly over the list (deterministic)."""
    if len(items) <= n:
        return list(items)
    return [items[i * len(items) // n] for i in range(n)]


def _owner_label(note, tree):
    if note.owner_type == "diag":
        return tree.diags[note.owner].name
    return f"{note.owner_type} {note.owner}"


def _level(note, billable):
    if note.owner_type == "diag":
        return tabular.diag_level(note.owner, billable)
    return note.owner_type


def _by_length(codes):
    """{str(length): count}, shortest first (string keys, as in the JSON)."""
    return {str(k): n for k, n in sorted(Counter(len(c) for c in codes).items())}


def _ordered(counter, order):
    return {k: counter[k] for k in order if counter.get(k)}


def survey(path, stored, billable):
    """Every count the report uses, as a JSON-ready dict."""
    stored, billable = set(stored), set(billable)
    tree = tabular.load_tree(path)
    census = tabular.element_census(path)
    prefixes = tabular.prefix_set(stored)

    # --- notes by kind -------------------------------------------------
    by_kind = defaultdict(list)
    for n in tree.notes:
        by_kind[n.kind].append(n)
    notes = {}
    for kind in REPORT_KINDS:
        rows = by_kind.get(kind, [])
        levels, classes, examples = Counter(), Counter(), defaultdict(list)
        refs = resolved = 0
        for n in rows:
            levels[_level(n, billable)] += 1
            c = tabular.classify_note(n.text, prefixes)
            classes[c] += 1
            examples[c].append(n)
            found = tabular.find_references(n.text)
            refs += len(found)
            resolved += sum(tabular.reference_resolves(r, prefixes) for r in found)
        notes[kind] = {
            "elements": census.get(kind, {}).get("count", 0),
            "notes": len(rows),
            "notes_by_level": _ordered(levels, LEVELS),
            "classes": {c: classes[c] for c in CLASSES},
            "references": refs,
            "references_resolved": resolved,
            "examples": {c: [[_owner_label(n, tree), n.text] for n in _spread(examples[c])]
                         for c in CLASSES},
        }

    # --- 7th character -------------------------------------------------
    defs = [d for d in tree.diags.values() if d.seven_chr is not None]
    nested = [d.code for d in defs
              if any(tree.diags[a].seven_chr is not None
                     for a in tabular.scope_of(d.code, tree).diags[1:])]
    nested_differ = []
    for c in nested:
        above = next(tree.diags[a] for a in tabular.scope_of(c, tree).diags[1:]
                     if tree.diags[a].seven_chr is not None)
        if set(tree.diags[c].seven_chr) != set(above.seven_chr):
            nested_differ.append([tree.diags[c].name, above.name])
    note_owners = {n.owner for n in by_kind.get("sevenChrNote", [])}
    def_owners = {d.code for d in defs}
    char_sets = Counter("".join(c for c, _ in d.seven_chr) for d in defs)
    seven = [c for c in sorted(billable) if len(c) == 7]
    explained, unexplained, farther = [], [], 0
    base_forms = Counter()
    for c in seven:
        src = tabular.seven_chr_source(c, tree)
        if src is None:
            unexplained.append((c, "tabular_diag_no_definition" if c in tree.diags
                                else "no_definition"))
            continue
        if c[6] in {ch for ch, _ in src.seven_chr}:
            explained.append(c)
            near = tabular.nearest_diag(c, tree)
            if c[:6] == near.code:
                base_forms["first 6 characters are a tabular diag"] += 1
            elif c[:6] == near.code + "X" * (6 - len(near.code)):
                base_forms["tabular diag padded with X to 6 characters"] += 1
            else:
                base_forms["other"] += 1
        else:
            unexplained.append((c, "char_not_listed"))
            if any(tree.diags[a].seven_chr and c[6] in {ch for ch, _ in tree.diags[a].seven_chr}
                   for a in tabular.scope_of(c, tree).diags):
                farther += 1
    explained_set = set(explained)
    short_under_def = sorted(c for c in billable if len(c) < 7
                             and tabular.seven_chr_source(c, tree) is not None)
    x6 = [c for c in sorted(stored) if len(c) == 7 and c[5] == "X"]
    x_codes = Counter()
    for c in stored:
        xs = [i for i in range(3, min(len(c), 6)) if c[i] == "X"]
        if not xs:
            continue
        near = tabular.nearest_diag(c, tree)
        if near is not None and max(xs) < len(near.code):
            form = "X is in a tabular diag name"
        elif (near is not None and len(c) == 7 and c in explained_set
              and c[:6] == near.code + "X" * (6 - len(near.code))):
            form = "X pads a tabular diag to 6 characters before a 7th character"
        else:
            form = "other"
        x_codes[(form, "billable" if c in billable else "header")] += 1
    x_intro = [d for d in tree.diags.values()
               if d.code[-1] == "X" and len(d.code) > 3]
    placeholder = [d for d in tree.diags.values() if d.placeholder]
    seventh = {
        "defs": len(defs),
        "defs_by_level": _ordered(Counter(tabular.diag_level(d.code, billable)
                                          for d in defs), LEVELS),
        "defs_by_name_length": _by_length(d.code for d in defs),
        "defs_with_def_on_ancestor": len(nested),
        "defs_with_def_on_ancestor_examples": nested[:LIMIT],
        "defs_differing_from_def_above": len(nested_differ),
        "defs_differing_from_def_above_examples": nested_differ[:LIMIT],
        "def_without_seven_chr_note": len(def_owners - note_owners),
        "seven_chr_note_without_def": len(note_owners - def_owners),
        "extensions": sum(len(d.seven_chr) for d in defs),
        "char_sets_top": char_sets.most_common(10),
        "char_sets_distinct": len(char_sets),
        "billable_7": len(seven),
        "billable_7_explained": len(explained),
        "billable_7_explained_base_forms": dict(base_forms),
        "billable_7_unexplained_count": len(unexplained),
        "billable_7_unexplained_by_reason": dict(Counter(r for _, r in unexplained)),
        "billable_7_unexplained": unexplained[:LIMIT],
        "billable_7_unexplained_but_farther_def_lists_char": farther,
        "billable_under_def_shorter_than_7": len(short_under_def),
        "billable_under_def_shorter_than_7_examples": short_under_def[:LIMIT],
        "x6_codes": len(x6),
        "x6_billable": sum(c in billable for c in x6),
        "x6_explained": sum(c in explained_set for c in x6),
        "x_in_positions_4_to_6": {f"{f} ({b})": n for (f, b), n in sorted(x_codes.items())},
        "xml_diags_ending_in_x": len(x_intro),
        "xml_diags_ending_in_x_with_placeholder_true": sum(d.placeholder for d in x_intro),
        "placeholder_true": len(placeholder),
        "placeholder_true_name_ends_in_x": sum(d.code[-1] == "X" for d in placeholder),
        "placeholder_true_by_name_length": _by_length(d.code for d in placeholder),
        "placeholder_true_with_def_in_scope": sum(
            tabular.seven_chr_source(d.code, tree) is not None for d in placeholder),
    }

    # --- order file against XML ----------------------------------------
    xml = set(tree.diags)
    xml_only = sorted(xml - stored)
    order_only = sorted(stored - xml)
    reasons = Counter(DEF_REASON if c in explained_set else "other" for c in order_only)
    other = [c for c in order_only if c not in explained_set]
    flags = Counter()
    flag_examples = defaultdict(list)
    for c in sorted(xml & stored):
        d = tree.diags[c]
        under_def = tabular.seven_chr_source(c, tree) is not None
        leaf = not d.children
        key = ("billable" if c in billable else "header",
               "leaf" if leaf else "has children",
               "7th character in scope" if under_def else "no 7th character in scope")
        flags[key] += 1
        if len(flag_examples[key]) < 5:
            flag_examples[key].append(d.name)
    order_vs_xml = {
        "xml_codes": len(xml),
        "order_codes": len(stored),
        "xml_only_count": len(xml_only),
        "xml_only": xml_only[:LIMIT],
        "order_only_count": len(order_only),
        "order_only_by_reason": {k: reasons[k] for k in (DEF_REASON, "other") if reasons[k]},
        "order_only_examples": order_only[:LIMIT],
        "order_only_other_examples": other[:LIMIT],
        "order_only_by_length": _by_length(order_only),
        "shared_by_flag_shape": [[*k, n, flag_examples[k]] for k, n in sorted(flags.items())],
    }

    # --- coverage for proposed rules --------------------------------------
    owner_kinds = defaultdict(lambda: defaultdict(lambda: [False, False]))
    for n in tree.notes:
        if n.kind in RULE_KINDS:
            slot = owner_kinds[(n.owner_type, n.owner)][n.kind]
            slot[0] = True
            if any(tabular.reference_resolves(r, prefixes)
                   for r in tabular.find_references(n.text)):
                slot[1] = True
    coverage = {k: {"any_note": 0, "resolvable_note": 0} for k in RULE_KINDS}
    no_scope = 0
    for c in billable:
        sc = tabular.scope_of(c, tree)
        if not sc.diags:
            no_scope += 1
            continue
        owners = [("diag", d) for d in sc.diags] + [("section", sc.section),
                                                     ("chapter", str(sc.chapter))]
        for k in RULE_KINDS:
            slots = [owner_kinds[o][k] for o in owners if o in owner_kinds]
            if any(s[0] for s in slots):
                coverage[k]["any_note"] += 1
            if any(s[1] for s in slots):
                coverage[k]["resolvable_note"] += 1

    return {
        "code_set": CODE_SET,
        "tabular_version": tree.version,
        "census": census,
        "notes": notes,
        "seventh": seventh,
        "order_vs_xml": order_vs_xml,
        "coverage": {"billable": len(billable), "billable_without_tabular_diag": no_scope,
                     "by_kind": coverage},
    }


def _cut(text, n=110):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 3] + "..."


def to_markdown(s):
    out = [f"Code set: {s['code_set']}. Tabular <version>: {s['tabular_version']}.\n\n"]
    out.append("### a. Elements\n\n| Element | Count | Parents (count) | Attributes |\n"
               "|---|---|---|---|\n")
    for tag, e in sorted(s["census"].items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        parents = ", ".join(f"{p} {n}" for p, n in sorted(e["parents"].items(),
                                                          key=lambda x: -x[1])) or "(root)"
        attrs = ", ".join(f"{a} {n}" for a, n in e["attributes"].items()) or ""
        out.append(f"| {tag} | {e['count']} | {parents} | {attrs} |\n")
    out.append("\n### b. Notes by kind\n\n| Kind | Elements | Notes | Notes by level "
               "| all | some | none (unresolved refs) | none (no refs) | References "
               "(resolved) |\n|---|---|---|---|---|---|---|---|---|\n")
    for k, v in s["notes"].items():
        lv = ", ".join(f"{a} {n}" for a, n in v["notes_by_level"].items())
        c = v["classes"]
        out.append(f"| {k} | {v['elements']} | {v['notes']} | {lv} | {c['all']} | "
                   f"{c['some']} | {c['none_unresolved']} | {c['no_refs']} | "
                   f"{v['references']} ({v['references_resolved']}) |\n")
    out.append("\nExamples (owner: note text), three per class where there are any:\n\n")
    for k, v in s["notes"].items():
        out.append(f"- **{k}**\n")
        for c in CLASSES:
            ex = v["examples"][c]
            if ex:
                out.append(f"  - {c}: " + " ; ".join(f"{o}: \"{_cut(t)}\"" for o, t in ex)
                           + "\n")
    out.append("\n### c. 7th character\n\n```\n")
    for k, v in s["seventh"].items():
        out.append(f"{k}: {json.dumps(v)}\n")
    out.append("```\n\n### d. Order file against XML\n\n```\n")
    for k, v in s["order_vs_xml"].items():
        if k == "shared_by_flag_shape":
            out.append(f"{k}:\n")
            for row in v:
                out.append(f"  {row[0]} | {row[1]} | {row[2]}: {row[3]}  e.g. "
                           f"{', '.join(row[4])}\n")
        else:
            out.append(f"{k}: {json.dumps(v)}\n")
    out.append("```\n\n### Coverage (billable codes with a note of the kind in scope)\n\n"
               f"Billable codes: {s['coverage']['billable']}; without a tabular diag "
               f"above them: {s['coverage']['billable_without_tabular_diag']}.\n\n"
               "| Kind | Any note in scope | Note with a resolvable reference in scope |\n"
               "|---|---|---|\n")
    for k, v in s["coverage"]["by_kind"].items():
        out.append(f"| {k} | {v['any_note']} | {v['resolvable_note']} |\n")
    return "".join(out)


def load_real(root=REPO_ROOT):
    """(tabular path, stored codes, billable codes) from refdata."""
    recs = orderfile.load(root / DEFAULT_PATHS["order"])
    return (root / DEFAULT_PATHS["tabular"], {r.code for r in recs},
            {r.code for r in recs if r.billable})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Survey the ICD-10-CM tabular XML.")
    ap.add_argument("--json", help="also write every count to this file")
    args = ap.parse_args(argv)
    s = survey(*load_real())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(s, indent=2, sort_keys=True) + "\n")
    print(to_markdown(s), end="")
    return s


if __name__ == "__main__":
    main()
