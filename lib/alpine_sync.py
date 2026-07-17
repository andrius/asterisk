"""Pure logic for the Alpine sync resolver (plans/003-alpine-apk-images.md section 7).

Turns the live Cloudsmith APKINDEX picture into the set of ``os: alpine``
os_matrix members the build matrix should carry. No network, no file I/O, no
clock: the caller (scripts/alpine-sync.py) fetches the indexes and writes the
YAML; this module only parses index bytes and maps facts.

Responsibilities:
  - parse_apkindex: APKINDEX.tar.gz bytes -> flat package records.
  - resolve_pkgver: our version label -> the exact published pkgver (identity,
    the cert 4-component rule, the git newest-snapshot rule).
  - derive_roles: live vX.Y trees -> stable/previous; edge -> edge.
  - resolve_alpine_members: the whole mapping, including the desired-subpackage
    intersection, arch resolution, the at-most-one-member-per-(line,tree)
    dedup invariant, and the drift report.

The tree/pin/repo URL are NOT emitted here - the generator derives them from
the Alpine version (``lib.template_generator.alpine_tree``). A member carries
only resolved facts: distribution, alpine_tree, alpine_role, apk_version,
apk_packages, architectures.
"""
from __future__ import annotations

import io
import re
import tarfile
from typing import Dict, List, Optional, Tuple

try:
    from .tag_lifecycle import line_key
except ImportError:  # imported flat (scripts insert lib/ on sys.path)
    from tag_lifecycle import line_key

# Runtime-functional subpackages we want on every image, in install order. The
# published superset is larger (dbg/dev/doc/alsa/openrc/sounds-*); we take the
# intersection with what each line actually ships (cert omits ldap/pgsql/...,
# the git snapshot omits opus). sample-config is installed unconditionally by
# the Dockerfile, so it is not listed here.
DESIRED_SUBPACKAGES = [
    "opus", "srtp", "curl", "speex", "fax",
    "odbc", "ldap", "pgsql", "prometheus", "mobile", "tds",
]

# Cloudsmith arch segment -> our matrix arch name -> docker platform.
ARCH_MAP = {
    "x86_64": "amd64",
    "aarch64": "arm64",
    "armv7": "armv7",
    "armhf": "armhf",
}
ARCH_ORDER = ["amd64", "arm64", "armv7", "armhf"]

# The arch segments we probe on every tree (32-bit indexes may be empty).
CANDIDATE_ARCHES = ["x86_64", "aarch64", "armv7", "armhf"]

_CERT_RE = re.compile(r"^(\d+)\.(\d+)-cert(\d+)$")
_RN_RE = re.compile(r"-r\d+$")


def _is_git(label: str) -> bool:
    return label == "git" or label.startswith("git")


def _major(label: str) -> int:
    """Leading major version; git sorts highest."""
    if _is_git(label):
        return 99
    m = re.match(r"^(\d+)", label)
    return int(m.group(1)) if m else 0


def _strip_rn(pkgver: str) -> str:
    """Drop the apk pkgrel: 22.10.1-r0 -> 22.10.1."""
    return _RN_RE.sub("", pkgver)


def parse_apkindex(tar_gz_bytes: bytes) -> List[Dict[str, str]]:
    """Parse APKINDEX.tar.gz bytes into flat package records.

    Each record is ``{"name": P, "version": V, "arch": A}``. Records are
    blank-line separated inside the ``APKINDEX`` member of the tarball.
    """
    with tarfile.open(fileobj=io.BytesIO(tar_gz_bytes), mode="r:gz") as tar:
        member = tar.extractfile("APKINDEX")
        if member is None:
            return []
        text = member.read().decode("utf-8", errors="replace")

    records: List[Dict[str, str]] = []
    cur: Dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if cur.get("name"):
                records.append({
                    "name": cur.get("name", ""),
                    "version": cur.get("version", ""),
                    "arch": cur.get("arch", ""),
                })
            cur = {}
            continue
        key, _, val = line.partition(":")
        if key == "P":
            cur["name"] = val
        elif key == "V":
            cur["version"] = val
        elif key == "A":
            cur["arch"] = val
    if cur.get("name"):
        records.append({
            "name": cur.get("name", ""),
            "version": cur.get("version", ""),
            "arch": cur.get("arch", ""),
        })
    return records


def tree_to_distribution(tree: str) -> str:
    """Cloudsmith tree segment -> matrix distribution token (v3.24 -> 3.24)."""
    return tree[1:] if re.match(r"^v\d", tree) else tree


def distribution_to_tree(distribution: str) -> str:
    """Inverse of tree_to_distribution; mirrors template_generator.alpine_tree."""
    return distribution if distribution == "edge" else f"v{distribution}"


def _pkgver_sort_key(pkgver: str) -> Tuple:
    """Sort key over the numeric components of a stripped pkgver."""
    base = _strip_rn(pkgver)
    nums = re.findall(r"\d+", base)
    return tuple(int(n) for n in nums)


def resolve_pkgver(label: str, pkgvers) -> Optional[str]:
    """Map our matrix label to the exact published pkgver present in ``pkgvers``.

    Rules:
      - git   -> the newest ``*_git*`` snapshot.
      - cert  -> ``NN.M-certK`` maps to the 4-component ``NN.M.0.K``.
      - else  -> identity on the version part (``-rN`` stripped).
    Returns the full pkgver (with ``-rN``) or None if not published.
    """
    pkgvers = set(pkgvers)
    if _is_git(label):
        snaps = [v for v in pkgvers if "_git" in v]
        return max(snaps, key=_pkgver_sort_key) if snaps else None

    cert = _CERT_RE.match(label)
    target = f"{cert.group(1)}.{cert.group(2)}.0.{cert.group(3)}" if cert else label
    for v in pkgvers:
        if _strip_rn(v) == target:
            return v
    return None


