#!/usr/bin/env python3
# scripts/apply-tag-lifecycle.py
"""Apply tag-lifecycle plan to supported-asterisk-builds.yml.

Phases:
  pr        - move tags, set superseded_by (no deprecated_at), migrate experimental
  finalize  - stamp deprecated_at on entries pending deprecation (Task 5)
Round-trips YAML with ruamel to preserve comments/order/quotes.
"""
from __future__ import annotations

import argparse
import copy
import io
import os
import sys
from datetime import datetime, timezone

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.tag_lifecycle import plan  # noqa: E402

DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "..",
                            "asterisk", "supported-asterisk-builds.yml")


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096  # avoid line-wrapping long values
    # Match the repo's indented block-sequence style (dash indented under its
    # key) so a no-op round-trip of supported-asterisk-builds.yml is
    # byte-stable and real edits produce minimal PR diffs.
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _by_version(data):
    return {b["version"]: b for b in data["latest_builds"]}


def apply_pr(data):
    builds = list(data["latest_builds"])
    p = plan(builds)
    index = _by_version(data)

    for ver, tags in p.set_tags.items():
        index[ver]["additional_tags"] = DoubleQuotedScalarString(tags)
    for ver in p.clear_tags:
        index[ver].pop("additional_tags", None)
    for ver, superseded_by in p.deprecate.items():
        index[ver]["superseded_by"] = DoubleQuotedScalarString(superseded_by)
    for new_ver, members in p.migrate_experimental.items():
        target = index[new_ver].setdefault("os_matrix", [])
        for member in members:
            target.append(copy.deepcopy(member))


def finalize(data, now_iso):
    stamped = []
    for b in data["latest_builds"]:
        if b.get("superseded_by") and not b.get("deprecated_at"):
            b["deprecated_at"] = DoubleQuotedScalarString(now_iso)
            stamped.append(b["version"])
    return stamped


def _render(y, data):
    buf = io.StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["pr", "finalize"])
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    y = _yaml()
    with open(args.file) as fh:
        original = fh.read()
    data = y.load(original)

    if args.phase == "pr":
        apply_pr(data)
    else:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"finalized: {finalize(data, now_iso)}")

    rendered = _render(y, data)
    if args.check:
        changed = rendered != original
        if changed:
            print("DRIFT: supported-asterisk-builds.yml is not in desired state")
        return 1 if changed else 0
    if args.dry_run:
        print(rendered)
        return 0
    with open(args.file, "w") as fh:
        fh.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
