#!/usr/bin/env python3
"""Validate (and scaffold) an mtp-manifest/2.0 release manifest.

The manifest records readiness evidence for one merge-to-prod run. It is a
record, not proof: every consumer re-validates the manifest AND the live
state it points to. A manifest copied from another run, hand-edited, or
pointing at moved pins is rejected and the evidence is rebuilt.

G1 fail-closed: the manifest must carry the recorded prospective-merge
result (merge_check) against the same pinned SHAs. A missing, malformed,
stale, or non-clean G1 record rejects the manifest, which blocks PR
publication (G5) and finalize.

Usage:
    python3 manifest.py --validate manifest.json
    python3 manifest.py --scaffold --repo owner/slug --base <sha> --head <sha> > manifest.json

Exit codes: 0 valid (or scaffold written), 1 invalid with errors on stdout,
2 usage error. Standard library only.
"""

import argparse
import json
import re
import sys

SCHEMA = "mtp-manifest/2.0"
CARD_STATES = ("covered", "already_on_target", "not_ready", "unknown",
               "non_code_complete")
MIGRATION_STATES = ("verified_applied", "missing", "partial_or_drifted",
                    "unknown", "not_applicable")
VERDICTS = ("ready", "blocked", "incomplete")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Substrings that indicate an external mutation. Used by --check-dry-run to
# prove a dry-run plan executed nothing. Keep narrow: read-only git/gh/fizzy
# GET commands must NOT match.
MUTATION_PATTERNS = (
    "gh pr create", "gh pr edit", "gh pr merge",
    "curl -X POST", "curl --request POST", "-X POST",
    "git push", "git worktree remove",
    "supabase db push",
    "/closure.json", "/triage.json", "/comments.json",
)


def scaffold(repo, base, head, mode="prepare"):
    return {
        "manifest_version": SCHEMA,
        "repository": {
            "remote_url": "",
            "resolved_slug": repo,
            "integration_branch": "",
            "target_branch": "",
        },
        "revisions": {"base_sha": base, "head_sha": head,
                      "fetched_at": ""},
        "merge_check": {"base_sha": "", "head_sha": "", "worktree": "",
                        "merge_exit": None, "status": "", "checked_at": ""},
        "verdict": "incomplete",
        "cards": [],
        "changes": [],
        "migrations": [],
        "blockers": ["scaffold — evidence not yet collected"],
        "mode": mode,
        "generated_at": "",
    }


def _err(errors, msg):
    errors.append(msg)


