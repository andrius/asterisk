#!/usr/bin/env python3
# scripts/alpine-sync.py
"""Mirror the live Cloudsmith APKINDEX into ``os: alpine`` os_matrix members.

The daily ``alpine-sync.yml`` workflow runs this against
``asterisk/supported-asterisk-builds.yml``:

  1. Probe the candidate Cloudsmith trees (from templates/distributions/alpine.yml)
     across {x86_64, aarch64, armv7, armhf}, fetching each APKINDEX.tar.gz.
  2. Hand the parsed indexes + the matrix version labels to the pure resolver
     (lib/alpine_sync.py), which returns the desired Alpine members + a drift
     report (active lines with no published apk).
  3. Upsert those members in place (ruamel round-trip: Debian members and their
     formatting are untouched; stale Alpine members are dropped).
  4. Emit a change + drift summary (to GITHUB_STEP_SUMMARY when set).

I/O only. All mapping/derivation lives in lib/alpine_sync.py and is unit-tested
against captured fixtures. Spec: plans/003-alpine-apk-images.md section 7.
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))
import alpine_sync as A  # noqa: E402

DEFAULT_MATRIX = os.path.join(ROOT, "asterisk", "supported-asterisk-builds.yml")
ALPINE_YML = os.path.join(ROOT, "templates", "distributions", "alpine.yml")

# Member key order (mirrors the spec section 5 example).
_MEMBER_ORDER = ["os", "distribution", "alpine_tree", "alpine_role",
                 "apk_version", "apk_packages", "architectures"]


def _yaml() -> YAML:
    # Same dialect as scripts/apply-tag-lifecycle.py so a no-op round-trip is
    # byte-stable and real edits produce minimal PR diffs.
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _load_alpine_config():
    with open(ALPINE_YML) as f:
        return _yaml().load(f)


def candidate_trees(cfg) -> list:
    """v3.<min..max> (+ edge) from the alpine.yml probe range."""
    lo = int(cfg.get("apk_probe_minor_min", 20))
    hi = int(cfg.get("apk_probe_minor_max", 40))
    trees = [f"v3.{m}" for m in range(lo, hi + 1)]
    if cfg.get("apk_probe_include_edge", True):
        trees.append("edge")
    return trees


def fetch(url: str, timeout: int = 30):
    """GET url -> bytes, or None on 404/other HTTP error."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except urllib.error.URLError:
        return None


def probe_indexes(base: str, trees, arches, log=print) -> dict:
    """Fetch + parse every (tree, arch) index; absent/404 -> omitted."""
    indexes: dict = {}
    for tree in trees:
        per_arch = {}
        for arch in arches:
            url = f"{base}/{tree}/main/{arch}/APKINDEX.tar.gz"
            raw = fetch(url)
            if raw is None:
                continue
            recs = A.parse_apkindex(raw)
            per_arch[arch] = recs
            n_ast = sum(1 for r in recs if r["name"] == "asterisk")
            log(f"  probe {tree}/{arch}: {n_ast} asterisk pkg(s)", file=sys.stderr)
        if per_arch:
            indexes[tree] = per_arch
    return indexes


def load_versions(data) -> list:
    """Every entry that can carry an Alpine member.

    Candidates = entries with an os_matrix (intentionally-disabled entries have
    none and are excluded). ``active`` = not deprecated: a deprecated entry is
    still a candidate (deprecation-survival) but drift is reported only for
    active lines.
    """
    versions = []
    for build in data.get("latest_builds", []):
        v = build.get("version")
        if not v or "os_matrix" not in build or build.get("os_matrix") is None:
            continue
        versions.append({"version": v, "active": not build.get("deprecated_at")})
    return versions


def _to_member(m: dict) -> CommentedMap:
    """Build a ruamel member matching the repo's quoted-scalar style."""
    cm = CommentedMap()
    for key in _MEMBER_ORDER:
        val = m[key]
        if key == "apk_packages":
            seq = CommentedSeq(DQ(p) for p in val)
            seq.fa.set_flow_style()  # compact [opus, srtp, ...]
            cm[key] = seq
        elif key == "architectures":
            cm[key] = CommentedSeq(DQ(a) for a in val)  # block, like Debian members
        else:
            cm[key] = DQ(str(val))
    return cm


def upsert(data, members_by_version) -> dict:
    """Replace each entry's Alpine members in place. Returns a change summary."""
    summary = {"set": [], "removed": []}
    for build in data.get("latest_builds", []):
        v = build.get("version")
        om = build.get("os_matrix")
        if not v or om is None:
            continue
        had = [i for i in range(len(om)) if isinstance(om[i], dict)
               and om[i].get("os") == "alpine"]
        for i in reversed(had):
            del om[i]
        resolved = members_by_version.get(v, [])
        for m in resolved:
            om.append(_to_member(m))
        if resolved:
            summary["set"].append(
                f"{v}: " + ", ".join(f"{m['distribution']}={m['apk_version']}"
                                     for m in resolved))
        elif had:
            summary["removed"].append(v)
    return summary


def render_summary(summary, drift) -> str:
    lines = ["# Alpine sync", ""]
    if summary["set"]:
        lines.append("## Alpine members set")
        lines += [f"- {s}" for s in summary["set"]]
        lines.append("")
    if summary["removed"]:
        lines.append("## Alpine members removed (apk no longer live)")
        lines += [f"- {v}" for v in summary["removed"]]
        lines.append("")
    if drift.get("no_apk"):
        lines.append("## Drift - active lines with no published apk")
        lines += [f"- {v}" for v in sorted(drift["no_apk"])]
        lines.append("")
    if len(lines) == 2:
        lines.append("_No Alpine changes; index matches the matrix._")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", default=DEFAULT_MATRIX, help="matrix YAML to update")
    ap.add_argument("--dry-run", action="store_true",
                    help="probe + resolve + report, but do not write the matrix")
    args = ap.parse_args(argv)

    alpine_cfg = _load_alpine_config()
    base = alpine_cfg["apk_repo_base"]
    trees = candidate_trees(alpine_cfg)

    print(f"Probing {len(trees)} tree(s) x {len(A.CANDIDATE_ARCHES)} arch(es) "
          f"under {base}", file=sys.stderr)
    indexes = probe_indexes(base, trees, A.CANDIDATE_ARCHES)
    if not indexes:
        print("ERROR: no live Cloudsmith index reachable", file=sys.stderr)
        return 1

    y = _yaml()
    with open(args.file) as f:
        data = y.load(f)

    versions = load_versions(data)
    members_by_version, drift = A.resolve_alpine_members(
        versions=versions, indexes=indexes,
        drift_major_floor=int(alpine_cfg.get("apk_drift_major_min", 16)))
    summary = upsert(data, members_by_version)

    report = render_summary(summary, drift)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write(report)
    print(report, file=sys.stderr)

    if args.dry_run:
        print("(dry-run) matrix not written", file=sys.stderr)
        return 0

    with open(args.file, "w") as f:
        y.dump(data, f)
    print(f"Wrote {args.file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
