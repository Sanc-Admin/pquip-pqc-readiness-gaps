#!/usr/bin/env python3
"""IETF Datatracker prior-art monitor.

Reads a repo-specific query set, runs it against the public Datatracker API,
diffs the results against a committed baseline, and reports ONLY drafts that
are new or newly revised relative to that baseline.

Design notes / guard rails:

* The Datatracker Tastypie API silently IGNORES unknown filter keywords. A
  typo such as ``name__containss=foo`` returns the ENTIRE draft corpus with
  HTTP 200. Every query is therefore (a) restricted to a documented filter
  allow-list and (b) sanity-capped: a query whose ``meta.total_count``
  exceeds MAX_HITS_PER_QUERY is treated as a configuration error and the run
  FAILS instead of filing a meaningless issue.
* Any HTTP/transport/JSON error also fails the run loudly. Silence is never
  interpreted as "no prior art".

Outputs (all optional, controlled by env):
  PRIOR_ART_FINDINGS_JSON  path to write the findings payload
  GITHUB_OUTPUT            gets ``new_hits=<n>``
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://datatracker.ietf.org/api/v1"
UA = "sanctumsecops-prior-art-monitor/2.0 (+https://github.com/sanctumsecopsmssp)"
TIMEOUT = 45
MAX_HITS_PER_QUERY = 60
PAGE_LIMIT = 100

# Documented Tastypie filters we allow in the query config. Anything else is a
# config bug, because unknown keys are ignored by the API and would silently
# widen the query to "every draft ever published".
ALLOWED_FILTERS = {
    "name__contains",
    "title__icontains",
    "group__acronym",
    "states__slug",
    "type",
}


class MonitorError(RuntimeError):
    pass


def _get(path: str, params: dict) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                raise MonitorError(f"Datatracker returned HTTP {resp.status} for {url}")
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        raise MonitorError(f"Datatracker HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise MonitorError(f"Datatracker unreachable ({exc.reason}) for {url}") from exc
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise MonitorError(f"Datatracker returned non-JSON for {url}") from exc
    if "meta" not in data or "objects" not in data:
        raise MonitorError(f"Unexpected Datatracker payload shape for {url}")
    return data


_GROUP_CACHE: dict[str, str] = {}


def group_acronym(resource_uri: str | None) -> str:
    """Resolve /api/v1/group/group/<id>/ to a WG acronym."""
    if not resource_uri:
        return "none"
    if resource_uri in _GROUP_CACHE:
        return _GROUP_CACHE[resource_uri]
    url = f"https://datatracker.ietf.org{resource_uri}"
    req = urllib.request.Request(url + "?format=json", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            acronym = json.loads(resp.read()).get("acronym", "unknown")
    except Exception:  # a WG lookup failure must not mask real findings
        acronym = "unknown"
    _GROUP_CACHE[resource_uri] = acronym
    return acronym


def run_query(query: dict) -> list[dict]:
    filters = query["filters"]
    bad = set(filters) - ALLOWED_FILTERS
    if bad:
        raise MonitorError(
            f"query '{query.get('label')}' uses non-allow-listed Datatracker "
            f"filter(s) {sorted(bad)}; unknown filters are silently ignored by "
            "the API and would match every draft"
        )
    params = {"format": "json", "limit": PAGE_LIMIT, "type": "draft"}
    params.update(filters)
    data = _get("/doc/document/", params)
    total = data["meta"].get("total_count", 0)
    if total > MAX_HITS_PER_QUERY:
        raise MonitorError(
            f"query '{query.get('label')}' matched {total} drafts (cap "
            f"{MAX_HITS_PER_QUERY}). Refusing to file a low-signal issue; "
            "tighten the query in .github/prior-art-queries.json"
        )
    objects = list(data["objects"])
    while data["meta"].get("next"):
        nxt = data["meta"]["next"]
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(nxt).query))
        data = _get("/doc/document/", qs)
        objects.extend(data["objects"])

    # Second-stage, client-side narrowing. The Datatracker API cannot AND two
    # title substrings, so a broad-but-bounded title query is paired with a
    # required-keyword list to keep the match set on-subject.
    require = [s.lower() for s in query.get("require_title_any", [])]
    if require:
        objects = [
            o for o in objects
            if any(k in ((o.get("title") or "") + " " + o.get("name", "")).lower() for k in require)
        ]

    for obj in objects:
        obj["_query"] = query.get("label", "")
    return objects


def collect(config: dict) -> tuple[dict[str, dict], list[str]]:
    exclusions = [s.lower() for s in config.get("exclude_name_contains", [])]
    hits: dict[str, dict] = {}
    labels: list[str] = []
    for query in config["queries"]:
        labels.append(query.get("label", ""))
        for obj in run_query(query):
            name = obj.get("name", "")
            if not name.startswith("draft-"):
                continue
            if any(ex in name.lower() for ex in exclusions):
                continue
            rec = {
                "name": name,
                "rev": obj.get("rev", "??"),
                "title": (obj.get("title") or "").strip(),
                "updated": (obj.get("time") or "")[:10],
                "wg": group_acronym(obj.get("group")),
                "url": f"https://datatracker.ietf.org/doc/{name}/",
                "matched_query": obj.get("_query", ""),
            }
            prev = hits.get(name)
            if prev is None:
                hits[name] = rec
            elif rec["matched_query"] not in prev["matched_query"]:
                prev["matched_query"] += f", {rec['matched_query']}"
    return hits, labels


def diff(hits: dict[str, dict], baseline: dict) -> tuple[list[dict], list[dict]]:
    seen = baseline.get("seen", {})
    new_drafts, new_revs = [], []
    for name, rec in sorted(hits.items()):
        if name not in seen:
            new_drafts.append(rec)
        elif str(seen[name].get("rev")) != str(rec["rev"]):
            rec = dict(rec, previous_rev=seen[name].get("rev"))
            new_revs.append(rec)
    return new_drafts, new_revs


def render_body(repo: str, hits, new_drafts, new_revs, labels, run_url, stamp) -> str:
    lines = [
        f"Rolling prior-art status for `{repo}`. This single issue is updated in "
        "place by the Prior Art Monitor workflow; it is not re-created per run.",
        "",
        f"- Last sweep (UTC): {stamp}",
        f"- Queries executed: {len(labels)}",
        f"- Drafts currently matched: {len(hits)}",
        f"- New drafts since baseline: {len(new_drafts)}",
        f"- New revisions of known drafts: {len(new_revs)}",
        f"- Workflow run: {run_url}",
        "",
    ]

    def table(rows, revcol=False):
        head = "| Draft | Rev | Title | Last updated | WG | Matched query |"
        sep = "| --- | --- | --- | --- | --- | --- |"
        out = [head, sep]
        for r in rows:
            rev = f"-{r['rev']}" + (f" (was -{r['previous_rev']})" if revcol else "")
            title = r["title"].replace("|", "\\|")
            out.append(
                f"| [{r['name']}]({r['url']}) | {rev} | {title} | "
                f"{r['updated']} | {r['wg']} | {r['matched_query']} |"
            )
        return out

    if new_drafts:
        lines += ["## New drafts (not in baseline)", ""] + table(new_drafts) + [""]
    if new_revs:
        lines += ["## New revisions of baselined drafts", ""] + table(new_revs, revcol=True) + [""]
    if not new_drafts and not new_revs:
        lines += [
            "## No change",
            "",
            "Every matched draft is already recorded in "
            "`.github/prior-art-baseline.json` at the same revision. No action required.",
            "",
        ]
    lines += ["## Current match set", ""] + table(sorted(hits.values(), key=lambda r: r["name"])) + [""]
    lines += [
        "## Queries",
        "",
        *[f"- {label}" for label in labels],
        "",
        "## How this works",
        "",
        "- Baseline: `.github/prior-art-baseline.json` records every draft name and "
        "revision already reviewed. Only drafts absent from the baseline, or at a "
        "higher revision than the baseline, are reported as new.",
        "- The baseline is updated by the same run, so a finding is announced once "
        "rather than every sweep.",
        "- Query set: `.github/prior-art-queries.json`. A query that matches more "
        f"than {MAX_HITS_PER_QUERY} drafts, or a Datatracker error of any kind, "
        "fails the workflow loudly instead of filing a content-free issue.",
    ]
    return "\n".join(lines)


def main() -> int:
    root = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", "."))
    repo = os.environ.get("REPO_NAME") or root.name
    qpath = root / ".github" / "prior-art-queries.json"
    bpath = root / ".github" / "prior-art-baseline.json"
    if not qpath.exists():
        raise MonitorError(f"missing query config: {qpath}")
    config = json.loads(qpath.read_text())
    if not config.get("queries"):
        raise MonitorError(f"{qpath} defines no queries")
    baseline = json.loads(bpath.read_text()) if bpath.exists() else {"seen": {}}

    hits, labels = collect(config)
    new_drafts, new_revs = diff(hits, baseline)

    print(f"repo={repo} queries={len(labels)} matched={len(hits)} "
          f"new_drafts={len(new_drafts)} new_revs={len(new_revs)}")
    for rec in new_drafts + new_revs:
        print(f"  NEW {rec['name']}-{rec['rev']} [{rec['wg']}] {rec['title']}")

    stamp = os.environ.get("SWEEP_STAMP", "")
    run_url = os.environ.get("RUN_URL", "")
    body = render_body(repo, hits, new_drafts, new_revs, labels, run_url, stamp)

    payload = {
        "repo": repo,
        "swept_at": stamp,
        "matched": sorted(hits.values(), key=lambda r: r["name"]),
        "new_drafts": new_drafts,
        "new_revisions": new_revs,
        "body": body,
    }
    out = os.environ.get("PRIOR_ART_FINDINGS_JSON")
    if out:
        pathlib.Path(out).write_text(json.dumps(payload, indent=2) + "\n")

    # Update the baseline in the same run so findings are not re-reported.
    baseline["updated"] = stamp
    baseline["queries_source"] = ".github/prior-art-queries.json"
    seen = baseline.setdefault("seen", {})
    for name, rec in hits.items():
        seen[name] = {
            "rev": rec["rev"],
            "title": rec["title"],
            "wg": rec["wg"],
            "first_seen": seen.get(name, {}).get("first_seen", stamp or rec["updated"]),
            "last_seen_rev_at": stamp or rec["updated"],
        }
    baseline["seen"] = dict(sorted(seen.items()))
    bpath.parent.mkdir(parents=True, exist_ok=True)
    bpath.write_text(json.dumps(baseline, indent=2, sort_keys=False) + "\n")

    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as fh:
            fh.write(f"new_hits={len(new_drafts) + len(new_revs)}\n")
            fh.write(f"matched={len(hits)}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MonitorError as exc:
        print(f"::error title=Prior Art Monitor::{exc}")
        sys.exit(1)
