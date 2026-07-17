"""Task 4 of plans/003-alpine-apk-images.md.

Covers the Alpine consumption block (config.alpine) assembled from alpine.yml
constants + the matrix apk pin, and the alpine-apk Dockerfile it renders. The
apk pin + subpackages come from the os_matrix entry (resolved by alpine-sync
from the published APKINDEX); tree / pin tag / repo URL derive from the Alpine
version.
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
SCHEMA = os.path.join(ROOT, "schema", "build-config.schema.json")


def _generator(tmp_path, entries):
    builds = {"latest_builds": entries, "metadata": {"mode": "manual"}}
    p = tmp_path / "supported-asterisk-builds.yml"
    with open(p, "w") as f:
        yaml.dump(builds, f)
    gen = DRYTemplateGenerator(TEMPLATES)
    gen.supported_builds_file = str(p)
    return gen


STABLE_ENTRY = {
    "version": "22.10.1",
    "os_matrix": [{
        "os": "alpine", "distribution": "3.24",
        "apk_version": "22.10.1-r0",
        "apk_packages": ["opus", "srtp", "curl"],
        "architectures": ["amd64", "arm64"],
    }],
}

EDGE_ENTRY = {
    "version": "23.4.1",
    "os_matrix": [{
        "os": "alpine", "distribution": "edge",
        "apk_version": "23.4.1-r0",
        "apk_packages": ["opus"],
        "architectures": ["amd64", "arm64"],
    }],
}


class TestAlpineConfigBlock:
    def test_stable_tree_pin_and_repo_url(self, tmp_path):
        cfg = _generator(tmp_path, [STABLE_ENTRY]).generate_config(
            "22.10.1", "3.24", os_name="alpine")
        a = cfg["alpine"]
        assert a["tree"] == "v3.24"
        assert a["pin_tag"] == "andrius-asterisk"
        assert a["repo_url"] == (
            "https://dl.cloudsmith.io/public/asterisk/alpine/alpine/v3.24/main")
        assert a["apk_version"] == "22.10.1-r0"
        assert a["apk_packages"] == ["opus", "srtp", "curl"]
        assert a["signing_key_dest"] == (
            "/etc/apk/keys/alpine@asterisk-25B0C9A992BE0CEF.rsa.pub")
        assert "bash" in a["runtime_packages"]

    def test_edge_tree_uses_edge_pin_tag_and_path(self, tmp_path):
        cfg = _generator(tmp_path, [EDGE_ENTRY]).generate_config(
            "23.4.1", "edge", os_name="alpine")
        a = cfg["alpine"]
        assert a["tree"] == "edge"
        assert a["pin_tag"] == "andrius-asterisk-edge"
        assert a["repo_url"].endswith("/alpine/edge/main")
        assert a["apk_version"] == "23.4.1-r0"


class TestAlpineDockerfileRender:
    def _render(self, tmp_path, entry, version, distribution):
        cfg = _generator(tmp_path, [entry]).generate_config(
            version, distribution, os_name="alpine")
        cfg_path = tmp_path / "cfg.yml"
        with open(cfg_path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False)
        gen = DockerfileGenerator(DOCKERFILE_TEMPLATES, SCHEMA)
        # format_dockerfile=False keeps the test hermetic (no docker/dockerfmt);
        # byte-golden formatting is covered when real dirs are seeded (Task 10).
        return gen.generate_dockerfile(str(cfg_path), format_dockerfile=False)

    def test_renders_apk_install_recipe(self, tmp_path):
        df = self._render(tmp_path, STABLE_ENTRY, "22.10.1", "3.24")
        assert "FROM alpine:3.24" in df
        assert ("COPY cloudsmith-asterisk-alpine.rsa.pub "
                "/etc/apk/keys/alpine@asterisk-25B0C9A992BE0CEF.rsa.pub") in df
        assert ('echo "@andrius-asterisk '
                'https://dl.cloudsmith.io/public/asterisk/alpine/alpine/v3.24/main"') in df
        assert '"asterisk@andrius-asterisk=22.10.1-r0"' in df
        assert '"asterisk-sample-config@andrius-asterisk=22.10.1-r0"' in df
        assert '"asterisk-opus@andrius-asterisk=22.10.1-r0"' in df
        assert "asterisk -V" in df
        assert 'ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]' in df

    def test_has_no_build_stage_or_menuselect(self, tmp_path):
        df = self._render(tmp_path, STABLE_ENTRY, "22.10.1", "3.24")
        assert "menuselect" not in df
        assert "asterisk-builder" not in df  # no multi-stage builder
        assert "apt-get" not in df

    def test_edge_dockerfile_uses_edge_repo(self, tmp_path):
        df = self._render(tmp_path, EDGE_ENTRY, "23.4.1", "edge")
        assert "FROM alpine:edge" in df
        assert "@andrius-asterisk-edge" in df
        assert "/alpine/edge/main" in df


class TestBuildScriptSkipped:
    def test_generate_build_script_returns_none_for_alpine(self, tmp_path):
        cfg = _generator(tmp_path, [STABLE_ENTRY]).generate_config(
            "22.10.1", "3.24", os_name="alpine")
        cfg_path = tmp_path / "cfg.yml"
        with open(cfg_path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False)
        gen = DockerfileGenerator(DOCKERFILE_TEMPLATES, SCHEMA)
        assert gen.generate_build_script(str(cfg_path)) is None
