#!/usr/bin/env python3
"""Pre-build availability gate for Alpine apk images.

Reads the generated Alpine config for a (version, distribution), resolves the
Cloudsmith arch segment for our matrix arch name, fetches that arch's
APKINDEX.tar.gz, and checks that ``asterisk``, ``asterisk-sample-config`` and
every selected ``asterisk-<sub>`` subpackage is present at exactly
``apk_version``.

Why: the sibling repo (andrius/asterisk-alpine) publishes the main package and
its subpackages in one batch; under transient failure the main can be live on an
arch before every subpackage at the same pkgver is (andrius/asterisk-alpine#39).
The consumer pins the exact version (subpackages carry no ``depend: asterisk``),
so a partial set is unsatisfiable. Rather than fail a multi-arch manifest for
that, the calling workflow skips THIS arch and retries it next sync.

Exit codes (consumed by .github/workflows/build-single-image.yml):
  0 - every pinned package is published for this arch; proceed to build.
  2 - some pinned package is missing; skip this arch gracefully.
  1 - hard error (bad config, unknown arch, network/parse failure); fail the leg.

Pure availability logic lives in lib/alpine_sync.py (install_names +
missing_pinned_packages); this script is the I/O wrapper, mirroring the fetch()
style of scripts/alpine-sync.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

import yaml

sys.path.insert(0, "lib")
import alpine_sync as A  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", required=True,
                   help="generated alpine config yml (configs/generated/asterisk-<v>-alpine-<dist>.yml)")
    p.add_argument("--arch", required=True,
                   help="our matrix arch name (amd64/arm64/armv7/armhf)")
    args = p.parse_args(argv)

    cloud_arch = A.MATRIX_TO_CLOUD.get(args.arch)
    if cloud_arch is None:
        print(f"hard error: unknown matrix arch {args.arch!r}", file=sys.stderr)
        return 1

    try:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
        alpine = cfg["alpine"]
        apk_version = alpine["apk_version"]
        repo_url = alpine["repo_url"].rstrip("/")
        names = A.install_names(alpine.get("apk_packages", []))
    except (OSError, KeyError, TypeError, yaml.YAMLError) as e:
        print(f"hard error reading config {args.config}: {e}", file=sys.stderr)
        return 1

    url = f"{repo_url}/{cloud_arch}/APKINDEX.tar.gz"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            records = A.parse_apkindex(resp.read())
    except urllib.error.HTTPError as e:
        print(f"hard error: index not reachable for {args.arch}: "
              f"HTTP {e.code} {url}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as e:
        print(f"hard error fetching {url}: {e}", file=sys.stderr)
        return 1

    missing = A.missing_pinned_packages(records, apk_version, names)
    if not missing:
        print(f"ok: all {len(names)} pinned packages present at {apk_version} "
              f"for {args.arch}")
        return 0

    # exit 2 = "skip this arch", not a hard failure. Emit JSON the workflow can
    # surface in the build summary.
    print(json.dumps({
        "arch": args.arch, "apk_version": apk_version, "missing": missing}))
    return 2


if __name__ == "__main__":
    sys.exit(main())
