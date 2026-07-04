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


def _b_forky(version, tags=None):
    entry = _b(version, tags)
    entry["os_matrix"].append({"os": "debian", "distribution": "forky",
                               "architectures": ["amd64", "arm64"],
                               "additional_tags": "experimental"})
    return entry


def test_deprecate_all_older_active_in_line():
    builds = [_b("22.7.0"), _b("22.9.0", "latest,stable,22"), _b("22.10.1")]
    p = plan(builds)
    assert p.deprecate == {"22.7.0": "22.10.1", "22.9.0": "22.10.1"}
    assert "22.9.0" in p.clear_tags      # it held tags
    assert "22.7.0" not in p.clear_tags  # it had none


def test_single_entry_line_not_deprecated():
    builds = [_b("18.9-cert18", "18-cert"), _b("22.10.1")]
    p = plan(builds)
    assert "18.9-cert18" not in p.deprecate


def test_experimental_member_migrated_to_newest():
    builds = [_b_forky("23.3.0", "23"), _b("23.4.1")]
    p = plan(builds)
    assert p.deprecate["23.3.0"] == "23.4.1"
    moved = p.migrate_experimental["23.4.1"]
    assert len(moved) == 1
    assert moved[0]["distribution"] == "forky"
    assert moved[0]["additional_tags"] == "experimental"


def test_experimental_not_migrated_if_target_has_distribution():
    newest = _b_forky("23.4.1")          # already has forky
    builds = [_b_forky("23.3.0", "23"), newest]
    p = plan(builds)
    assert "23.4.1" not in p.migrate_experimental


def test_plan_idempotent_after_apply():
    # simulate applied state: newest has tags, old is deprecated + forky moved
    applied = [
        {"version": "23.3.0", "additional_tags": "23",
         "deprecated_at": "2026-07-04T00:00:00Z", "superseded_by": "23.4.1",
         "os_matrix": [{"distribution": "trixie", "architectures": ["amd64"]},
                       {"distribution": "forky", "architectures": ["amd64"],
                        "additional_tags": "experimental"}]},
        {"version": "23.4.1", "additional_tags": "23",
         "os_matrix": [{"distribution": "trixie", "architectures": ["amd64"]},
                       {"distribution": "forky", "architectures": ["amd64"],
                        "additional_tags": "experimental"}]},
    ]
    p = plan(applied)
    assert p.deprecate == {}                 # 23.3.0 already deprecated -> excluded
    assert p.migrate_experimental == {}
    assert p.set_tags == {"23.4.1": "23"}    # unchanged


def test_experimental_deduped_across_multiple_superseded():
    # two older entries in one line both carry a forky member; only ONE migrates
    p = plan([_b_forky("23.2.0", "23"), _b_forky("23.3.0", "23"), _b("23.4.1")])
    moved = p.migrate_experimental["23.4.1"]
    assert len([m for m in moved if m["distribution"] == "forky"]) == 1
