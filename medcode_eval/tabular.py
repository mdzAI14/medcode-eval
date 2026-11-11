"""Chapters of the ICD-10-CM tabular list (icd10cm_tabular_<year>.xml).

How the file expresses chapters (per icd10cm_tabular.xsd and the file):
the root element ICD10CM.tabular has <chapter> children. Each chapter has
a <name> (the chapter number) and a <desc> whose text ends with the
chapter's category range in parentheses, e.g.
"Certain infectious and parasitic diseases (A00-B99)". The chapter element
has no range attribute; its <sectionIndex>/<sectionRef first= last=> and
<section id=> elements give the ranges of its blocks, not of the chapter.

load_chapters reads only the number, title and category range of each
chapter. Categories compare as ASCII strings, which puts digits before
letters (O99 < O9A, Q99 < QA0), the same order the ranges use.

load_tree (below) reads the whole tree: diags, instructional notes and
7th-character definitions; find_references and classify_note read code
references out of note text.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_RANGE = re.compile(r"(.*\S) \(([A-Z0-9]{3})-([A-Z0-9]{3})\)")
_CATEGORY = re.compile(r"[A-Z0-9]{3}")


class TabularError(ValueError):
    pass


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    first: str
    last: str


def load_chapters(path):
    """Return the chapters of a tabular XML file, in file order."""
    root = ET.parse(path).getroot()
    chapters = []
    for index, el in enumerate(root.findall("chapter"), start=1):
        name = (el.findtext("name") or "").strip()
        desc = (el.findtext("desc") or "").strip()
        if not name.isdigit():
            raise TabularError(f"chapter {index}: <name> is not a number")
        m = _RANGE.fullmatch(desc)
        if m is None:
            raise TabularError(f"chapter {name}: <desc> does not end with a "
                               "category range")
        title, first, last = m.groups()
        if first > last:
            raise TabularError(f"chapter {name}: range {first}-{last} is reversed")
        chapters.append(Chapter(int(name), title, first, last))
    if not chapters:
        raise TabularError("no <chapter> elements")
    return chapters


def chapter_of(category, chapters):
    """Number of the chapter whose range holds a 3-character category.

    None when no range holds it; TabularError when more than one does.
    """
    if not _CATEGORY.fullmatch(category):
        raise ValueError(f"not a 3-character category: {category!r}")
    hits = [c.number for c in chapters if c.first <= category <= c.last]
    if len(hits) > 1:
        raise TabularError(f"category {category} is in chapters {hits}")
    return hits[0] if hits else None


# ---------------------------------------------------------------------------
# The full tree: diags, instructional notes, 7th-character definitions.
#
# Structure, from icd10cm_tabular.xsd: the root holds <introduction>
# (<introSection>/<instruction>) and <chapter>s; a chapter holds <section>s,
# a section holds <diag>s and a diag holds <diag>s. Chapters, sections and
# diags may hold notes of these noteType elements, each a list of <note>
# children: inclusionTerm, sevenChrNote, includes, excludes1, excludes2,
# codeFirst, useAdditionalCode, codeAlso, notes. <instruction> (also
# noteType) occurs only in the introduction. <sevenChrDef> holds
# <extension char="x"> children (the 7th-character values) and may hold
# <note>s. A diag may carry placeholder="true". The XSD also defines
# addenda markup (diff, new, old, unc) and <deactivated>; note text is read
# with itertext() so markup inside a note does not lose text.
# ---------------------------------------------------------------------------

NOTE_KINDS = ("includes", "inclusionTerm", "excludes1", "excludes2", "codeFirst",
              "useAdditionalCode", "codeAlso", "notes", "sevenChrNote")
_NAME = re.compile(r"[A-Z0-9]{3}(?:\.[A-Z0-9]{1,4})?")
_EXT_CHAR = re.compile(r"[A-Za-z0-9]")


@dataclass(frozen=True)
class Note:
    kind: str          # element name: one of NOTE_KINDS, sevenChrDef or instruction
    text: str          # the <note> text, stripped
    owner_type: str    # chapter, section, diag or introduction
    owner: str         # chapter number, section id, diag code (no dot) or introSection type


@dataclass(frozen=True)
class Diag:
    code: str          # name without the dot
    name: str          # name as in the file
    desc: str
    parent: object     # parent diag code, or None under a section
    section: str
    chapter: int
    depth: int         # 1 for a diag directly under a section
    placeholder: bool
    seven_chr: object  # ((char, text), ...) from its own sevenChrDef, or None
    children: tuple


@dataclass(frozen=True)
class Tree:
    version: str
    diags: dict        # code -> Diag, in file order
    notes: tuple       # every Note, in file order
    sections: dict     # section id -> chapter number


def _text(el):
    return "".join(el.itertext()).strip()


def _notes_of(el, kind, owner_type, owner):
    return [Note(kind, _text(n), owner_type, owner) for n in el.findall("note")]


def _own_notes(el, owner_type, owner):
    out = []
    for child in el:
        if child.tag in NOTE_KINDS or child.tag == "sevenChrDef":
            out.extend(_notes_of(child, child.tag, owner_type, owner))
    return out


def load_tree(path):
    """Parse the whole tabular file into a Tree."""
    root = ET.parse(path).getroot()
    diags, notes, sections = {}, [], {}
    for intro in root.iter("introSection"):
        for ins in intro.findall("instruction"):
            notes.extend(_notes_of(ins, "instruction", "introduction",
                                   intro.get("type", "")))
    for ch in root.findall("chapter"):
        number = (ch.findtext("name") or "").strip()
        if not number.isdigit():
            raise TabularError("a <chapter> <name> is not a number")
        number = int(number)
        notes.extend(_own_notes(ch, "chapter", str(number)))
        for sec in ch.findall("section"):
            sid = sec.get("id")
            if not sid or sid in sections:
                raise TabularError(f"chapter {number}: section id {sid!r} missing or repeated")
            sections[sid] = number
            notes.extend(_own_notes(sec, "section", sid))
            for d in sec.findall("diag"):
                _walk(d, None, sid, number, 1, diags, notes)
    return Tree((root.findtext("version") or "").strip(), diags, tuple(notes), sections)


def _walk(el, parent, sid, chapter, depth, diags, notes):
    name = (el.findtext("name") or "").strip()
    if not _NAME.fullmatch(name):
        raise TabularError(f"diag name {name!r} is not a code")
    code = name.replace(".", "")
    if code in diags:
        raise TabularError(f"diag {name} occurs twice")
    if parent is not None and not code.startswith(parent):
        raise TabularError(f"diag {name} is not an extension of its parent")
    seven = None
    defs = el.findall("sevenChrDef")
    if len(defs) > 1:
        raise TabularError(f"diag {name} has more than one sevenChrDef")
    if defs:
        seven = []
        for ext in defs[0].findall("extension"):
            ch = (ext.get("char") or "").strip()
            if not _EXT_CHAR.fullmatch(ch):
                raise TabularError(f"diag {name}: 7th character {ch!r} is not one character")
            seven.append((ch, _text(ext)))
        seven = tuple(seven)
    kids = el.findall("diag")
    diags[code] = Diag(code, name, (el.findtext("desc") or "").strip(), parent, sid,
                       chapter, depth, el.get("placeholder") == "true", seven,
                       tuple(k.findtext("name").strip().replace(".", "") for k in kids))
    notes.extend(_own_notes(el, "diag", code))
    for k in kids:
        _walk(k, code, sid, chapter, depth + 1, diags, notes)


def element_census(path):
    """{element name: {"count", "parents": {parent name: n}, "attributes": {name: n}}}.

    The root's parents are empty.
    """
    root = ET.parse(path).getroot()
    out = {}

    def visit(el, parent):
        e = out.setdefault(el.tag, {"count": 0, "parents": {}, "attributes": {}})
        e["count"] += 1
        if parent is not None:
            e["parents"][parent] = e["parents"].get(parent, 0) + 1
        for a in el.attrib:
            e["attributes"][a] = e["attributes"].get(a, 0) + 1
        for child in el:
            visit(child, el.tag)

    visit(root, None)
    return out


def nearest_diag(code, tree):
    """The diag whose code is the longest prefix of code (itself included)."""
    for n in range(len(code), 2, -1):
        d = tree.diags.get(code[:n])
        if d is not None:
            return d
    return None


@dataclass(frozen=True)
class Scope:
    diags: tuple       # nearest diag first, then its ancestors
    section: object
    chapter: object


def scope_of(code, tree):
    """The diags, section and chapter whose notes are above a code."""
    d = nearest_diag(code, tree)
    if d is None:
        return Scope((), None, None)
    chain = []
    while d is not None:
        chain.append(d.code)
        d = tree.diags.get(d.parent) if d.parent else None
    first = tree.diags[chain[0]]
    return Scope(tuple(chain), first.section, first.chapter)


def seven_chr_source(code, tree):
    """The nearest diag at or above code that has a sevenChrDef, or None."""
    for c in scope_of(code, tree).diags:
        if tree.diags[c].seven_chr is not None:
            return tree.diags[c]
    return None


def diag_level(code, billable):
    """category (3 characters), code (billable) or subcategory (the rest)."""
    if len(code) == 3:
        return "category"
    return "code" if code in billable else "subcategory"


# ---------------------------------------------------------------------------
# Code references in note text.
#
# A reference is a code written with or without its dot, e.g. P35.0, J40,
# M1A.-, S01.12-, or a range of two such codes, e.g. T82.6-T82.7, O00-O9A.
# A code is a letter, then a digit or letter, then a digit or letter, with
# at least one of the second and third characters a digit, then optionally
# a dot and 1-4 letters or digits. A trailing "-" or ".-" marks a prefix.
# ---------------------------------------------------------------------------

_C = r"[A-Z](?:[0-9][0-9A-Z]|[A-Z][0-9])(?:\.[0-9A-Z]{1,4})?"
_REF = re.compile(rf"(?<![A-Za-z0-9.])({_C})(?:-({_C})|(\.?-))?(?![A-Za-z0-9])")


@dataclass(frozen=True)
class Reference:
    text: str          # as written
    first: str         # code without dot (prefix for a wildcard)
    last: object       # range end without dot, or None
    wildcard: bool     # written with a trailing "-" or ".-"


def _reference(m):
    a, b, w = m.groups()
    return Reference(m.group(0), a.replace(".", ""),
                     b.replace(".", "") if b else None, bool(w))


def find_references(text):
    """Code references in a note, in text order."""
    return [_reference(m) for m in _REF.finditer(text)]


def prefix_set(codes):
    """Every prefix of 3 or more characters of the given codes (no dots)."""
    return {c[:n] for c in codes for n in range(3, len(c) + 1)}


def reference_resolves(ref, prefixes):
    """True when every code in the reference is a stored code or a prefix
    of stored codes (prefixes from prefix_set)."""
    return ref.first in prefixes and (ref.last is None or ref.last in prefixes)


def classify_note(text, prefixes):
    """all, some or none_unresolved by how many references resolve;
    no_refs when the text holds no reference."""
    refs = find_references(text)
    if not refs:
        return "no_refs"
    ok = sum(reference_resolves(r, prefixes) for r in refs)
    return "all" if ok == len(refs) else "some" if ok else "none_unresolved"


def split_by_parentheses(text):
    """(inside, outside): the references of find_references that sit inside
    a pair of parentheses (at any depth), and the rest, each in text order.

    An unmatched ")" does not take the depth below zero."""
    depth_at, depth = [], 0
    for ch in text:
        depth_at.append(depth)
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
    inside, outside = [], []
    for m in _REF.finditer(text):
        (inside if depth_at[m.start()] > 0 else outside).append(_reference(m))
    return inside, outside


def reference_matches(ref, code):
    """True when a code (no dot) falls under a reference.

    A range holds the codes whose leading characters lie between its ends in
    ASCII order (the category order chapter_of uses), each end compared on
    its own length; a wildcard holds the codes that start with it; any other
    reference holds only the code written."""
    if ref.last is not None:
        return (code[:len(ref.first)] >= ref.first
                and code[:len(ref.last)] <= ref.last)
    if ref.wildcard:
        return code.startswith(ref.first)
    return code == ref.first