def validate(manifest):
    """Return a list of error strings; empty means valid."""
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    if manifest.get("manifest_version") != SCHEMA:
        _err(errors, "manifest_version must be %r" % SCHEMA)

    repo = manifest.get("repository", {})
    if not repo.get("resolved_slug"):
        _err(errors, "repository.resolved_slug is required "
                      "(remote identity, not directory name)")

    revs = manifest.get("revisions", {})
    for key in ("base_sha", "head_sha"):
        sha = revs.get(key, "")
        if not (isinstance(sha, str) and SHA_RE.match(sha)):
            _err(errors, "revisions.%s must be a full 40-hex SHA" % key)
    if revs.get("base_sha") == revs.get("head_sha"):
        _err(errors, "base_sha and head_sha must differ (empty range)")

    # G1 fail-closed: the recorded prospective-merge result. Missing,
    # malformed, stale, or non-clean records reject the manifest, which
    # blocks publication (G5) and finalize. There is no bypass: reconcile
    # first, then record a fresh check.
    check = manifest.get("merge_check")
    if not isinstance(check, dict):
        _err(errors, "merge_check (G1 prospective-merge record) is required: "
                      "pinned main SHA, pinned staging SHA, worktree/check id, "
                      "merge command result, explicit clean/conflict status")
    else:
        for key in ("base_sha", "head_sha"):
            sha = check.get(key)
            if not (isinstance(sha, str) and SHA_RE.match(sha)):
                _err(errors, "merge_check.%s must be a full 40-hex SHA" % key)
            elif sha != revs.get(key):
                _err(errors, "merge_check.%s does not match revisions.%s "
                             "(stale G1 record — re-run the check)" % (key, key))
        if not (isinstance(check.get("worktree"), str)
                and check.get("worktree").strip()):
            _err(errors, "merge_check.worktree must name the temporary "
                         "worktree/check the merge ran in")
        exit_code = check.get("merge_exit")
        if not (isinstance(exit_code, int)
                and not isinstance(exit_code, bool)):
            _err(errors, "merge_check.merge_exit must be the integer exit "
                         "code of the merge command")
        status = check.get("status")
        if status not in ("clean", "conflict"):
            _err(errors, "merge_check.status must be 'clean' or 'conflict' "
                         "(explicit — never inferred)")
        elif (exit_code == 0) != (status == "clean"):
            _err(errors, "merge_check.status %r contradicts merge_exit %r"
                 % (status, exit_code))
        elif status != "clean":
            _err(errors, "merge_check.status is 'conflict' — reconcile main "
                         "into staging and record a fresh clean check; "
                         "a conflicted G1 record rejects the manifest")

    verdict = manifest.get("verdict")
    if verdict not in VERDICTS:
        _err(errors, "verdict must be one of %s" % (list(VERDICTS),))

    cards = manifest.get("cards", [])
    if not isinstance(cards, list):
        _err(errors, "cards must be a list")
        cards = []
    seen_numbers = set()
    for i, card in enumerate(cards):
        where = "cards[%d]" % i
        num = card.get("number")
        if not (isinstance(num, int) and num > 0):
            _err(errors, "%s.number must be a positive int" % where)
        if num in seen_numbers:
            _err(errors, "%s.number %r is duplicated" % (where, num))
        seen_numbers.add(num)
        state = card.get("state")
        if state not in CARD_STATES:
            _err(errors, "%s.state must be one of %s"
                 % (where, list(CARD_STATES)))
            continue
        deliverables = card.get("deliverables", [])
        if state in ("covered", "already_on_target"):
            if not deliverables:
                _err(errors, "%s: state %r requires at least one "
                             "deliverable with a merge SHA" % (where, state))
            for d in deliverables:
                sha = d.get("sha")
                if sha is not None and not (
                        isinstance(sha, str) and SHA_RE.match(sha)):
                    _err(errors, "%s: deliverable sha must be a full "
                                 "40-hex SHA or null" % where)
            if not any(isinstance(d.get("sha"), str)
                       and SHA_RE.match(d.get("sha")) for d in deliverables):
                _err(errors, "%s: state %r requires at least one "
                             "deliverable carrying a merge SHA "
                             "(ancestry proof)" % (where, state))
        if state == "non_code_complete":
            if any(isinstance(d.get("sha"), str) for d in deliverables):
                _err(errors, "%s: non_code_complete must not carry a "
                             "commit SHA (nothing is 'in main')" % where)
            if not card.get("completion_evidence"):
                _err(errors, "%s: non_code_complete requires "
                             "completion_evidence" % where)

    changes = manifest.get("changes", [])
    if not isinstance(changes, list):
        _err(errors, "changes must be a list")
        changes = []
    for i, ch in enumerate(changes):
        where = "changes[%d]" % i
        if not ch.get("path"):
            _err(errors, "%s.path is required" % where)
        if ch.get("unreviewed"):
            continue
        if not ch.get("evidence"):
            _err(errors, "%s: needs evidence or unreviewed:true "
                         "(never auto-label unmatched work)" % where)

    migrations = manifest.get("migrations", [])
    for i, mig in enumerate(migrations):
        where = "migrations[%d]" % i
        state = mig.get("state")
        if state not in MIGRATION_STATES:
            _err(errors, "%s.state must be one of %s"
                 % (where, list(MIGRATION_STATES)))

    # Verdict consistency: ready is only for fully accounted-for runs.
    if verdict == "ready":
        bad_cards = [c.get("number") for c in cards
                     if c.get("state") in ("unknown", "not_ready")]
        if bad_cards:
            _err(errors, "verdict ready with cards in unknown/not_ready: %r"
                 % bad_cards)
        unrev = [c.get("path") for c in changes if c.get("unreviewed")]
        if unrev:
            _err(errors, "verdict ready with unreviewed changes: %r" % unrev)
        bad_mig = [m.get("file") for m in migrations
                   if m.get("state") in ("partial_or_drifted", "unknown")]
        if bad_mig:
            _err(errors, "verdict ready with migrations in "
                         "partial_or_drifted/unknown: %r" % bad_mig)
        if manifest.get("blockers"):
            _err(errors, "verdict ready with non-empty blockers: %r"
                 % manifest.get("blockers"))
    return errors


def pins_match(manifest, base_sha, head_sha):
    """True when the live pins equal the manifest's recorded pins.

    A changed release head (or base) after audit invalidates the evidence:
    callers must refresh affected items, not publish from stale pins.
    """
    revs = manifest.get("revisions", {})
    return (revs.get("base_sha") == base_sha
            and revs.get("head_sha") == head_sha)


def find_mutations(commands):
    """Return the subset of planned commands that would mutate externals.

    Used to enforce globally-read-only dry runs. Matching is substring and
    deliberately narrow (see MUTATION_PATTERNS).
    """
    hits = []
    for cmd in commands:
        lowered = cmd.lower()
        if any(p.lower() in lowered for p in MUTATION_PATTERNS):
            hits.append(cmd)
    return hits


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", metavar="FILE",
                        help="validate a manifest JSON file")
    parser.add_argument("--scaffold", action="store_true",
                        help="print a scaffold manifest")
    parser.add_argument("--repo", default="",
                        help="resolved repo slug for --scaffold")
    parser.add_argument("--base", default="0" * 40,
                        help="pinned base SHA for --scaffold")
    parser.add_argument("--head", default="1" * 40,
                        help="pinned head SHA for --scaffold")
    parser.add_argument("--check-dry-run", nargs="*", default=None,
                        metavar="CMD",
                        help="fail if any CMD looks like an external "
                             "mutation (dry-run must be read-only)")
    args = parser.parse_args(argv)

    if args.check_dry_run is not None:
        hits = find_mutations(args.check_dry_run)
        if hits:
            print("dry-run violation — external mutations planned:")
            for h in hits:
                print("  " + h)
            return 1
        print("dry-run clean — no external mutations")
        return 0

    if args.scaffold:
        if not args.repo:
            print("--scaffold requires --repo owner/slug", file=sys.stderr)
            return 2
        print(json.dumps(scaffold(args.repo, args.base, args.head),
                         indent=2))
        return 0

    if args.validate:
        try:
            with open(args.validate) as f:
                manifest = json.load(f)
        except (OSError, ValueError) as e:
            print("cannot load manifest: %s" % e, file=sys.stderr)
            return 2
        errors = validate(manifest)
        if errors:
            print("INVALID manifest (%d error(s)):" % len(errors))
            for e in errors:
                print("  - " + e)
            return 1
        print("VALID manifest (%s)" % SCHEMA)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
