import os, importlib.util

ROOT = os.path.join(os.path.dirname(__file__), "..")
_spec = importlib.util.spec_from_file_location(
    "update_readme_versions", os.path.join(ROOT, "scripts", "update-readme-versions.py"))
urv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(urv)


def _build(version, deprecated=False, os_matrix=True):
    b = {"version": version}
    if os_matrix:
        b["os_matrix"] = [{"os": "debian", "distribution": "trixie"}]
    if deprecated:
        b["deprecated_at"] = "2026-05-04T07:22:53Z"
    return b


def test_metrics_total_excludes_git_from_version_count():
    builds = [_build("git"), _build("1.2.40"), _build("22.10.1")]
    m = urv.calculate_version_metrics(builds)
    assert m["total"] == 2
    assert m["has_git"] is True
    assert m["oldest"] == "1.2.40"
    assert m["latest"] == "22.10.1"


def test_metrics_skips_deprecated_and_disabled_entries():
    builds = [
        _build("22.10.1"),
        _build("22.9.0", deprecated=True),
        _build("18.0.0", os_matrix=False),
    ]
    m = urv.calculate_version_metrics(builds)
    assert m["total"] == 1
    assert m["has_git"] is False


def test_update_readme_intro_does_not_claim_artifacts_untracked(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "## Supported Versions\n\nold intro\n\n| old table |\n\n## Next Section\n\nrest\n")
    assert urv.update_readme(str(readme), "| new table |", dry_run=False)
    content = readme.read_text()
    assert "not tracked in git" not in content
    assert "| new table |" in content


def test_metrics_ranks_release_candidate_as_newest_not_oldest():
    # PR #235 rendered "from 24.0.0-rc2 to 23.5.0": the local parser could not
    # read '-rc2' and sorted the release candidate as the oldest version.
    builds = [_build("1.2.40"), _build("23.5.0"), _build("24.0.0-rc2")]
    m = urv.calculate_version_metrics(builds)
    assert m["oldest"] == "1.2.40"
    assert m["latest"] == "24.0.0-rc2"


def test_version_table_orders_rc_between_previous_ga_and_its_ga():
    table = urv.generate_version_table(
        [_build("23.5.0"), _build("24.0.0-rc2"), _build("24.0.0"), _build("1.2.40")])
    rows = [line.split("|")[1].strip() for line in table.splitlines()[2:]]
    assert rows == ["**24.0.0**", "**24.0.0-rc2**", "**23.5.0**", "**1.2.40**"]
