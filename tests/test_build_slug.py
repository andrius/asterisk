"""Unit tests for the build_slug helper and os-aware distribution loading.

Task 2 of plans/003-alpine-apk-images.md: the generator learns to build an
`os: alpine` config sourced from templates/distributions/alpine.yml, while
Debian output stays byte-identical (covered by tests/test_golden_regeneration.py).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from template_generator import DRYTemplateGenerator, build_slug  # noqa: E402

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


class TestBuildSlug:
    def test_debian_keeps_the_bare_distribution_name(self):
        assert build_slug("debian", "trixie") == "trixie"
        assert build_slug("debian", "bookworm") == "bookworm"
        assert build_slug("debian", "jessie") == "jessie"

    def test_alpine_namespaces_the_version(self):
        assert build_slug("alpine", "3.24") == "alpine-3.24"
        assert build_slug("alpine", "edge") == "alpine-edge"


class TestOsAwareDistributionLoad:
    def _gen(self):
        return DRYTemplateGenerator(TEMPLATES_DIR)

    def test_debian_default_loads_the_per_distribution_file(self):
        cfg = self._gen()._load_distribution_config("trixie")
        assert cfg["distribution"] == "trixie"
        assert cfg["base"]["image"] == "debian:trixie"

    def test_alpine_loads_the_single_alpine_file(self):
        cfg = self._gen()._load_distribution_config("3.24", os_name="alpine")
        assert cfg["os"] == "alpine"
        assert cfg["apk_repo_base"].startswith("https://dl.cloudsmith.io/")
        assert "bash" in cfg["runtime_packages"]


class TestAlpineBaseResolution:
    def _gen(self):
        return DRYTemplateGenerator(TEMPLATES_DIR)

    def test_alpine_config_flips_os_and_composes_the_base_image(self):
        cfg = self._gen().generate_config("22.10.1", "3.24", os_name="alpine")
        assert cfg["base"]["os"] == "alpine"
        assert cfg["base"]["image"] == "alpine:3.24"

    def test_alpine_edge_base_image(self):
        cfg = self._gen().generate_config("23.4.1", "edge", os_name="alpine")
        assert cfg["base"]["image"] == "alpine:edge"

    def test_debian_default_is_unchanged(self):
        cfg = self._gen().generate_config("22.10.1", "trixie")
        assert cfg["base"]["os"] == "debian"
        assert cfg["base"]["image"] == "debian:trixie"


class TestAlpineConfigIsLean:
    """Alpine installs prebuilt apks and compiles nothing, so its config must
    not carry Debian package lists or any compile-time Asterisk config."""

    def _alpine_cfg(self):
        return DRYTemplateGenerator(TEMPLATES_DIR).generate_config(
            "22.10.1", "3.24", os_name="alpine")

    def test_no_compile_asterisk_block(self):
        cfg = self._alpine_cfg()
        assert cfg["asterisk"] == {}  # no menuselect / configure / source / addons

    def test_no_menuselect_or_opus_codec(self):
        cfg = self._alpine_cfg()
        assert "menuselect" not in cfg["asterisk"]
        assert "opus_codec" not in cfg["asterisk"]

    def test_no_debian_packages(self):
        cfg = self._alpine_cfg()
        assert cfg["packages"]["build"] == []
        assert cfg["packages"]["runtime"] == []

    def test_no_build_script_and_no_features(self):
        cfg = self._alpine_cfg()
        # Single-stage, but with no build.sh (no build script generated).
        assert "script" not in cfg["build"]
        assert cfg["build"].get("type") == "single-stage"
        assert "features" not in cfg

    def test_docker_tags_use_alpine_not_debian(self):
        tags = self._alpine_cfg()["docker"]["tags"]
        assert "22.10.1_alpine-3.24" in tags
        assert not any("debian" in t for t in tags)
