#!/usr/bin/env python3
"""Bounded card-reference extraction for merge-to-prod finalize.

Two jobs, both deliberately narrow:

1. extract_ticket_numbers(body): ticket numbers ONLY from bullet lines under
   the "### Tickets" heading INSIDE the managed section. Whole-body number
   extraction false-positives on GitHub PR numbers like (#541),
   parenthetical refs like "Card #644", and related-ticket refs like
   "(from #318)" — all of which wrongly close cards.
2. extract_pr_refs(text, context_repo): repository-qualified PR identities.
   A bare #NNN inherits the context repo; a cross-repository URL keeps its
   own repo and must NEVER be resolved as a local PR number.

Word boundaries are enforced: searching for card 12 never matches 312 or
#123. Standard library only.

Usage:
    gh pr view <N> --json body -q .body | python3 card_refs.py --stdin
    python3 card_refs.py --pr-refs --repo owner/slug --file body.md
"""

import argparse
import json
import re
import sys

from managed_section import extract_managed

# Bullet line anchored at the leading card ref: "- #123 ..." or "* #123 ...".
# (\D|$) after the digits rejects "#123" when looking for 12 and "312"
# never matches at all (no '#' prefix).
BULLET_TICKET_RE = re.compile(r"^\s*[-*]\s+#(\d+)(?:\D|$)")

# PR references: cross-repo URL, slug-qualified, or bare.
PR_URL_RE = re.compile(
    r"github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
    r"/pull/(?P<num>\d+)(?:\D|$)")
PR_QUALIFIED_RE = re.compile(
    r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<num>\d+)(?:\D|$)")
PR_BARE_RE = re.compile(r"(?<![A-Za-z0-9_./-])#(?P<num>\d+)(?:\D|$)")

REVERT_RE = re.compile(r'^\s*revert\b|"this reverts"', re.IGNORECASE)


def tickets_section(managed_body):
    """Return the text under the '### Tickets' heading (to the next '### ')."""
    lines = managed_body.splitlines()
    in_section = False
    collected = []
    for line in lines:
        if re.match(r"^###\s+Tickets\s*$", line):
            in_section = True
            continue
        if in_section and re.match(r"^###\s+", line):
            break
        if in_section:
            collected.append(line)
    return "\n".join(collected)


def extract_ticket_numbers(pr_body):
    """Bounded extraction: managed section -> Tickets heading -> bullets."""
    managed, _ = extract_managed(pr_body)
    scope = tickets_section(managed) if managed is not None else ""
    numbers = []
    for line in scope.splitlines():
        m = BULLET_TICKET_RE.match(line)
        if m:
            numbers.append(int(m.group(1)))
    # De-duplicate, preserve order.
    return list(dict.fromkeys(numbers))


def extract_pr_refs(text, context_repo=""):
    """Return [{repo, pr, qualified}] preserving first-seen order."""
    found = []
    seen = set()

    def add(repo, num, qualified):
        key = (repo, num)
        if key not in seen:
            seen.add(key)
            found.append({"repo": repo, "pr": num,
                          "qualified": qualified})

    # URLs first so their trailing bare "#NNN" cannot double-count.
    redacted = text
    for m in PR_URL_RE.finditer(text):
        repo = m.group("owner") + "/" + m.group("repo")
        add(repo, int(m.group("num")), True)
        redacted = redacted.replace(m.group(0), " ")
    for m in PR_QUALIFIED_RE.finditer(redacted):
        add(m.group("slug"), int(m.group("num")), True)
    for m in PR_BARE_RE.finditer(redacted):
        add(context_repo, int(m.group("num")), False)
    return found


def mentions_revert(text):
    """True when text contains a revert marker needing re-evidence."""
    return bool(REVERT_RE.search(text or ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin", action="store_true",
                        help="read PR body from stdin, print ticket numbers")
    parser.add_argument("--file", metavar="FILE",
                        help="read PR body from FILE, print ticket numbers")
    parser.add_argument("--pr-refs", action="store_true",
                        help="print repo-qualified PR identities as JSON")
    parser.add_argument("--repo", default="",
                        help="context repo slug for bare #NNN refs")
    args = parser.parse_args(argv)

    if args.stdin:
        body = sys.stdin.read()
    elif args.file:
        with open(args.file) as f:
            body = f.read()
    else:
        parser.print_help()
        return 2

    if args.pr_refs:
        print(json.dumps(extract_pr_refs(body, args.repo), indent=2))
    else:
        for n in extract_ticket_numbers(body):
            print(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
