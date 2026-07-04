import sys, os, importlib.util
from ruamel.yaml import YAML

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location(
    "apply_tag_lifecycle", os.path.join(ROOT, "scripts", "apply-tag-lifecycle.py"))
atl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atl)

YAML_IN = """\
# header comment must survive
latest_builds:
  - version: "23.3.0"
    additional_tags: "23"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
      - os: "debian"
        distribution: "forky"
        architectures: ["amd64", "arm64"]
        additional_tags: "experimental"
  - version: "23.4.1"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
metadata:
  mode: "manual"
"""


def _load(text):
    y = YAML()
    y.preserve_quotes = True
    return y, y.load(text)


def test_apply_pr_moves_tag_sets_superseded_migrates_forky(tmp_path):
    y, data = _load(YAML_IN)
    atl.apply_pr(data)
    builds = {b["version"]: b for b in data["latest_builds"]}
    # tag moved to newest, cleared from old
    assert builds["23.4.1"]["additional_tags"] == "23"
    assert "additional_tags" not in builds["23.3.0"]
    # pending deprecation: superseded_by set, NO deprecated_at yet
    assert builds["23.3.0"]["superseded_by"] == "23.4.1"
    assert "deprecated_at" not in builds["23.3.0"]
    # forky migrated onto 23.4.1
    dists = [m["distribution"] for m in builds["23.4.1"]["os_matrix"]]
    assert "forky" in dists
    forky = [m for m in builds["23.4.1"]["os_matrix"] if m["distribution"] == "forky"][0]
    assert forky["additional_tags"] == "experimental"


def test_apply_pr_preserves_header_comment(tmp_path):
    import io
    y, data = _load(YAML_IN)
    atl.apply_pr(data)
    buf = io.StringIO()
    y.dump(data, buf)
    assert "# header comment must survive" in buf.getvalue()


# Byte-stability guard: the real supported-asterisk-builds.yml uses indented
# block sequences (dash indented under its key). _yaml() must round-trip that
# style byte-for-byte with NO changes, or every real run produces a huge noisy
# diff. This fixture is in that exact canonical style.
INDENTED_YAML = (
    "# header\n"
    "latest_builds:\n"
    '  - version: "22.10.1"\n'
    '    additional_tags: "latest,stable,22"\n'
    "    os_matrix:\n"
    '      - os: "debian"\n'
    '        distribution: "trixie"\n'
    "        architectures:\n"
    '          - "amd64"\n'
    '          - "arm64"\n'
    "metadata:\n"
    '  mode: "manual"\n'
)


def test_yaml_roundtrip_preserves_indented_sequence_style():
    import io
    y = atl._yaml()
    data = y.load(INDENTED_YAML)
    buf = io.StringIO()
    y.dump(data, buf)
    assert buf.getvalue() == INDENTED_YAML


PENDING_YAML = """\
latest_builds:
  - version: "23.3.0"
    superseded_by: "23.4.1"
    os_matrix:
      - {os: "debian", distribution: "trixie", architectures: ["amd64"]}
  - version: "22.8.2"
    superseded_by: "22.9.0"
    deprecated_at: "2026-05-04T07:22:53Z"
    os_matrix:
      - {os: "debian", distribution: "trixie", architectures: ["amd64"]}
  - version: "23.4.1"
    additional_tags: "23"
    os_matrix:
      - {os: "debian", distribution: "trixie", architectures: ["amd64"]}
metadata:
  mode: "manual"
"""


def test_finalize_stamps_only_pending():
    y, data = _load(PENDING_YAML)
    stamped = atl.finalize(data, "2026-07-04T11:00:00Z")
    builds = {b["version"]: b for b in data["latest_builds"]}
    assert stamped == ["23.3.0"]
    assert builds["23.3.0"]["deprecated_at"] == "2026-07-04T11:00:00Z"
    # already-deprecated one is untouched (keeps original date)
    assert builds["22.8.2"]["deprecated_at"] == "2026-05-04T07:22:53Z"


def test_finalize_idempotent():
    y, data = _load(PENDING_YAML)
    atl.finalize(data, "2026-07-04T11:00:00Z")
    stamped_again = atl.finalize(data, "2026-07-05T11:00:00Z")
    assert stamped_again == []   # nothing pending on second run


