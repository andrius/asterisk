"""Pure logic for semantic-tag promotion and version deprecation.

No I/O, no clock, no git. Input is the parsed ``latest_builds`` list from
asterisk/supported-asterisk-builds.yml; output is a Plan (see plan()).
Spec: docs/superpowers/specs/2026-07-04-tag-lifecycle-design.md
"""
from __future__ import annotations

import re

_BASE_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")
_CERT_RE = re.compile(r"-cert(\d+)")
EXPERIMENTAL_TOKEN = "experimental"


def version_sort_key(version):
    """Return (major, minor, patch, cert_number); 'git'/'git-*' -> (999,0,0,0)."""
    if version == "git" or version.startswith("git-"):
        return (999, 0, 0, 0)
    cert = _CERT_RE.search(version)
    cert_number = int(cert.group(1)) if cert else 0
    base = version.split("-cert")[0]
    m = _BASE_RE.match(base)
    if not m:
        raise ValueError(f"unparseable version: {version!r}")
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) else 0
    return (major, minor, patch, cert_number)


def is_cert(version):
    return "-cert" in version


def line_key(version):
    """Grouping key for tag ownership. Raises ValueError if unparseable."""
    major, minor, _patch, _cert = version_sort_key(version)
    if is_cert(version):
        return f"{major}-cert"
    if major == 1:
        return f"{major}.{minor}"
    return str(major)


from dataclasses import dataclass, field


@dataclass
class Plan:
    set_tags: dict = field(default_factory=dict)            # version -> entry additional_tags
    clear_tags: set = field(default_factory=set)            # versions to strip entry tags from
    deprecate: dict = field(default_factory=dict)           # version -> superseded_by
    migrate_experimental: dict = field(default_factory=dict)  # new_version -> [member dicts]


def _is_git(build):
    v = build.get("version", "")
    return v == "git" or v.startswith("git-")


def _is_active(build):
    return "os_matrix" in build and not build.get("deprecated_at")


def _active_parseable(builds):
    out = []
    for b in builds:
        if _is_git(b) or not _is_active(b):
            continue
        try:
            line_key(b["version"])
        except (ValueError, KeyError):
            continue
        out.append(b)
    return out


def _newest_per_line(active):
    lines = {}
    for b in active:
        lines.setdefault(line_key(b["version"]), []).append(b)
    newest = {lk: max(entries, key=lambda b: version_sort_key(b["version"]))
              for lk, entries in lines.items()}
    return lines, newest


def _lts_major(newest):
    """Highest active even (LTS) *stable* major, or None."""
    best = None
    for lk, b in newest.items():
        if lk.endswith("-cert"):
            continue
        major = version_sort_key(b["version"])[0]
        if major % 2 == 0 and (best is None or major > best):
            best = major
    return best


def _experimental_members(build):
    members = build.get("os_matrix") or []
    return [m for m in members
            if EXPERIMENTAL_TOKEN in (m.get("additional_tags") or "")]


def plan(builds):
    active = _active_parseable(builds)
    lines, newest = _newest_per_line(active)
    lts = _lts_major(newest)

    p = Plan()
    for lk, b in newest.items():
        ver = b["version"]
        if lk.endswith("-cert"):
            tags = [lk]
        else:
            major, _minor, _patch, _cert = version_sort_key(ver)
            bare = lk if major == 1 else str(major)
            tags = [bare]
            if lts is not None and major == lts:
                tags = ["latest", "stable"] + tags
        p.set_tags[ver] = ",".join(tags)

    for lk, entries in lines.items():
        keep = newest[lk]["version"]
        keep_dists = {m.get("distribution")
                      for m in (newest[lk].get("os_matrix") or [])}
        for b in entries:
            ver = b["version"]
            if ver == keep:
                continue
            p.deprecate[ver] = keep
            if b.get("additional_tags"):
                p.clear_tags.add(ver)
            to_move = [m for m in _experimental_members(b)
                       if m.get("distribution") not in keep_dists]
            if to_move:
                p.migrate_experimental.setdefault(keep, []).extend(to_move)
    return p
