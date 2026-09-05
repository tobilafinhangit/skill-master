#!/usr/bin/env python3
"""Managed-section extract/replace for merge-to-prod PR bodies.

The managed section is machine-owned; everything outside the markers belongs
to the operator and must survive every update. Bodies without markers are
LEGACY: callers must reconstruct and validate evidence, never blind-close
from number extraction. Bodies with markers but a divergent manifest are
SUSPECT: re-validate and rebuild.

Markers:
    <!-- merge-to-prod:managed:begin -->
    <!-- merge-to-prod:manifest version="2.0" -->
    <!-- merge-to-prod:managed:end -->

Usage:
    python3 managed_section.py --extract body.md
    python3 managed_section.py --replace body.md --with managed.md --out new.md
Standard library only.
"""

import argparse
import re
import sys

BEGIN = "<!-- merge-to-prod:managed:begin -->"
MANIFEST_MARK = '<!-- merge-to-prod:manifest version="2.0" -->'
END = "<!-- merge-to-prod:managed:end -->"


def extract_managed(body):
    """Return (managed_inner, outside) or (None, body) for legacy bodies."""
    if BEGIN not in body or END not in body:
        return None, body
    start = body.index(BEGIN) + len(BEGIN)
    end = body.index(END)
    if end < start:
        return None, body
    return body[start:end].strip(), body[:body.index(BEGIN)] + body[end + len(END):]


def has_markers(body):
    return BEGIN in body and END in body


def manifest_json_text(managed_inner):
    """Return the embedded manifest JSON text, or None."""
    m = re.search(r"```json\s*(.*?)```", managed_inner or "", re.DOTALL)
    return m.group(1).strip() if m else None


def replace_managed(body, new_inner):
    """Replace the managed section, preserving all operator content.

    Legacy bodies (no markers): the new section is appended and the whole
    original body is preserved verbatim above it.
    """
    block = "%s\n%s\n%s" % (BEGIN, new_inner.strip(), END)
    if not has_markers(body):
        if body.strip():
            return body.rstrip() + "\n\n" + block + "\n"
        return block + "\n"
    start = body.index(BEGIN)
    end = body.index(END) + len(END)
    return body[:start] + block + body[end:]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", metavar="FILE",
                        help="print the managed inner section (or LEGACY)")
    parser.add_argument("--replace", metavar="FILE",
                        help="PR body file to update")
    parser.add_argument("--with", dest="with_file", metavar="FILE",
                        help="file holding the new managed inner content")
    parser.add_argument("--out", metavar="FILE",
                        help="write result here (default: stdout)")
    args = parser.parse_args(argv)

    if args.extract:
        with open(args.extract) as f:
            body = f.read()
        managed, _ = extract_managed(body)
        if managed is None:
            print("LEGACY — no managed section; reconstruct evidence, "
                  "never close from number extraction alone.")
            return 1
        print(managed)
        return 0

    if args.replace:
        if not args.with_file:
            print("--replace requires --with FILE", file=sys.stderr)
            return 2
        with open(args.replace) as f:
            body = f.read()
        with open(args.with_file) as f:
            new_inner = f.read()
        result = replace_managed(body, new_inner)
        if args.out:
            with open(args.out, "w") as f:
                f.write(result)
        else:
            print(result, end="")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
