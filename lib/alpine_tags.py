"""Pure logic for the Alpine image tag lattice.

No I/O, no clock, no git. Given the facts of one Alpine build leg (the
Asterisk version label, its exact apk pin, the Alpine version + role, and
whether it owns the `latest`/`stable` line), returns the set of Docker tags
that leg publishes.

The lattice spans two axes:
  - Asterisk identity: the line token (`22`, `22-cert`, `23`) and the full
    version label (`22.10.1`, `22.8-cert3`).
  - Alpine identity: implicit (no version suffix, minted ONLY for the stable
    tree) and explicit (`alpine-3.24`, `alpine-edge`).

Gating the implicit tags to the stable tree is what lets `edge` coexist
without stealing the generic tags (`22-alpine`, `alpine`) from stable.

NOT emitted here: the `<version>_<os>-<distribution>` underscore twin and its
sha-suffixed variant - those come from the existing build-single-image meta
step, unchanged. Spec: plans/003-alpine-apk-images.md section 6.
"""
from __future__ import annotations

import re

try:
    from .tag_lifecycle import line_key
except ImportError:  # imported flat (scripts insert lib/ on sys.path)
    from tag_lifecycle import line_key

# The git line is the bleeding-edge channel; it publishes these convenience
# tags in addition to its immutable snapshot tag.
_GIT_CHANNELS = ("git", "testing", "dev")


def _is_git(version: str) -> bool:
    return version == "git" or version.startswith("git")


def _strip_pkgrel(apk_version: str) -> str:
    """Drop the apk pkgrel suffix: 24.0.0_git20260716-r0 -> 24.0.0_git20260716."""
    return re.sub(r"-r\d+$", "", apk_version) if apk_version else apk_version


def alpine_tags(*, version: str, apk_version: str, alpine_version: str,
                alpine_role: str, owns_latest: bool = False) -> list:
    """Return the Docker tags an Alpine build leg publishes.

    Args:
      version: our matrix version label (``22.10.1``, ``22.8-cert3``, ``git``).
      apk_version: the exact apk pin (``22.10.1-r0``); used for the git
        immutable snapshot tag.
      alpine_version: ``3.24`` or ``edge`` (the explicit tag token).
      alpine_role: ``stable`` | ``previous`` | ``edge``. Implicit (unsuffixed)
        tags are minted only for ``stable``.
      owns_latest: True when this version holds the ``latest``/``stable`` line
        (computed cross-leg by the caller, mirroring tag_lifecycle).

    Deterministic, de-duplicated, insertion-ordered.
    """
    av = alpine_version
    is_stable = alpine_role == "stable"
    tags: list = []

    if _is_git(version):
        # Git rides one tree (edge today). Its convenience tags are always
        # minted regardless of tree (per the design: git is the bleeding-edge
        # channel). If git is ever published on 2+ trees at once, exactly one
        # leg must own the bare tags to avoid a race - deferred until that
        # happens (plans/003 section 6).
        for channel in _GIT_CHANNELS:
            tags.append(f"{channel}-alpine")          # git-alpine, testing-alpine, dev-alpine
            tags.append(f"{channel}-alpine-{av}")     # git-alpine-edge, ...
        pkgver = _strip_pkgrel(apk_version)
        if pkgver:
            tags.append(f"{pkgver}-alpine-{av}")      # 24.0.0_git20260716-alpine-edge
        return list(dict.fromkeys(tags))

    line = line_key(version)

    # Explicit tags - always.
    tags.append(f"{line}-alpine-{av}")                # 22-alpine-3.24
    tags.append(f"{version}-alpine-{av}")             # 22.10.1-alpine-3.24

    # Implicit tags - stable tree only.
    if is_stable:
        tags.append(f"{line}-alpine")                 # 22-alpine
        tags.append(f"{version}-alpine")              # 22.10.1-alpine

    # LTS latest-owner aliases.
    if owns_latest:
        tags.append(f"stable-alpine-{av}")            # stable-alpine-3.24
        if is_stable:
            tags.append("alpine")                     # alpine  (the latest twin)
            tags.append("stable-alpine")              # stable-alpine

    return list(dict.fromkeys(tags))
