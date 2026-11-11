"""Load the ICD-10-CM order addenda file (icd10cm_order_addenda_<year>.txt).

The file lists the changes from the previous year's order file. It has two
parts, record lines and then a summary.

Record lines, fixed width, columns counted from 1:

    1-13   action, left-aligned, space-padded: "Add:", "Delete:",
           "Revise from:" or "Revise to:"
    14     1 = billable code, 0 = header
    15     space
    16-22  code without a dot, left-aligned, space-padded
    23     space
    24-83  short description, space-padded
    84     space
    85-    long description

A "Revise from:" line is followed at once by a "Revise to:" line for the
same code. A "Delete:" line removes one (code, flag) row; when the same
code also has an "Add:" line the code was kept with a new flag (a billable
code that became a header), so it was not removed from the code set.

The summary starts at the first blank line. It has a "Headers" and a
"Codes" section, each made of count lines ("<n> <label>") and an
"of which" line. Any other line raises AddendaError naming its line number.
The file is read as ASCII.
"""

import re
from dataclasses import dataclass, field

_ACTIONS = {
    "Add:": "add",
    "Delete:": "delete",
    "Revise from:": "revise_from",
    "Revise to:": "revise_to",
}
_CODE = re.compile(r"[A-Z0-9]{3,7}")
_COUNT = re.compile(r" *(\d+) (\S.*)")
_SECTIONS = ("Headers", "Codes")


class AddendaError(ValueError):
    pass


@dataclass(frozen=True)
class AddendaRecord:
    action: str
    billable: bool
    code: str
    short: str
    long: str


@dataclass
class Addenda:
    records: list
    # (section, label) -> count, e.g. ("Codes", "deletions") -> 30
    summary: dict = field(default_factory=dict)

    def check_summary(self):
        """Compare the summary counts with the record lines.

        Returns a list of mismatch messages (empty when they agree). The
        counts of rows in the two order files are not checked here: they
        need the order files themselves.
        """
        problems = []
        for section, billable in (("Headers", False), ("Codes", True)):
            recs = [r for r in self.records if r.billable == billable]
            froms = [r for r in recs if r.action == "revise_from"]
            tos = {r.code: r for r in recs if r.action == "revise_to"}
            both = long_only = short_only = 0
            for old in froms:
                new = tos[old.code]
                s, l = old.short != new.short, old.long != new.long
                both += s and l
                long_only += l and not s
                short_only += s and not l
            expected = {
                "additions": sum(r.action == "add" for r in recs),
                "deletions": sum(r.action == "delete" for r in recs),
                "revisions": len(froms),
                "revisions to both long and short titles": both,
                "revisions to long title only": long_only,
                "revisions to short title only": short_only,
            }
            for label, want in expected.items():
                got = self.summary.get((section, label))
                if got != want:
                    problems.append(
                        f"{section} {label}: summary says {got}, records give {want}")
        return problems


def parse_line(line):
    """Parse one record line (a trailing CR/LF is ignored)."""
    line = line.rstrip("\r\n")

    def fail(why):
        raise AddendaError(f"row does not fit the addenda layout: {why}")

    if len(line) < 85:
        fail(f"length {len(line)} is under 85")
    action_field = line[0:13].rstrip(" ")
    if action_field not in _ACTIONS:
        fail("unknown action")
    for col in (15, 23, 84):
        if line[col - 1] != " ":
            fail(f"column {col} is not a space")
    flag = line[13]
    if flag not in "01":
        fail("billable flag is not 0 or 1")
    code = line[15:22].rstrip(" ")
    if not _CODE.fullmatch(code):
        fail("code is not 3-7 letters or digits")
    short = line[23:83].rstrip(" ")
    long = line[84:].rstrip(" ")
    if not short or short[0] == " ":
        fail("short description is empty or starts with a space")
    if not long or long[0] == " ":
        fail("long description is empty or starts with a space")
    return AddendaRecord(_ACTIONS[action_field], flag == "1", code, short, long)


def parse_text(lines):
    """Parse all lines of the file; errors name the 1-based line number."""
    records, summary = [], {}
    in_summary, section = False, None
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        try:
            if not in_summary:
                if line == "":
                    in_summary = True
                    continue
                rec = parse_line(line)
                if records and records[-1].action == "revise_from":
                    prev = records[-1]
                    if rec.action != "revise_to" or rec.code != prev.code:
                        raise AddendaError("'Revise from:' not followed by "
                                           "'Revise to:' for the same code")
                elif rec.action == "revise_to":
                    raise AddendaError("'Revise to:' without 'Revise from:'")
                records.append(rec)
                continue
            if line == "" or line == "of which":
                continue
            if line in _SECTIONS:
                section = line
                continue
            m = _COUNT.fullmatch(line)
            if m is None or section is None:
                raise AddendaError("summary line not understood")
            key = (section, m.group(2))
            if key in summary:
                raise AddendaError("summary label repeated")
            summary[key] = int(m.group(1))
        except AddendaError as exc:
            raise AddendaError(f"line {number}: {exc}") from None
    if records and records[-1].action == "revise_from":
        raise AddendaError("file ends after 'Revise from:'")
    return Addenda(records, summary)


def load(path):
    """Read an order addenda file."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AddendaError(f"byte {exc.start} is not ASCII") from None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return parse_text(lines)


def removed_codes(records):
    """Codes with a "Delete:" line and no "Add:" line, in file order."""
    added = {r.code for r in records if r.action == "add"}
    out = []
    for r in records:
        if r.action == "delete" and r.code not in added and r.code not in out:
            out.append(r.code)
    return out
