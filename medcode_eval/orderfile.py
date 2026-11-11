"""Load the ICD-10-CM order file (icd10cm_order_<year>.txt).

Layout, fixed width, columns counted from 1:

    1-5    order number, zero-padded
    6      space
    7-13   code without a dot, left-aligned, space-padded
    14     space
    15     1 = valid for HIPAA-covered transactions (billable), 0 = header
    16     space
    17-76  short description, space-padded
    77     space
    78-    long description

Every row is checked against this layout; a row that does not fit raises
OrderFileError naming its line number. The file is read as ASCII.
"""

import re
from dataclasses import dataclass

_CODE = re.compile(r"[A-Z0-9]{3,7}")
_ORDER = re.compile(r"\d{5}")


class OrderFileError(ValueError):
    pass


@dataclass(frozen=True)
class OrderRecord:
    order: int
    code: str
    billable: bool
    short: str
    long: str


def parse_line(line):
    """Parse one row (a trailing CR/LF is ignored) into an OrderRecord."""
    line = line.rstrip("\r\n")

    def fail(why):
        raise OrderFileError(f"row does not fit the order-file layout: {why}")

    if len(line) < 78:
        fail(f"length {len(line)} is under 78")
    for col in (6, 14, 16, 77):
        if line[col - 1] != " ":
            fail(f"column {col} is not a space")
    order, code_field, flag = line[0:5], line[6:13], line[14]
    short_field, long_field = line[16:76], line[77:]
    if not _ORDER.fullmatch(order):
        fail("order number is not five digits")
    code = code_field.rstrip(" ")
    if not _CODE.fullmatch(code):
        fail("code is not 3-7 letters or digits")
    if flag not in "01":
        fail("billable flag is not 0 or 1")
    short = short_field.rstrip(" ")
    long = long_field.rstrip(" ")
    if not short or short[0] == " ":
        fail("short description is empty or starts with a space")
    if not long or long[0] == " ":
        fail("long description is empty or starts with a space")
    return OrderRecord(int(order), code, flag == "1", short, long)


def parse_lines(lines):
    """Parse an iterable of rows; errors name the 1-based line number."""
    records = []
    for number, line in enumerate(lines, start=1):
        try:
            records.append(parse_line(line))
        except OrderFileError as exc:
            raise OrderFileError(f"line {number}: {exc}") from None
    return records


def load(path):
    """Read an order file and return its records in file order."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise OrderFileError(f"byte {exc.start} is not ASCII") from None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return parse_lines(lines)


def parent_map(records):
    """Map each code to its parent, or None.

    The parent is the longest proper prefix of the code that is itself a
    code in the records.
    """
    codes = {r.code for r in records}
    parents = {}
    for r in records:
        parent = None
        for n in range(len(r.code) - 1, 0, -1):
            if r.code[:n] in codes:
                parent = r.code[:n]
                break
        parents[r.code] = parent
    return parents
