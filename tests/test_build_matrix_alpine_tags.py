"""Local build path emits the Alpine tag lattice, not the version-level tags.

Regression test for the tag-lattice inheritance gap in build-asterisk.sh's
embedded get_build_matrix(): before the fix an Alpine build leg inherited the
Debian/semantic version-level tags (latest, stable, 22, bare 22.10.1) and, on
--push, collided with the Debian image for those tags. The CI matrix generator
(.github/actions/generate-build-matrix) already REPLACES an Alpine member's
tags with lib/alpine_tags.py's lattice; this pins that the LOCAL path does the
same. Debian members honor per-member additional_tags overrides (forky's
'experimental'), while members without the key (trixie) keep the version-level
tags - matching the CI generator's line-128 behavior.

Style mirrors tests/test_golden_regeneration.py: build-asterisk.sh --dry-run
runs inside a throwaway git worktree so generated files are never written into
the developer's working tree. The working-tree copy of the script is staged
into the worktree first, so the test exercises uncommitted edits too.

The worktree's build matrix is replaced with a frozen snapshot
(tests/fixtures/build-matrix/): every release PR moves additional_tags and
deprecates the previous version, so assertions against the live matrix broke
on each release (PR #235).
"""

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

# Repo root is one level up from tests/ (this checkout is itself a worktree).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FROZEN_MATRIX = os.path.join(
    os.path.dirname(__file__), "fixtures", "build-matrix",
    "supported-asterisk-builds.yml",
)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# One "Build targets" line: "  -> os/distribution (archs) [additional_tags: T] [from: src]"
_TARGET = re.compile(
    r"→\s+(?P<os>\S+?)/(?P<dist>\S+?)\s+\([^)]*\).*?"
    r"\[additional_tags:\s*(?P<tags>[^\]]*)\]"
)

_CACHE = {}


@pytest.fixture(scope="module")
def worktree(tmp_path_factory):
    """A throwaway detached worktree of HEAD, carrying the working-tree script
    and the frozen build matrix."""
    wt = tmp_path_factory.mktemp("alpine_tags") / "wt"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(wt)],
        check=True, cwd=REPO_ROOT, capture_output=True, text=True,
    )
    # Exercise the working-tree script and the lib/ it imports (both may carry
    # uncommitted edits), not HEAD.
    shutil.copy2(
        os.path.join(REPO_ROOT, "scripts", "build-asterisk.sh"),
        os.path.join(str(wt), "scripts", "build-asterisk.sh"),
    )
    shutil.copytree(
        os.path.join(REPO_ROOT, "lib"), os.path.join(str(wt), "lib"),
        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy2(
        FROZEN_MATRIX,
        os.path.join(str(wt), "asterisk", "supported-asterisk-builds.yml"),
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

    def test_stable_owner_gets_only_the_stable_aliases(self, worktree):
        # Frozen 22.10.1 carries 'stable,22': 'stable-alpine*' follow stable.
        alpine_324 = set(_tags_by_leg(worktree, "22.10.1")[("alpine", "3.24")])
        assert {"stable-alpine", "stable-alpine-3.24"} <= alpine_324
        assert "alpine" not in alpine_324

    def test_latest_owner_gets_only_the_latest_twin(self, worktree):
        # Frozen 23.4.1 carries 'latest,23': 'alpine' follows latest.
        alpine_324 = set(_tags_by_leg(worktree, "23.4.1")[("alpine", "3.24")])
        assert "alpine" in alpine_324
        assert not {"stable-alpine", "stable-alpine-3.24"} & alpine_324

    def test_edge_leg_is_explicit_only(self, worktree):
        alpine_edge = _tags_by_leg(worktree, "22.10.1")[("alpine", "edge")]
        assert "22.10.1-alpine-edge" in alpine_edge
        # edge is not the stable tree: the implicit '22-alpine' must be absent.
        assert "22-alpine" not in alpine_edge


class TestDebianLegTags:
    """Debian legs: members without a per-member tag keep the version-level
    tags (trixie); members with one honor it (forky's 'experimental'), matching
    the CI generator's line-128 behavior."""

    def test_trixie_keeps_version_level_tags(self, worktree):
        assert _tags_by_leg(worktree, "22.10.1")[("debian", "trixie")] == [
            "stable", "22",
        ]

    def test_forky_adopts_its_experimental_tag(self, worktree):
        # The local path honors per-member additional_tags (parity with the CI
        # generator): 23.4.1's forky leg publishes its own 'experimental' tag
        # instead of inheriting the version-level 'latest,23', which would
        # collide with the trixie image. trixie has no per-member key, so it
        # keeps the version-level tags.
        legs = _tags_by_leg(worktree, "23.4.1")
        assert legs[("debian", "trixie")] == ["latest", "23"]
        assert legs[("debian", "forky")] == ["experimental"]
        # ...while the Alpine legs of the same version carry the lattice.
        assert "23.4.1-alpine-3.24" in legs[("alpine", "3.24")]


class TestDeprecatedVersionLegs:
    """Given a deprecated version, the local path keeps its Alpine members
    (they track the live apk) and skips its Debian members, matching the CI
    generator's deprecation-survival (generate-build-matrix 'deprecated')."""

    def test_only_alpine_legs_survive(self, worktree):
        legs = _tags_by_leg(worktree, "22.8-cert3")
        assert list(legs) == [("alpine", "3.24")]
        assert "22.8-cert3-alpine-3.24" in legs[("alpine", "3.24")]


def _ci_tags_by_leg(worktree):
    """Map (version, distribution) -> tags from the CI matrix generator.

    Runs the Python embedded in .github/actions/generate-build-matrix/action.yml
    (working-tree copy) against the throwaway worktree, which carries the
    frozen matrix and the working-tree lib/.
    """
    src = open(os.path.join(
        REPO_ROOT, ".github", "actions", "generate-build-matrix", "action.yml")).read()
    script = src.split("python3 << 'PYTHON_EOF'\n", 1)[1].split("        PYTHON_EOF", 1)[0]
    script = "\n".join(l[8:] if l.startswith("        ") else l for l in script.splitlines())
    for expr, value in {"${{ inputs.version-pattern }}": ".*",
                        "${{ inputs.batch-name }}": "pytest",
                        "${{ inputs.filter-version }}": "",
                        "${{ inputs.filter-distribution }}": ""}.items():
        script = script.replace(expr, value)
    assert "${{" not in script, "action.yml grew an input this test does not substitute"
    out = os.path.join(worktree, ".github-output")
    run = subprocess.run(
        [sys.executable, "-c", script], cwd=worktree, capture_output=True, text=True,
        env=dict(os.environ, GITHUB_OUTPUT=out),
    )
    assert run.returncode == 0, run.stderr[-2000:]
    matrix = json.loads(re.search(r"^matrix=(.*)$", open(out).read(), re.M).group(1))
    legs = matrix.get("include", matrix) if isinstance(matrix, dict) else matrix
    return {(leg["version"], leg["distribution"]):
            [t for t in (leg.get("additional_tags") or "").split(",") if t]
            for leg in legs}


class TestCiGeneratorParity:
    """The CI matrix generator and the local build path emit the same tags for
    every leg of the frozen matrix (owner flags, Alpine lattice, deprecation)."""

    def test_every_leg_matches_the_local_path(self, worktree):
        ci = _ci_tags_by_leg(worktree)
        local = {(version, dist): tags
                 for version in ("22.10.1", "22.8-cert3", "23.4.1")
                 for (_os, dist), tags in _tags_by_leg(worktree, version).items()}
        assert ci == local