def derive_roles(live_trees) -> Dict[str, str]:
    """Assign roles: highest live vX.Y -> stable, lower -> previous, edge -> edge."""
    numeric = sorted(
        (t for t in live_trees if t != "edge"),
        key=lambda t: _pkgver_sort_key(t),
    )
    roles: Dict[str, str] = {}
    for t in live_trees:
        if t == "edge":
            roles[t] = "edge"
        elif numeric and t == numeric[-1]:
            roles[t] = "stable"
        else:
            roles[t] = "previous"
    return roles


def _line_token(label: str) -> str:
    """Dedup bucket per Asterisk line; git is its own bucket."""
    return "git" if _is_git(label) else line_key(label)


def resolve_alpine_members(*, versions, indexes,
                           desired_subpackages=None, drift_major_floor=0):
    """Resolve the ``os: alpine`` members from the live index picture.

    Args:
      versions: ``[{"version": label, "active": bool}, ...]`` - every matrix
        entry that could carry an Alpine member (active or deprecated-surviving).
      indexes: ``{tree: {cloud_arch: [records]}}`` - parsed APKINDEX per probed
        (tree, arch). A tree/arch that 404'd or was empty is absent or ``[]``.
      desired_subpackages: override for DESIRED_SUBPACKAGES (tests).
      drift_major_floor: only report drift for active lines whose major version
        is >= this (0 = all). Suppresses ancient legacy (1.x-15.x) that Alpine
        never carries, keeping the report actionable. Does NOT gate which
        members are built - that is purely index-driven (decision #2).

    Returns ``(members_by_version, drift)``:
      members_by_version: ``{label: [member_dict, ...]}`` (member per live tree).
      drift: ``{"no_apk": [active labels with no member, floor-filtered]}``.
    """
    desired = list(DESIRED_SUBPACKAGES if desired_subpackages is None
                   else desired_subpackages)

    # A tree is live only if some arch published >=1 asterisk package.
    live_trees = [
        tree for tree, per_arch in indexes.items()
        if any(any(r["name"] == "asterisk" for r in recs)
               for recs in per_arch.values())
    ]
    roles = derive_roles(live_trees)

    # Per (tree, arch): the asterisk main pkgvers and, per pkgver, the set of
    # available subpackage short names.
    main_by_tree: Dict[str, Dict[str, set]] = {}
    subs_by_tree: Dict[str, Dict[str, Dict[str, set]]] = {}
    for tree in live_trees:
        main_by_tree[tree] = {}
        subs_by_tree[tree] = {}
        for arch, recs in indexes[tree].items():
            mains = {r["version"] for r in recs if r["name"] == "asterisk"}
            main_by_tree[tree][arch] = mains
            per_pkgver: Dict[str, set] = {}
            for r in recs:
                if r["name"].startswith("asterisk-"):
                    per_pkgver.setdefault(r["version"], set()).add(r["name"][len("asterisk-"):])
            subs_by_tree[tree][arch] = per_pkgver

    # Build candidate members: one per (label, tree) where the pkgver is live.
    candidates: List[Tuple[str, Dict]] = []  # (label, member)
    for entry in versions:
        label = entry["version"]
        for tree in live_trees:
            if _is_git(label) and tree != "edge":
                continue  # the git snapshot is edge-only
            union = set().union(*main_by_tree[tree].values()) if main_by_tree[tree] else set()
            pkgver = resolve_pkgver(label, union)
            if not pkgver:
                continue
            arches_cloud = [a for a, mains in main_by_tree[tree].items() if pkgver in mains]
            if not arches_cloud:
                continue
            # subpackages available on EVERY target arch (multi-arch build safety)
            avail = None
            for a in arches_cloud:
                have = subs_by_tree[tree][a].get(pkgver, set())
                avail = have if avail is None else (avail & have)
            avail = avail or set()
            packages = [p for p in desired if p in avail]
            arches = sorted(
                {ARCH_MAP[a] for a in arches_cloud if a in ARCH_MAP},
                key=ARCH_ORDER.index,
            )
            member = {
                "os": "alpine",
                "distribution": tree_to_distribution(tree),
                "alpine_tree": tree,
                "alpine_role": roles[tree],
                "apk_version": pkgver,
                "apk_packages": packages,
                "architectures": arches,
            }
            candidates.append((label, member))

    # Invariant: at most one member per (line, tree) - the newest pkgver wins,
    # else two builds race the <line>-alpine[-av] tag (plan 003 section 6).
    best: Dict[Tuple[str, str], Tuple[str, Dict]] = {}
    for label, member in candidates:
        key = (_line_token(label), member["alpine_tree"])
        incumbent = best.get(key)
        if incumbent is None or _pkgver_sort_key(member["apk_version"]) > \
                _pkgver_sort_key(incumbent[1]["apk_version"]):
            best[key] = (label, member)

    members_by_version: Dict[str, List[Dict]] = {}
    kept_labels = set()
    for label, member in best.values():
        members_by_version.setdefault(label, []).append(member)
        kept_labels.add(label)
    # Deterministic order: trees by role (stable, previous, edge) then dist.
    _role_rank = {"stable": 0, "previous": 1, "edge": 2}
    for label in members_by_version:
        members_by_version[label].sort(
            key=lambda m: (_role_rank.get(m["alpine_role"], 9), m["distribution"]))

    drift = {
        "no_apk": [e["version"] for e in versions
                   if e.get("active") and e["version"] not in kept_labels
                   and _major(e["version"]) >= drift_major_floor],
    }
    return members_by_version, drift
