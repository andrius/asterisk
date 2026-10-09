"""Pure logic for semantic-tag promotion and version deprecation.

No I/O, no clock, no git. Input is the parsed ``latest_builds`` list from
asterisk/supported-asterisk-builds.yml; output is a Plan (see plan()).
Spec: docs/superpowers/specs/2026-07-04-tag-lifecycle-design.md
"""
from __future__ import annotations

import re

_BASE_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")
_CERT_RE = re.compile(r"-cert(\d+)")
_PRE_RE = re.compile(r"-(alpha|beta|rc)(\d*)")
# Pre-release stages sort below their GA release (same priorities as
# scripts/discover-latest-versions.sh: alpha < beta < rc < stable).
_STAGES = {"alpha": 0, "beta": 1, "rc": 2}
_GA_STAGE = 3
EXPERIMENTAL_TOKEN = "experimental"


def version_sort_key(version):
    """Return (major, minor, patch, cert_number, stage, pre_number).

    stage is alpha=0 < beta=1 < rc=2 < GA=3, so 24.0.0-rc2 sorts above 23.5.0
    and below 24.0.0. 'git'/'git-*' -> (999, 0, 0, 0, 3, 0).
    """
    if version == "git" or version.startswith("git-"):
        return (999, 0, 0, 0, _GA_STAGE, 0)
    cert = _CERT_RE.search(version)
    cert_number = int(cert.group(1)) if cert else 0
    pre = _PRE_RE.search(version)
    stage = _STAGES[pre.group(1)] if pre else _GA_STAGE
    pre_number = int(pre.group(2) or 0) if pre else 0
    base = version.split("-cert")[0]
    m = _BASE_RE.match(base)
    if not m:
        raise ValueError(f"unparseable version: {version!r}")
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) else 0
    return (major, minor, patch, cert_number, stage, pre_number)


def is_cert(version):
    return "-cert" in version


def is_prerelease(version):
    """True for alpha/beta/rc releases (24.0.0-rc2), False for GA releases."""
    return bool(_PRE_RE.search(version))


def line_key(version):
    """Grouping key for tag ownership. Raises ValueError if unparseable."""
    major, minor = version_sort_key(version)[:2]
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


def _key(build):
    return version_sort_key(build["version"])


def _newest(entries):
    return max(entries, key=_key) if entries else None


def _owners_per_line(active):
    """Per line: (newest GA entry, newest pre-release newer than that GA).

    A pre-release only owns its '<line>-rc' tag while no GA release of the
    same or a newer version exists; it never takes the line from a GA release.
    """
    lines = {}
    for b in active:
        lines.setdefault(line_key(b["version"]), []).append(b)
    owners = {}
    for lk, entries in lines.items():
        ga = _newest([b for b in entries if not is_prerelease(b["version"])])
        rc = _newest([b for b in entries if is_prerelease(b["version"])])
        if rc is not None and ga is not None and _key(rc) < _key(ga):
            rc = None
        owners[lk] = (ga, rc)
    return lines, owners


def _latest_stable_majors(owners):
    """(latest, stable) majors: newest GA series and newest LTS (even) GA series.

    docs.asterisk.org/About-the-Project/Asterisk-Versions: 'latest' is the
    newest released series (Standard or LTS), 'stable' the newest LTS series.
    They coincide while the newest released series is an LTS. Cert lines and
    pre-release-only lines never count.
    """
    majors = [_key(ga)[0] for lk, (ga, _rc) in owners.items()
              if ga is not None and not lk.endswith("-cert")]
    lts = [m for m in majors if m % 2 == 0]
    return (max(majors) if majors else None), (max(lts) if lts else None)


def _experimental_members(build):
    members = build.get("os_matrix") or []
    return [m for m in members
            if EXPERIMENTAL_TOKEN in (m.get("additional_tags") or "")]


def plan(builds):
    active = _active_parseable(builds)
    lines, owners = _owners_per_line(active)
    latest, stable = _latest_stable_majors(owners)

    p = Plan()
    for lk, (ga, rc) in owners.items():
        if ga is not None:
            tags = [lk]
            if not lk.endswith("-cert"):
                major = _key(ga)[0]
                if major == stable:
                    tags.insert(0, "stable")
                if major == latest:
                    tags.insert(0, "latest")
            p.set_tags[ga["version"]] = ",".join(tags)
        if rc is not None:
            p.set_tags[rc["version"]] = f"{lk}-rc"

    for lk, entries in lines.items():
        ga, rc = owners[lk]
        keepers = {o["version"]: o for o in (ga, rc) if o is not None}
        keep_dists = {v: {m.get("distribution") for m in (o.get("os_matrix") or [])}
                      for v, o in keepers.items()}
        for b in entries:
            ver = b["version"]
            if ver in keepers:
                continue
            # A pre-release newer than the GA owner is superseded by the newest
            # pre-release; everything else (older GA, or an RC that its GA has
            # shipped past) by the GA owner.
            if rc is not None and is_prerelease(ver) and (ga is None or _key(b) > _key(ga)):
                keep = rc["version"]
            else:
                keep = ga["version"]
            p.deprecate[ver] = keep
            if b.get("additional_tags"):
                p.clear_tags.add(ver)
            to_move = [m for m in _experimental_members(b)
                       if m.get("distribution") not in keep_dists[keep]]
            if to_move:
                p.migrate_experimental.setdefault(keep, []).extend(to_move)
                keep_dists[keep].update(m.get("distribution") for m in to_move)
    return p
