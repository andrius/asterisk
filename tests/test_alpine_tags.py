"""Unit tests for the Alpine tag lattice (plans/003-alpine-apk-images.md section 6)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from alpine_tags import alpine_tags  # noqa: E402


class TestStableLtsOwner:
    """22.10.1 on the stable 3.24 tree, owning latest/stable."""

    def _tags(self):
        return set(alpine_tags(
            version="22.10.1", apk_version="22.10.1-r0",
            alpine_version="3.24", alpine_role="stable", owns_latest=True))

    def test_explicit_line_and_version(self):
        t = self._tags()
        assert "22-alpine-3.24" in t
        assert "22.10.1-alpine-3.24" in t

    def test_implicit_line_and_version(self):
        t = self._tags()
        assert "22-alpine" in t
        assert "22.10.1-alpine" in t

    def test_latest_owner_aliases(self):
        t = self._tags()
        assert {"alpine", "stable-alpine", "stable-alpine-3.24"} <= t

    def test_no_debian_or_git_tags(self):
        t = self._tags()
        assert not any("debian" in x for x in t)
        assert not any(x.startswith("git") for x in t)


class TestStableNonOwner:
    """20.20.1 on stable 3.24 - a plain LTS line, not the latest-owner."""

    def _tags(self):
        return set(alpine_tags(
            version="20.20.1", apk_version="20.20.1-r0",
            alpine_version="3.24", alpine_role="stable", owns_latest=False))

    def test_line_and_version_tags_present(self):
        t = self._tags()
        assert {"20-alpine", "20-alpine-3.24", "20.20.1-alpine", "20.20.1-alpine-3.24"} <= t

    def test_no_latest_aliases(self):
        t = self._tags()
        assert "alpine" not in t
        assert "stable-alpine" not in t
        assert "stable-alpine-3.24" not in t


class TestCertLine:
    """22.8-cert3 -> line token 22-cert; never owns latest."""

    def _tags(self):
        return set(alpine_tags(
            version="22.8-cert3", apk_version="22.8.0.3-r0",
            alpine_version="3.24", alpine_role="stable", owns_latest=False))

    def test_cert_line_and_full_label(self):
        t = self._tags()
        assert {"22-cert-alpine", "22-cert-alpine-3.24",
                "22.8-cert3-alpine", "22.8-cert3-alpine-3.24"} <= t

    def test_no_bare_alpine(self):
        assert "alpine" not in self._tags()


class TestEdgeIsExplicitOnly:
    """A release line on edge gets only explicit -alpine-edge tags."""

    def _tags(self):
        return set(alpine_tags(
            version="23.4.1", apk_version="23.4.1-r0",
            alpine_version="edge", alpine_role="edge", owns_latest=False))

    def test_explicit_edge_tags(self):
        t = self._tags()
        assert {"23-alpine-edge", "23.4.1-alpine-edge"} <= t

    def test_no_implicit_tags_from_edge(self):
        t = self._tags()
        assert "23-alpine" not in t
        assert "23.4.1-alpine" not in t


class TestPreviousStableIsExplicitOnly:
    """A demoted (previous) stable tree keeps only its explicit tags."""

    def test_previous_role_has_no_implicit_tags(self):
        t = set(alpine_tags(
            version="22.10.1", apk_version="22.10.1-r0",
            alpine_version="3.24", alpine_role="previous", owns_latest=True))
        assert "22-alpine-3.24" in t          # explicit still there
        assert "22-alpine" not in t           # implicit suppressed
        assert "alpine" not in t              # latest twin suppressed
        assert "stable-alpine-3.24" in t      # explicit latest alias stays


class TestGitLine:
    """git master snapshot on edge - always gets the bare channel tags."""

    def _tags(self):
        return set(alpine_tags(
            version="git", apk_version="24.0.0_git20260716-r0",
            alpine_version="edge", alpine_role="edge", owns_latest=False))

    def test_bare_channel_tags_always_minted(self):
        assert {"git-alpine", "testing-alpine", "dev-alpine"} <= self._tags()

    def test_explicit_channel_tags(self):
        assert {"git-alpine-edge", "testing-alpine-edge", "dev-alpine-edge"} <= self._tags()

    def test_immutable_snapshot_tag(self):
        assert "24.0.0_git20260716-alpine-edge" in self._tags()

    def test_no_numeric_line_tag(self):
        # line_key("git") would be "999" - must not leak into tags.
        assert not any("999" in x for x in self._tags())


class TestDeterminism:
    def test_output_is_deduplicated(self):
        tags = alpine_tags(
            version="22.10.1", apk_version="22.10.1-r0",
            alpine_version="3.24", alpine_role="stable", owns_latest=True)
        assert len(tags) == len(set(tags))
