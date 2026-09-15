"""Safety-oriented primitives shared by PR review and QA handoff.

This module deliberately stops at evidence collection and validation. It does not
merge, deploy, apply migrations, or turn untrusted ticket text into commands.
All functions are usable with injected fakes so the mechanics can be tested
without credentials, network access, or an application checkout.
"""

from __future__ import annotations

import html
import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EvidenceError(RuntimeError):
    """Raised when evidence is missing, malformed, stale, or unsafe to use."""


def _checked_payload(payload: Any, status: int, url: str) -> Mapping[str, Any]:
    if status < 200 or status >= 300:
        raise EvidenceError(f"HTTP {status} from {url}")
    if not isinstance(payload, Mapping):
        raise EvidenceError(f"Malformed JSON object from {url}")
    return payload


def collect_paginated(
    first_url: str,
    get: Callable[[str], tuple[Any, int]],
    *,
    item_key: str = "items",
    max_pages: int = 100,
) -> list[Mapping[str, Any]]:
    """Collect a complete linked collection, failing closed on bad pages."""
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    results: list[Mapping[str, Any]] = []
    url: str | None = first_url
    for _ in range(max_pages):
        if url is None:
            return results
        response = get(url)
        if not isinstance(response, tuple) or len(response) not in (2, 3):
            raise EvidenceError(f"Malformed response from {url}")
        payload, status = response[:2]
        headers = response[2] if len(response) == 3 else {}
        if not isinstance(headers, Mapping):
            raise EvidenceError(f"Malformed response headers from {url}")
        if status < 200 or status >= 300:
            raise EvidenceError(f"HTTP {status} from {url}")
        if isinstance(payload, list):
            items = payload
            next_url = _next_link(headers.get("Link"))
            total = headers.get("X-Total-Count")
            if total is None:
                raise EvidenceError(f"Missing X-Total-Count from {url}")
            try:
                expected_total = int(total)
            except (TypeError, ValueError) as exc:
                raise EvidenceError(f"Malformed X-Total-Count from {url}") from exc
        else:
            body = _checked_payload(payload, status, url)
            items = body.get(item_key)
            next_url = body.get("next")
            expected_total = None
        if not isinstance(items, list) or not all(isinstance(item, Mapping) for item in items):
            raise EvidenceError(f"Malformed {item_key} collection from {url}")
        results.extend(items)
        if next_url is not None and not isinstance(next_url, str):
            raise EvidenceError(f"Malformed pagination link from {url}")
        if expected_total is not None and next_url is None and len(results) != expected_total:
            raise EvidenceError(f"Fetched {len(results)} items but Fizzy reported {expected_total} from {url}")
        url = next_url
    raise EvidenceError(f"Pagination exceeded {max_pages} pages")


