"""Unit tests for the Alpine sync resolver (plans/003-alpine-apk-images.md section 7).

Drives the pure logic in lib/alpine_sync.py against captured, real APKINDEX
fixtures (tests/fixtures/apkindex/*.tar.gz, probed 2026-07-17 from Cloudsmith):

  v3.24 x86_64 : 23.4.1 22.10.1 22.8.0.3 20.20.1 1.8.32.3 1.6.2.24
  v3.24 aarch64: 23.4.1 22.10.1 22.8.0.3 20.20.1
  v3.24 armv7  : (empty - mid-backfill)
  edge  x86_64 : 24.0.0_git20260716 23.4.1 22.10.1
  edge  aarch64: 24.0.0_git20260716 23.4.1 22.10.1

The network fetch lives in scripts/alpine-sync.py; here the parsed indexes are
injected, so the resolver is exercised with zero I/O.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import alpine_sync as A  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "apkindex")


def _load(name):
    with open(os.path.join(FIXTURES, f"{name}.tar.gz"), "rb") as f:
        return A.parse_apkindex(f.read())


def live_indexes():
    """The real live picture from the captured fixtures."""
    return {
        "v3.24": {
            "x86_64": _load("v3.24-x86_64"),
            "aarch64": _load("v3.24-aarch64"),
            "armv7": _load("v3.24-armv7"),
        },
        "edge": {
            "x86_64": _load("edge-x86_64"),
            "aarch64": _load("edge-aarch64"),
        },
    }


# The version labels the matrix carries today (subset that matters for Alpine).
MATRIX_VERSIONS = [
    {"version": "23.4.1", "active": True},
    {"version": "22.10.1", "active": True},
    {"version": "22.8-cert3", "active": True},
    {"version": "20.20.1", "active": True},
    {"version": "18.26.4", "active": True},
    {"version": "16.30.1", "active": True},
    {"version": "1.8.32.3", "active": True},
    {"version": "1.6.2.24", "active": True},
    {"version": "git", "active": True},
]


class TestParseApkindex:
    def test_extracts_asterisk_main_versions(self):
        recs = _load("v3.24-x86_64")
        mains = {r["version"] for r in recs if r["name"] == "asterisk"}
        assert "22.10.1-r0" in mains
        assert "22.8.0.3-r0" in mains
        assert "1.6.2.24-r0" in mains

    def test_records_carry_arch(self):
        recs = _load("v3.24-aarch64")
        assert recs, "index should not be empty"
        # arch-specific packages carry the index arch; noarch subpackages
        # (sounds-*, sample-config, doc) ride every arch's index as "noarch".
        assert all(r["arch"] in ("aarch64", "noarch") for r in recs)
        assert next(r for r in recs if r["name"] == "asterisk")["arch"] == "aarch64"

    def test_empty_index_parses_to_no_asterisk(self):
        recs = _load("v3.24-armv7")
        assert [r for r in recs if r["name"] == "asterisk"] == []

    def test_subpackages_present(self):
        recs = _load("v3.24-x86_64")
        subs = {r["name"] for r in recs if r["name"].startswith("asterisk-")
                and r["version"] == "22.10.1-r0"}
        assert "asterisk-opus" in subs
        assert "asterisk-sample-config" in subs


class TestTreeDistribution:
    def test_stable_tree_to_distribution(self):
        assert A.tree_to_distribution("v3.24") == "3.24"

    def test_edge_tree_to_distribution(self):
        assert A.tree_to_distribution("edge") == "edge"

    def test_roundtrip_matches_generator(self):
        # distribution_to_tree must mirror lib.template_generator.alpine_tree
        assert A.distribution_to_tree("3.24") == "v3.24"
        assert A.distribution_to_tree("edge") == "edge"


class TestResolvePkgver:
    def test_identity_mapping(self):
        pkgvers = {"22.10.1-r0", "23.4.1-r0", "20.20.1-r0"}
        assert A.resolve_pkgver("22.10.1", pkgvers) == "22.10.1-r0"

    def test_identity_no_partial_match(self):
        pkgvers = {"22.10.11-r0", "22.10.1-r0"}
        assert A.resolve_pkgver("22.10.1", pkgvers) == "22.10.1-r0"

    def test_cert_label_maps_to_four_component(self):
        pkgvers = {"22.8.0.3-r0", "22.10.1-r0"}
        assert A.resolve_pkgver("22.8-cert3", pkgvers) == "22.8.0.3-r0"

    def test_git_label_picks_newest_snapshot(self):
        pkgvers = {"24.0.0_git20260716-r0", "24.0.0_git20260701-r0", "23.4.1-r0"}
        assert A.resolve_pkgver("git", pkgvers) == "24.0.0_git20260716-r0"

    def test_missing_returns_none(self):
        assert A.resolve_pkgver("99.9.9", {"22.10.1-r0"}) is None

    def test_picks_highest_revision_when_multiple_pkgrels(self):
        # Sibling re-publishes rebuilds as -r1, -r2, ...; the resolver must
        # take the newest revision deterministically, not whatever a set
        # iteration happened to yield (PYTHONHASHSEED made it random).
        pkgvers = {"1.6.2.24-r0", "1.6.2.24-r1"}
        assert A.resolve_pkgver("1.6.2.24", pkgvers) == "1.6.2.24-r1"

    def test_picks_highest_revision_across_three_pkgrels(self):
        pkgvers = {"20.20.1-r2", "20.20.1-r0", "20.20.1-r1"}
        assert A.resolve_pkgver("20.20.1", pkgvers) == "20.20.1-r2"


class TestDeriveRoles:
    def test_single_stable_and_edge(self):
        roles = A.derive_roles(["v3.24", "edge"])
        assert roles["v3.24"] == "stable"
        assert roles["edge"] == "edge"

    def test_highest_stable_lower_previous(self):
        roles = A.derive_roles(["v3.24", "v3.25", "edge"])
        assert roles["v3.25"] == "stable"
        assert roles["v3.24"] == "previous"
        assert roles["edge"] == "edge"


class TestResolveMembersLive:
    def setup_method(self):
        self.members, self.drift = A.resolve_alpine_members(
            versions=MATRIX_VERSIONS, indexes=live_indexes())

    def _member(self, version, dist):
        for m in self.members.get(version, []):
            if m["distribution"] == dist:
                return m
        return None

    def test_stable_member_shape(self):
        m = self._member("22.10.1", "3.24")
        assert m is not None
        assert m["os"] == "alpine"
        assert m["alpine_tree"] == "v3.24"
        assert m["alpine_role"] == "stable"
        assert m["apk_version"] == "22.10.1-r0"
        assert m["architectures"] == ["amd64", "arm64"]

    def test_edge_member_for_multi_tree_version(self):
        m = self._member("22.10.1", "edge")
        assert m is not None
        assert m["alpine_role"] == "edge"
        assert m["apk_version"] == "22.10.1-r0"

    def test_cert_apk_version_and_subpackage_omissions(self):
        m = self._member("22.8-cert3", "3.24")
        assert m is not None
        assert m["apk_version"] == "22.8.0.3-r0"
        # cert line ships opus/srtp but omits ldap/pgsql/prometheus/tds
        assert "opus" in m["apk_packages"]
        assert "srtp" in m["apk_packages"]
        for absent in ("ldap", "pgsql", "prometheus", "tds"):
            assert absent not in m["apk_packages"]

    def test_subpackages_are_desired_intersect_available_ordered(self):
        m = self._member("22.10.1", "3.24")
        # desired order preserved, only desired names, all available for 22.10.1
        assert m["apk_packages"] == [
            "opus", "srtp", "curl", "speex", "fax", "odbc",
            "ldap", "pgsql", "prometheus", "mobile", "tds"]

    def test_git_only_on_edge_with_snapshot_pin(self):
        assert self._member("git", "3.24") is None
        m = self._member("git", "edge")
        assert m is not None
        assert m["alpine_role"] == "edge"
        assert m["apk_version"] == "24.0.0_git20260716-r0"

    def test_git_edge_omits_unavailable_opus(self):
        # the edge git snapshot has no asterisk-opus subpackage
        m = self._member("git", "edge")
        assert "opus" not in m["apk_packages"]
        assert "srtp" in m["apk_packages"]

    def test_arch_resolved_from_index_amd64_only(self):
        # 1.6/1.8 publish on v3.24 x86_64 only -> amd64 alone
        m = self._member("1.6.2.24", "3.24")
        assert m is not None
        assert m["architectures"] == ["amd64"]

    def test_drift_lists_active_versions_without_apk(self):
        assert set(self.drift["no_apk"]) == {"16.30.1", "18.26.4"}

    def test_drift_floor_suppresses_ancient_legacy(self):
        # a floor drops unpublished 1.x-15.x from the report but never gates
        # what is built (1.6/1.8 still get members from the live index).
        versions = MATRIX_VERSIONS + [
            {"version": "10.12.4", "active": True},
            {"version": "13.38.3", "active": True},
        ]
        members, drift = A.resolve_alpine_members(
            versions=versions, indexes=live_indexes(), drift_major_floor=16)
        assert "10.12.4" not in drift["no_apk"]
        assert "13.38.3" not in drift["no_apk"]
        assert set(drift["no_apk"]) == {"16.30.1", "18.26.4"}
        # decision #2 intact: 1.6/1.8 still built from the index
        assert members.get("1.6.2.24")
        assert members.get("1.8.32.3")

    def test_no_member_for_absent_line(self):
        assert self._member("16.30.1", "3.24") is None
        assert self._member("18.26.4", "3.24") is None


class TestPerLineDedup:
    """At most one alpine member per (line, tree): the newest pkgver wins."""

    def _synthetic_index(self, pkgvers):
        # minimal records: an asterisk main + a couple of subpackages per pkgver
        recs = []
        for v in pkgvers:
            recs.append({"name": "asterisk", "version": v, "arch": "x86_64"})
            recs.append({"name": "asterisk-opus", "version": v, "arch": "x86_64"})
            recs.append({"name": "asterisk-srtp", "version": v, "arch": "x86_64"})
        return recs

    def test_newest_patch_owns_the_line(self):
        indexes = {"v3.24": {"x86_64": self._synthetic_index(
            ["22.10.1-r0", "22.11.0-r0"])}}
        versions = [
            {"version": "22.10.1", "active": False},   # deprecated but apk live
            {"version": "22.11.0", "active": True},
        ]
        members, _ = A.resolve_alpine_members(versions=versions, indexes=indexes)
        # only the newest (22.11.0) keeps a stable member on v3.24
        assert members.get("22.11.0")
        assert members["22.11.0"][0]["apk_version"] == "22.11.0-r0"
        assert not members.get("22.10.1")


class TestArchMapping:
    def test_canonical_names(self):
        assert A.ARCH_MAP == {
            "x86_64": "amd64", "aarch64": "arm64",
            "armv7": "armv7", "armhf": "armhf"}
