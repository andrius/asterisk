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