def _next_link(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EvidenceError("Malformed Link header")
    match = re.search(r"<([^>]+)>\s*;\s*rel=\"next\"", value, re.I)
    return match.group(1) if match else None


def fetch_json(url: str, *, headers: Mapping[str, str] | None = None, retries: int = 2) -> Any:
    """Fetch JSON with bounded retries; credentials must be supplied as headers."""
    if retries < 0:
        raise ValueError("retries cannot be negative")
    request = Request(url, headers=dict(headers or {"Accept": "application/json"}))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read()
            if status < 200 or status >= 300:
                raise EvidenceError(f"HTTP {status} from {url}")
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise EvidenceError(f"Malformed JSON from {url}") from exc
        except (HTTPError, URLError, TimeoutError, EvidenceError) as exc:
            last_error = exc
            if isinstance(exc, EvidenceError) and not str(exc).startswith("HTTP 5"):
                raise
            if attempt < retries:
                time.sleep(0.1 * (attempt + 1))
    raise EvidenceError(f"Unable to fetch {url}: {last_error}") from last_error


def resolve_direct_push_context(
    commit: str,
    previous_commit: str | None,
    integration_branch: str,
    contains_commit: bool,
) -> dict[str, str]:
    if not commit or not previous_commit:
        raise EvidenceError("Direct-push handoff requires a known commit range")
    if not integration_branch or not contains_commit:
        raise EvidenceError("Direct-push commit is not verified on integration")
    return {"commit": commit, "integration_branch": integration_branch, "range": f"{previous_commit}..{commit}"}


def ensure_fresh_revision(expected_sha: str, observed_sha: str) -> None:
    if not expected_sha or expected_sha != observed_sha:
        raise EvidenceError(f"Revision changed: expected {expected_sha!r}, observed {observed_sha!r}")


def classify_qa_findings(
    events: Iterable[Mapping[str, Any]], *, response_dispositions: Mapping[str, tuple[str, str]]
) -> list[dict[str, Any]]:
    """Normalize failure history without treating unrelated comments as replies."""
    output: list[dict[str, Any]] = []
    for event in events:
        if event.get("kind") != "failure":
            continue
        event_id = str(event.get("id", ""))
        if not event_id:
            raise EvidenceError("QA failure is missing an identity")
        response = response_dispositions.get(event_id)
        if response is None:
            response_id, disposition = None, "unresolved"
        else:
            if not isinstance(response, tuple) or len(response) != 2:
                raise EvidenceError(f"Malformed response for QA failure {event_id}")
            response_id, disposition = response
            if disposition not in {"established-expectation-correct", "accepted-deferral", "fixed", "unresolved"}:
                raise EvidenceError(f"Unsupported QA disposition for {event_id}: {disposition}")
        output.append({"failure_id": event_id, "body": event.get("body", ""), "response_id": response_id, "disposition": disposition})
    return output


def build_evidence_record(
    *, repository: str, pr_number: int | None = None, head_sha: str, base_sha: str | None = None,
    card_ids: Sequence[str] = (), environment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not repository or not head_sha:
        raise EvidenceError("Repository identity and head revision are required")
    return {
        "schema_version": 2,
        "repository": repository,
        "pr_number": pr_number,
        "card_ids": list(card_ids),
        "revisions": {"head": head_sha, "base": base_sha},
        "head_sha": head_sha,
        "base_sha": base_sha,
        "requirements": [],
        "findings": [],
        "coverage": {},
        "verification": {},
        "runtime_contracts": [],
        "environment": dict(environment or {}),
        "completed_actions": [],
        "blockers": [],
    }


def require_complete_evidence(record: Mapping[str, Any], *, required: Sequence[str] = (
    "repository", "head_sha", "environment", "requirements", "findings", "coverage", "verification"
)) -> None:
    missing = [key for key in required if key not in record or record[key] in (None, "", [], {})]
    if missing:
        raise EvidenceError("Missing evidence: " + ", ".join(missing))
    if not isinstance(record.get("environment", {}), Mapping):
        raise EvidenceError("Environment evidence must be an object")


def validate_runtime_contract(
    expected: Mapping[str, Any], observed: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless a deployed runtime contract matches its consumer.

    This is deliberately a pure evidence validator. Network calls, catalog reads,
    and authenticated smoke tests happen outside this module; their recorded
    results are validated here so a migration row or service-role query cannot be
    mistaken for a working browser contract.
    """
    if expected.get("kind") != "supabase-rpc" or not expected.get("name"):
        raise EvidenceError("Runtime contract requires a Supabase RPC kind and name")
    expected_args = expected.get("arguments")
    observed_args = observed.get("catalog_signature")
    if not isinstance(expected_args, list) or not isinstance(observed_args, list):
        raise EvidenceError("Runtime contract requires expected and observed argument lists")

    def normalize(arguments: list[Any]) -> list[tuple[str, str]]:
        normalized: list[tuple[str, str]] = []
        for argument in arguments:
            if not isinstance(argument, Mapping) or not argument.get("name") or not argument.get("type"):
                raise EvidenceError("Runtime contract contains a malformed argument")
            normalized.append((str(argument["name"]), str(argument["type"])))
        return normalized

    expected_signature = normalize(expected_args)
    observed_signature = normalize(observed_args)
    if expected_signature != observed_signature:
        raise EvidenceError(
            f"Runtime contract mismatch for {expected['name']}: "
            f"expected {expected_signature!r}, observed {observed_signature!r}"
        )
    if not observed.get("target_ref") or not observed.get("deployed_revision"):
        raise EvidenceError("Runtime contract requires target ref and deployed revision")
    if expected.get("target_ref") and expected["target_ref"] != observed["target_ref"]:
        raise EvidenceError("Runtime contract target ref does not match the expected target")
    if expected.get("deployed_revision") and expected["deployed_revision"] != observed["deployed_revision"]:
        raise EvidenceError("Runtime contract deployed revision does not match the expected revision")

    smoke = observed.get("smoke")
    if not isinstance(smoke, Mapping) or smoke.get("role") != "authenticated" or smoke.get("status") not in {200, 204}:
        raise EvidenceError("Runtime contract requires a successful authenticated smoke test")

    return {
        "status": "passed",
        "kind": expected["kind"],
        "name": expected["name"],
        "target_ref": observed["target_ref"],
        "deployed_revision": observed["deployed_revision"],
        "signature": [{"name": name, "type": type_name} for name, type_name in observed_signature],
        "smoke_role": smoke["role"],
    }


def validate_local_ci_fallback(
    *,
    expected_head_sha: str,
    github: Mapping[str, Any],
    local: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate advisory local-CI evidence without treating it as authoritative CI."""
    if not expected_head_sha or local.get("commit_sha") != expected_head_sha:
        raise EvidenceError("Local CI fallback commit does not match the reviewed head")
    if local.get("clean_tree") is not True:
        raise EvidenceError("Local CI fallback requires a clean tree")
    timeout = local.get("timeout_minutes")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise EvidenceError("Local CI fallback requires a positive timeout")
    if not local.get("node_version") or not local.get("install_mode"):
        raise EvidenceError("Local CI fallback requires runtime and install evidence")
    commands = local.get("commands")
    if not isinstance(commands, list) or not commands:
        raise EvidenceError("Local CI fallback requires command results")
    if any(
        not isinstance(command, Mapping)
        or not command.get("command")
        or command.get("status") != "passed"
        for command in commands
    ):
        raise EvidenceError("Local CI fallback requires every listed command to pass")
    if github.get("status") not in {"queued", "in_progress", "pending"}:
        raise EvidenceError("Local CI fallback requires an explicitly pending GitHub check")
    if not github.get("run_id") or not github.get("observed_at"):
        raise EvidenceError("Local CI fallback requires GitHub check identity and observation time")
    if local.get("substitutes_for"):
        raise EvidenceError("Local CI fallback cannot substitute for deployment, migration, security, or environment checks")
    return {
        "state": "local-pass/github-pending",
        "authority": "github",
        "github": dict(github),
        "local_fallback": dict(local),
        "reconciliation": {"status": "pending"},
    }


def reconcile_ci_result(
    evidence: Mapping[str, Any], *, head_sha: str, github_status: str
) -> dict[str, Any]:
    """Attach the later GitHub result to a previously recorded local fallback."""
    if evidence.get("state") != "local-pass/github-pending":
        raise EvidenceError("Only a pending local fallback can be reconciled")
    if evidence.get("local_fallback", {}).get("commit_sha") != head_sha:
        raise EvidenceError("Reconciliation head does not match the local fallback")
    if github_status not in {"success", "failure", "cancelled", "skipped"}:
        raise EvidenceError("GitHub result is not terminal")
    result = dict(evidence)
    result["state"] = "github-reconciled"
    result["reconciliation"] = {"status": github_status, "head_sha": head_sha}
    return result


def inspect_git_manifest(name_status: str, cherry_output: str = "") -> dict[str, list[str]]:
    manifest: dict[str, list[str]] = {"added": [], "modified": [], "deleted": [], "renamed": [], "other": [], "history_drift": []}
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            if line.strip():
                manifest["other"].append(line)
            continue
        status, path = parts[0], parts[-1]
        bucket = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(status[0], "other")
        manifest[bucket].append(path)
    for line in cherry_output.splitlines():
        if line.startswith("+"):
            manifest["history_drift"].append(line[1:].strip())
    return manifest


def html_escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def serialize_html_comment(title: str, sections: Mapping[str, Iterable[str]]) -> str:
    chunks = [f"<h2>{html_escape(title)}</h2>"]
    for heading, values in sections.items():
        chunks.append(f"<h3>{html_escape(heading)}</h3><ul>")
        chunks.extend(f"<li>{html_escape(value)}</li>" for value in values)
        chunks.append("</ul>")
    return "\n".join(chunks)


def require_dry_run_read_only(commands: Iterable[str], *, dry_run: bool) -> None:
    if not dry_run:
        return
    mutating = re.compile(
        r"(?:\bgit\b.*\b(push|merge|commit|reset|restore|checkout)\b|"
        r"\bgh\s+pr\s+(merge|edit|comment)\b|"
        r"\bcurl\b.*(?:-X|--request)\s*(?:POST|PUT|PATCH|DELETE)\b|"
        r"\bsupabase\s+(?:db\s+push|functions\s+deploy)\b)", re.I,
    )
    unsafe = [command for command in commands if mutating.search(command)]
    if unsafe:
        raise EvidenceError("Dry-run contains remote or repository mutation: " + unsafe[0])


@dataclass(frozen=True)
class CardState:
    card_id: str
    column: str
    assignee: str | None


def run_git(args: Sequence[str], *, cwd: str) -> str:
    """Run fixed, caller-supplied Git arguments; never shell-evaluate content."""
    if not args or any("\n" in arg for arg in args):
        raise EvidenceError("Invalid Git arguments")
    dangerous_options = {"-c", "--config-env", "--upload-pack", "--receive-pack", "--exec-path"}
    if any(arg in dangerous_options for arg in args):
        raise EvidenceError("Unsafe Git option")
    if any(arg in {"push", "pull", "fetch", "merge", "commit", "reset", "restore", "checkout", "rebase", "cherry-pick"} for arg in args):
        raise EvidenceError("Mutation is not permitted by evidence Git helper")
    try:
        shlex.join(args)
    except (TypeError, ValueError) as exc:
        raise EvidenceError("Invalid Git arguments") from exc
    try:
        return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError(f"Git evidence command failed: {' '.join(args)}") from exc
