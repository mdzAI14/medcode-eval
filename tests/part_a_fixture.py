"""Invented code set shared by the Part A tests.

Every code starts U9 and is made up; descriptions are invented. Two
chapters: 1 = U90-U94, 2 = U95-U99. No network.
"""

from pathlib import Path

from tests.test_addenda import arow
from tests.test_orderfile import row

# (code, billable, long description)
CODES = [
    ("U90", 0, "Invented alpha"),
    ("U900", 1, "Invented alpha one"),
    ("U901", 1, "Invented alpha two"),
    ("U902", 1, "Invented alpha three"),
    ("U903", 1, "Invented alpha four"),
    ("U91", 0, "Invented beta"),
    ("U910", 1, "Invented beta one"),
    ("U911", 1, "Invented beta two"),
    ("U92", 1, "Invented gamma"),
    ("U93", 0, "Invented delta"),
    ("U931", 0, "Invented delta one"),
    ("U9311", 1, "Invented delta one, first"),
    ("U9312", 1, "Invented shared text"),
    ("U934", 0, "Invented delta four"),
    ("U934XXA", 1, "Invented delta four, initial encounter"),
    ("U934XXD", 1, "Invented delta four, subsequent encounter"),
    ("U95", 0, "Invented epsilon"),
    ("U950", 1, "Invented epsilon zero"),
    ("U951", 1, "Invented epsilon one"),
    ("U952", 1, "Invented zeta"),  # same text as header U96
    ("U96", 0, "Invented zeta"),
    ("U961", 0, "Invented zeta one"),
    ("U961XXA", 1, "Invented zeta one, initial encounter"),
    ("U97", 0, "Invented eta"),
    ("U970", 1, "Invented eta zero"),
    ("U971", 1, "Invented shared text"),
]

ORDER_LINES = [row(i, code, flag, long[:60], long)
               for i, (code, flag, long) in enumerate(CODES, start=1)]

# changes: U911, U970, U971 added billable; U961 added header; U934
# billable to header; U958 removed
ADDENDA_LINES = [
    arow("Add:", 1, "U911", "Invented beta two", "Invented beta two"),
    arow("Delete:", 1, "U934", "Invented delta four", "Invented delta four"),
    arow("Add:", 0, "U934", "Invented delta four", "Invented delta four"),
    arow("Delete:", 1, "U958", "Invented removed", "Invented removed"),
    arow("Add:", 0, "U961", "Invented zeta one", "Invented zeta one"),
    arow("Add:", 1, "U970", "Invented eta zero", "Invented eta zero"),
    arow("Add:", 1, "U971", "Invented shared text", "Invented shared text"),
    "",
    "Headers",
    "      2 additions",
    "      0 deletions",
    "Codes",
    "      3 additions",
    "      2 deletions",
]

ADDED = {"U911", "U934", "U961", "U970", "U971"}

TABULAR_XML = """<?xml version="1.0" encoding="utf-8"?>
<ICD10CM.tabular>
  <version>2099</version>
  <chapter><name>1</name><desc>Invented chapter one (U90-U94)</desc></chapter>
  <chapter><name>2</name><desc>Invented chapter two (U95-U99)</desc></chapter>
</ICD10CM.tabular>
"""

# sizes that the fixture can fill
FULL = {"code_to_description": 6, "description_to_code": 6, "status": 18}
LITE = {"code_to_description": 3, "description_to_code": 3, "status": 9}


def write_inputs(directory):
    """Write the three fixture refdata files; return their paths."""
    d = Path(directory)
    order = d / "order.txt"
    order.write_bytes("".join(l + "\r\n" for l in ORDER_LINES).encode("ascii"))
    addenda = d / "addenda.txt"
    addenda.write_bytes("".join(l + "\r\n" for l in ADDENDA_LINES).encode("ascii"))
    tab = d / "tabular.xml"
    tab.write_text(TABULAR_XML, encoding="utf-8")
    return {"order": order, "addenda": addenda, "tabular": tab}
