"""Local build path emits the Alpine tag lattice, not the version-level tags.

Regression test for the tag-lattice inheritance gap in build-asterisk.sh's
embedded get_build_matrix(): before the fix an Alpine build leg inherited the
Debian/semantic version-level tags (latest, stable, 22, bare 22.10.1) and, on
--push, collided with the Debian image for those tags. The CI matrix generator
(.github/actions/generate-build-matrix) already REPLACES an Alpine member's
tags with lib/alpine_tags.py's lattice; this pins that the LOCAL path does the
same, while Debian members keep their version-level tags byte-for-byte.

Style mirrors tests/test_golden_regeneration.py: build-asterisk.sh --dry-run
runs inside a throwaway git worktree so generated files are never written into
the developer's working tree. The working-tree copy of the script is staged
into the worktree first, so the test exercises uncommitted edits too.
"""

import os
import re
import shutil
import subprocess

import pytest

# Repo root is one level up from tests/ (this checkout is itself a worktree).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# One "Build targets" line: "  -> os/distribution (archs) [additional_tags: T] [from: src]"
_TARGET = re.compile(
    r"→\s+(?P<os>\S+?)/(?P<dist>\S+?)\s+\([^)]*\).*?"
    r"\[additional_tags:\s*(?P<tags>[^\]]*)\]"
)

_CACHE = {}


@pytest.fixture(scope="module")
def worktree(tmp_path_factory):
    """A throwaway detached worktree of HEAD, carrying the working-tree script."""
    wt = tmp_path_factory.mktemp("alpine_tags") / "wt"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(wt)],
        check=True, cwd=REPO_ROOT, capture_output=True, text=True,
    )
    # Exercise the working-tree script (may carry uncommitted edits), not HEAD.
    shutil.copy2(
        os.path.join(REPO_ROOT, "scripts", "build-asterisk.sh"),
        os.path.join(str(wt), "scripts", "build-asterisk.sh"),
    )
    yield str(wt)
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(wt)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


def _tags_by_leg(worktree, version):
    """Map (os, distribution) -> emitted additional_tags list for a --dry-run."""
    if version in _CACHE:
        return _CACHE[version]
    run = subprocess.run(
        ["./scripts/build-asterisk.sh", version, "--dry-run", "--skip-format-dockerfile"],
        cwd=worktree, capture_output=True, text=True,
    )
    assert run.returncode == 0, (
        f"{version}: dry-run failed (rc={run.returncode})\n"
        f"stderr:\n{run.stderr[-2000:]}"
    )
    legs = {}
    for line in _ANSI.sub("", run.stdout).splitlines():
        m = _TARGET.search(line)
        if m:
            legs[(m.group("os"), m.group("dist"))] = [
                t for t in m.group("tags").split(",") if t
            ]
    _CACHE[version] = legs
    return legs


class TestAlpineLegEmitsLattice:
    """Given an Alpine leg of 22.10.1, it publishes the suffixed tag lattice."""

    def test_stable_leg_carries_suffixed_lattice_not_bare_tags(self, worktree):
        alpine_324 = _tags_by_leg(worktree, "22.10.1")[("alpine", "3.24")]

        # Suffixed lattice is present: implicit line tag + explicit version tag.
        assert "22-alpine" in alpine_324
        assert "22.10.1-alpine-3.24" in alpine_324

        # The inherited Debian/semantic bare tags must NOT leak in. Token-exact
        # membership, so 'stable-alpine' never false-positives a bare 'stable'.
        for bare in ("latest", "stable", "22", "22.10.1"):
            assert bare not in alpine_324, f"bare {bare!r} leaked into {alpine_324}"

    def test_edge_leg_is_explicit_only(self, worktree):
        alpine_edge = _tags_by_leg(worktree, "22.10.1")[("alpine", "edge")]
        assert "22.10.1-alpine-edge" in alpine_edge
        # edge is not the stable tree: the implicit '22-alpine' must be absent.
        assert "22-alpine" not in alpine_edge


class TestDebianLegKeepsVersionTags:
    """Debian legs are untouched by the Alpine fix (tags stay byte-identical)."""

    def test_trixie_keeps_version_level_tags(self, worktree):
        assert _tags_by_leg(worktree, "22.10.1")[("debian", "trixie")] == [
            "latest", "stable", "22",
        ]

    def test_forky_leg_unchanged_and_alpine_still_lattice(self, worktree):
        # Guards the design trap: the local path must NOT adopt per-member tags,
        # so 23.4.1's forky leg stays '23' (its member-level 'experimental' tag
        # is a pre-existing, separate concern - out of scope for this fix).
        legs = _tags_by_leg(worktree, "23.4.1")
        assert legs[("debian", "trixie")] == ["23"]
        assert legs[("debian", "forky")] == ["23"]
        # ...while the Alpine legs of the same version carry the lattice.
        assert "23.4.1-alpine-3.24" in legs[("alpine", "3.24")]
