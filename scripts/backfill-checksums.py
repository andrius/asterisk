#!/usr/bin/env python3
"""Backfill tarball_sha256 / addons_sha256 into supported-asterisk-builds.yml.

For every active (os_matrix-bearing, non-deprecated) entry that lacks a
checksum, resolve the source/addons URL, try the upstream `.sha256` file
(preferred - same-origin corroboration), and fall back to downloading the
tarball and computing the sha256 (TOFU) for the legacy tail that has no
upstream checksum file. Writes the result back via ruamel round-trip so
the YAML stays byte-stable (reuses the indent/quote settings from
apply-tag-lifecycle.py).

This is a maintenance tool: run once to seed existing entries (plan 002,
task 4). New versions get their checksum at discovery time
(discover-latest-versions.sh), not via this script.

Usage:
    scripts/backfill-checksums.py                 # backfill all active entries
    scripts/backfill-checksums.py --dry-run       # show what would change
    scripts/backfill-checksums.py --version 1.4.44
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
import tempfile
import urllib.request
from typing import Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "..",
                            "asterisk", "supported-asterisk-builds.yml")

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _yaml() -> YAML:
    """ruamel settings matching apply-tag-lifecycle._yaml() for byte-stable round-trips."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _source_url(version: str) -> str:
    """Resolve the source tarball URL for a version (mirrors the generator/template defaults)."""
    if "-cert" in version:
        return f"https://downloads.asterisk.org/pub/telephony/certified-asterisk/releases/asterisk-certified-{version}.tar.gz"
    return f"https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-{version}.tar.gz"


def _addons_url(addons_version: str) -> str:
    return f"https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-addons-{addons_version}.tar.gz"


def _http_get(url: str, timeout: int = 60) -> Tuple[int, bytes]:
    """GET url, return (status_code, body). Treats non-2xx as the status code."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "asterisk-backfill-checksums/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except urllib.error.URLError as e:
        # File not found is reported as URLError by some stacks; surface a 404-ish code
        return (404 if "404" in str(e) else 0), b""


def _parse_sha256_file(body: bytes, expected_filename: str) -> Optional[str]:
    """Parse a `sha256sum`-format file, validating the filename field matches."""
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    # Standard format: "<64 hex>  <filename>" (two spaces) - allow any whitespace.
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and SHA256_RE.match(parts[0]):
            digest, fname = parts[0], parts[1].strip().strip("*")
            if fname == expected_filename:
                return digest
    return None


def _download_and_hash(url: str, timeout: int = 120) -> Optional[str]:
    """TOFU fallback: download the tarball and compute its sha256."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "asterisk-backfill-checksums/1.0"})
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def resolve_checksum(tarball_url: str) -> Tuple[Optional[str], str]:
    """Resolve a sha256 for a tarball URL.

    Tries `<url minus .tar.gz>.sha256` first; falls back to downloading
    and hashing. Returns (digest, source) where source is one of
    'upstream-sha256', 'tofu-download', or 'unresolved'.
    """
    filename = os.path.basename(tarball_url)
    sha_url = tarball_url[: -len(".tar.gz")] + ".sha256"
    code, body = _http_get(sha_url)
    if code == 200 and body:
        digest = _parse_sha256_file(body, filename)
        if digest:
            return digest, "upstream-sha256"
    digest = _download_and_hash(tarball_url)
    if digest:
        return digest, "tofu-download"
    return None, "unresolved"


def _addons_version(version: str) -> Optional[str]:
    """Mirror DRYTemplateGenerator._get_addons_version (legacy-addons variants only)."""
    mapping = {"1.2": "1.2.9", "1.4": "1.4.9", "1.6": "1.6.2.4"}
    major_minor = ".".join(version.split(".")[:2])
    return mapping.get(major_minor)


def backfill(data, only_version: Optional[str] = None, dry_run: bool = False) -> list:
    """Mutate `data` (a ruamel-loaded supported-asterisk-builds.yml) in place.

    Returns a list of (version, field, digest, source) tuples for reporting.
    """
    results = []
    # Legacy-addons variants are 1.2.x/1.4.x/1.6.x (see template_generator._determine_variant).
    for build in data.get("latest_builds", []):
        version = build.get("version")
        if not version or version == "git" or version.startswith("git-"):
            continue
        # Only active (os_matrix-bearing) entries are buildable; skip disabled/deprecated.
        if "os_matrix" not in build:
            continue
        if build.get("deprecated_at"):
            continue
        if only_version and version != only_version:
            continue

        # Source tarball checksum.
        if not build.get("tarball_sha256"):
            digest, source = resolve_checksum(_source_url(version))
            if digest:
                build["tarball_sha256"] = DoubleQuotedScalarString(digest)
                results.append((version, "tarball_sha256", digest, source))
            else:
                results.append((version, "tarball_sha256", None, "unresolved"))

        # Addons checksum (legacy-addons variants only).
        addons_version = _addons_version(version)
        if addons_version and not build.get("addons_sha256"):
            digest, source = resolve_checksum(_addons_url(addons_version))
            if digest:
                build["addons_sha256"] = DoubleQuotedScalarString(digest)
                results.append((version, "addons_sha256", digest, source))
            else:
                results.append((version, "addons_sha256", None, "unresolved"))

    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--version", help="backfill a single version only")
    ap.add_argument("--dry-run", action="store_true", help="report only; do not write")
    args = ap.parse_args(argv)

    y = _yaml()
    with open(args.file) as fh:
        data = y.load(fh.read())

    results = backfill(data, only_version=args.version, dry_run=args.dry_run)

    if not results:
        print("nothing to backfill (all active entries already have checksums)")
        return 0

    unresolved = 0
    print(f"{'version':<14} {'field':<16} {'source':<18} digest")
    print("-" * 80)
    for version, field, digest, source in results:
        if digest is None:
            unresolved += 1
            print(f"{version:<14} {field:<16} {source:<18} (none)")
        else:
            print(f"{version:<14} {field:<16} {source:<18} {digest[:16]}...")

    if args.dry_run:
        print(f"\n[dry-run] {len(results)} resolution(s), {unresolved} unresolved; no changes written.")
        return 0 if unresolved == 0 else 1

    buf = io.StringIO()
    y.dump(data, buf)
    with open(args.file, "w") as fh:
        fh.write(buf.getvalue())

    print(f"\nwrote {len(results)} checksum(s) to {args.file} ({unresolved} unresolved).")
    return 0 if unresolved == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
