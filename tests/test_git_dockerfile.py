"""Regression test for the daily Debian git build (build-git-daily.yml).

Symptom (regressed around 2026-07-27): the "Generate Dockerfile" step crashed
with ``Error: list object has no element 1``. Root cause: version ``git``
resolved to the ``modern`` variant, so the generated config lost
``source_type: git`` / ``git_repository``; the Dockerfile generator then picked
``multi-stage.dockerfile.j2`` whose ``version.split('.')[1]`` blew up on the
non-numeric ``git`` version. The ``git-dev`` variant must be selected instead,
yielding a git-clone Dockerfile (no release tarball) and a materialized
``GIT_SHA`` build arg read from the matrix metadata.
"""

import os
import sys

import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from template_generator import DRYTemplateGenerator  # noqa: E402
from dockerfile_generator import DockerfileGenerator  # noqa: E402

TEMPLATES = os.path.join(ROOT, "templates")
DOCKERFILE_TEMPLATES = os.path.join(ROOT, "templates", "dockerfile")

GIT_SHA = "7c60726"
GIT_REPO = "https://github.com/asterisk/asterisk.git"


def _write_matrix(tmp_path, with_sha=True):
    """Generator seeded with a Debian git matrix entry (+ optional git_sha)."""
    meta = {"mode": "manual"}
    if with_sha:
        meta["git_sha"] = GIT_SHA
    builds = {
        "latest_builds": [{
            "version": "git",
            "os_matrix": [
                {"os": "debian", "distribution": "trixie", "template": "git-dev"},
            ],
        }],
        "metadata": meta,
    }
    p = tmp_path / "supported-asterisk-builds.yml"
    with open(p, "w") as f:
        yaml.dump(builds, f)
    gen = DRYTemplateGenerator(TEMPLATES)
    gen.supported_builds_file = str(p)
    return gen


class TestVariantSelection:
    def test_git_version_picks_git_dev_for_debian(self):
        gen = DRYTemplateGenerator(TEMPLATES)
        assert gen._determine_variant("git", "debian") == "git-dev"
        assert gen._determine_variant("git-abc123", "debian") == "git-dev"

    def test_alpine_git_keeps_modern_variant(self):
        # Alpine git consumes prebuilt apks via its own template; it must not
        # flip to git-dev (which would pull in the git-clone Debian template).
        gen = DRYTemplateGenerator(TEMPLATES)
        assert gen._determine_variant("git", "alpine") == "modern"

    def test_release_versions_unchanged(self):
        gen = DRYTemplateGenerator(TEMPLATES)
        assert gen._determine_variant("22.10.1", "debian") == "modern"
        assert gen._determine_variant("1.4.44", "debian") == "legacy-addons"


class TestGitConfig:
    def test_carries_git_source_and_materialized_sha(self, tmp_path):
        cfg = _write_matrix(tmp_path).generate_config("git", "trixie")
        assert cfg["asterisk"]["source_type"] == "git"
        assert cfg["asterisk"]["git_repository"] == GIT_REPO
        # {{GIT_SHA}} is materialized from matrix metadata into the build args.
        assert cfg["build"]["args"]["GIT_SHA"] == GIT_SHA
        assert cfg["build"]["args"]["ASTERISK_VERSION"] == f"git-{GIT_SHA}"

    def test_sha_falls_back_to_unknown_when_missing(self, tmp_path):
        cfg = _write_matrix(tmp_path, with_sha=False).generate_config("git", "trixie")
        # No crash; placeholder resolves to "unknown".
        assert cfg["build"]["args"]["GIT_SHA"] == "unknown"
        assert cfg["asterisk"]["source_type"] == "git"


class TestGitDockerfileRender:
    def _render(self, tmp_path):
        cfg = _write_matrix(tmp_path).generate_config("git", "trixie")
        cfg_path = tmp_path / "cfg.yml"
        with open(cfg_path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False)
        # No schema: version "git" does not match the release-version pattern.
        # scripts/generate-dockerfile.py's default --schema path resolves
        # outside the repo, so CI likewise renders git configs unvalidated.
        gen = DockerfileGenerator(DOCKERFILE_TEMPLATES, None)
        return gen.generate_dockerfile(str(cfg_path), format_dockerfile=False)

    def test_renders_git_clone_not_release_tarball(self, tmp_path):
        df = self._render(tmp_path)
        # The git-dev template clones from the repository...
        assert "git clone --depth 1 " + GIT_REPO in df
        assert "asterisk-builder" in df  # multi-stage build stage
        # ...and must NOT fetch a release tarball (the modern path).
        assert "releases/asterisk-" not in df
        assert ".tar.gz" not in df

    def test_dockerfile_carries_git_sha(self, tmp_path):
        df = self._render(tmp_path)
        assert "git-" + GIT_SHA in df