def test_check_returns_nonzero_when_drift(tmp_path):
    f = tmp_path / "b.yml"
    f.write_text(YAML_IN)
    rc = atl.main(["--phase", "pr", "--file", str(f), "--check"])
    assert rc == 1                      # YAML_IN is not in desired state
    assert f.read_text() == YAML_IN     # unchanged


def test_check_returns_zero_when_clean(tmp_path):
    f = tmp_path / "b.yml"
    f.write_text(YAML_IN)
    atl.main(["--phase", "pr", "--file", str(f)])   # bring to desired state
    settled = f.read_text()
    rc = atl.main(["--phase", "pr", "--file", str(f), "--check"])
    assert rc == 0
    assert f.read_text() == settled


def test_apply_pr_double_quotes_fresh_keys():
    import io
    y, data = _load(YAML_IN)
    atl.apply_pr(data)
    buf = io.StringIO(); y.dump(data, buf); out = buf.getvalue()
    assert 'additional_tags: "23"' in out       # fresh entry-level tag on 23.4.1
    assert 'superseded_by: "23.4.1"' in out      # fresh key on 23.3.0


def test_finalize_double_quotes_deprecated_at():
    import io
    y, data = _load(PENDING_YAML)
    atl.finalize(data, "2026-07-04T11:00:00Z")
    buf = io.StringIO(); y.dump(data, buf)
    assert 'deprecated_at: "2026-07-04T11:00:00Z"' in buf.getvalue()


CHECKSUM_YAML = """\
latest_builds:
  - version: "23.3.0"
    tarball_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    additional_tags: "23"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
  - version: "1.4.44"
    tarball_sha256: "1111111111111111111111111111111111111111111111111111111111111111"
    addons_sha256: "2222222222222222222222222222222222222222222222222222222222222222"
    additional_tags: "1.4"
    os_matrix:
      - os: "debian"
        distribution: "jessie"
        architectures: ["amd64"]
  - version: "23.4.1"
    tarball_sha256: "3333333333333333333333333333333333333333333333333333333333333333"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
metadata:
  mode: "manual"
"""


def test_apply_pr_preserves_tarball_and_addons_checksums():
    """Tag-lifecycle must round-trip checksum fields byte-for-byte untouched.

    plan 002 stores tarball_sha256 / addons_sha256 on each build entry;
    apply-tag-lifecycle rewrites the YAML with ruamel, so a no-op pass
    over those entries must not drop, reformat, or rewrap the checksums.
    """
    import io
    y, data = _load(CHECKSUM_YAML)
    atl.apply_pr(data)
    buf = io.StringIO(); y.dump(data, buf); out = buf.getvalue()
    assert 'tarball_sha256: "0000000000000000000000000000000000000000000000000000000000000000"' in out
    assert 'tarball_sha256: "1111111111111111111111111111111111111111111111111111111111111111"' in out
    assert 'addons_sha256: "2222222222222222222222222222222222222222222222222222222222222222"' in out
    # the new active tag holder also keeps its checksum
    assert 'tarball_sha256: "3333333333333333333333333333333333333333333333333333333333333333"' in out
    # no unquoted / bare checksum renderings leaked through
    assert "tarball_sha256: 0" not in out
    assert "tarball_sha256: 1" not in out


def test_finalize_preserves_tarball_and_addons_checksums():
    """finalize must not touch checksum fields when stamping deprecated_at."""
    import io
    # mark one entry pending so finalize has work to do
    y, data = _load(CHECKSUM_YAML)
    data["latest_builds"][0]["superseded_by"] = "23.4.1"
    atl.finalize(data, "2026-07-04T11:00:00Z")
    buf = io.StringIO(); y.dump(data, buf); out = buf.getvalue()
    builds = {b["version"]: b for b in data["latest_builds"]}
    # checksums intact on the deprecated entry
    assert builds["23.3.0"]["tarball_sha256"] == "0" * 64
    # and on the legacy-addons entry, untouched
    assert builds["1.4.44"]["tarball_sha256"] == "1" * 64
    assert builds["1.4.44"]["addons_sha256"] == "2" * 64
    # rendered form preserved
    assert 'tarball_sha256: "1111111111111111111111111111111111111111111111111111111111111111"' in out

