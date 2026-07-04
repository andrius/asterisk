import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from lib.tag_lifecycle import version_sort_key, is_cert, line_key


def test_version_sort_key_stable():
    assert version_sort_key("22.10.1") == (22, 10, 1, 0)
    assert version_sort_key("20.19.0") == (20, 19, 0, 0)
    assert version_sort_key("1.8.32.3") == (1, 8, 32, 0)


def test_version_sort_key_cert():
    assert version_sort_key("20.7-cert11") == (20, 7, 0, 11)
    assert version_sort_key("22.8-cert3") == (22, 8, 0, 3)


def test_version_sort_key_git_highest():
    assert version_sort_key("git") == (999, 0, 0, 0)
    assert version_sort_key("git-forky") == (999, 0, 0, 0)


def test_version_sort_key_orders_cert_numerically():
    assert version_sort_key("20.7-cert11") > version_sort_key("20.7-cert10")


def test_version_sort_key_raises_on_garbage():
    with pytest.raises(ValueError):
        version_sort_key("not-a-version")


def test_is_cert():
    assert is_cert("20.7-cert11") is True
    assert is_cert("22.10.1") is False


def test_line_key():
    assert line_key("22.10.1") == "22"
    assert line_key("23.4.1") == "23"
    assert line_key("20.7-cert11") == "20-cert"   # major only
    assert line_key("22.8-cert3") == "22-cert"
    assert line_key("1.8.32.3") == "1.8"          # legacy: major.minor
    assert line_key("1.2.40") == "1.2"
    assert line_key("10.12.4") == "10"


from lib.tag_lifecycle import plan, Plan


def _b(version, tags=None, os_matrix=True, deprecated_at=None):
    entry = {"version": version}
    if tags is not None:
        entry["additional_tags"] = tags
    if os_matrix:
        entry["os_matrix"] = [{"os": "debian", "distribution": "trixie",
                               "architectures": ["amd64", "arm64"]}]
    if deprecated_at:
        entry["deprecated_at"] = deprecated_at
    return entry


def test_set_tags_latest_stable_on_newest_even_lts():
    builds = [_b("22.9.0", "latest,stable,22"), _b("22.10.1"),
              _b("23.3.0", "23"), _b("23.4.1")]
    p = plan(builds)
    assert p.set_tags["22.10.1"] == "latest,stable,22"   # 22 = newest even LTS
    assert p.set_tags["23.4.1"] == "23"                  # 23 odd -> bare major only
    assert "22.9.0" not in p.set_tags
    assert "23.3.0" not in p.set_tags


def test_set_tags_bare_major_for_non_top_lts():
    builds = [_b("20.19.0", "20"), _b("20.20.1"), _b("22.10.1", "latest,stable,22")]
    p = plan(builds)
    assert p.set_tags["20.20.1"] == "20"                 # 20 even but < 22
    assert p.set_tags["22.10.1"] == "latest,stable,22"


def test_set_tags_cert_line_isolated():
    # 22 is the newest even LTS -> gets latest/stable; the 20 stable line gets
    # bare "20"; the 20-cert line gets "20-cert". Cert line never leaks into "20".
    builds = [_b("20.7-cert10", "20-cert"), _b("20.7-cert11"),
              _b("20.20.1", "20"), _b("22.10.1", "latest,stable,22")]
    p = plan(builds)
    assert p.set_tags["20.7-cert11"] == "20-cert"
    assert p.set_tags["20.20.1"] == "20"
    assert p.set_tags["22.10.1"] == "latest,stable,22"


def test_lts_major_with_cert_counterpart_still_gets_latest_stable():
    # Real-data shape: the LTS major (22) has BOTH a stable line and a cert line.
    # latest/stable must ride the stable line; the cert counterpart must not
    # suppress it. (Regression guard: an earlier impl wrongly excluded any major
    # that had a cert line, which pushed latest/stable onto an ancient even major.)
    builds = [_b("22.10.1"), _b("22.8-cert3", "22-cert"),
              _b("20.20.1", "20"), _b("20.7-cert11", "20-cert")]
    p = plan(builds)
    assert p.set_tags["22.10.1"] == "latest,stable,22"
    assert p.set_tags["22.8-cert3"] == "22-cert"
    assert p.set_tags["20.20.1"] == "20"


def test_set_tags_git_ignored():
    builds = [{"version": "git", "additional_tags": "testing,dev",
               "os_matrix": [{"distribution": "trixie", "architectures": ["amd64"]}]},
              _b("22.10.1")]
    p = plan(builds)
    assert "git" not in p.set_tags


def test_set_tags_legacy_lines_separate():
    builds = [_b("1.2.40", "1.2"), _b("1.8.32.3", "1.8"), _b("22.10.1")]
    p = plan(builds)
    assert p.set_tags["1.2.40"] == "1.2"
    assert p.set_tags["1.8.32.3"] == "1.8"


def test_set_tags_skips_deprecated_and_unparseable():
    builds = [_b("22.9.0", "latest,stable,22", deprecated_at="2026-05-04T07:22:53Z"),
              _b("22.10.1"), _b("garbage")]
    p = plan(builds)
    assert p.set_tags["22.10.1"] == "latest,stable,22"
    assert "garbage" not in p.set_tags
