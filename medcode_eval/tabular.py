"""Chapters of the ICD-10-CM tabular list (icd10cm_tabular_<year>.xml).

How the file expresses chapters (per icd10cm_tabular.xsd and the file):
the root element ICD10CM.tabular has <chapter> children. Each chapter has
a <name> (the chapter number) and a <desc> whose text ends with the
chapter's category range in parentheses, e.g.
"Certain infectious and parasitic diseases (A00-B99)". The chapter element
has no range attribute; its <sectionIndex>/<sectionRef first= last=> and
<section id=> elements give the ranges of its blocks, not of the chapter.

Only what is needed here is read: the number, title and category range of
each chapter. Categories compare as ASCII strings, which puts digits before
letters (O99 < O9A, Q99 < QA0), the same order the ranges use.
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
