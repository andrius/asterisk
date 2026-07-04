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
