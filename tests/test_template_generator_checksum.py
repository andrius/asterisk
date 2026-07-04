"""
Tests for tarball checksum plumbing (plan 002).

Covers the path: supported-asterisk-builds.yml entry carries
tarball_sha256 / addons_sha256 -> DRYTemplateGenerator reads them and
emits asterisk.source.checksum / asterisk.addons.checksum into the
generated config. The Dockerfile template consumes those fields; that
rendering is exercised end-to-end by the golden regeneration tests once
checksums are backfilled.
"""

import os
import sys
import importlib.util

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

# DRYTemplateGenerator imports yaml; load it like generate-config.py does.
_spec = importlib.util.spec_from_file_location(
    "template_generator", os.path.join(ROOT, "lib", "template_generator.py"))
tg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tg)
DRYTemplateGenerator = tg.DRYTemplateGenerator

SAMPLE_SHA = "0" * 64
SAMPLE_SHA_2 = "1" * 64
ADDONS_SHA = "a" * 64


def _builds_file(tmp_path, entries):
    """Write a minimal supported-asterisk-builds.yml with the given entries."""
    import yaml
    builds = {"latest_builds": entries, "metadata": {"mode": "manual"}}
    p = tmp_path / "supported-asterisk-builds.yml"
    with open(p, "w") as f:
        yaml.dump(builds, f)
    return str(p)


def _generator(tmp_path, builds_entries):
    """A DRYTemplateGenerator pointed at a project layout rooted in tmp_path.

    The generator needs templates/ (the real one) and the supported-builds
    YAML; we wire the templates dir to the repo's templates and the builds
    file to the temp file.
    """
    builds_file = _builds_file(tmp_path, builds_entries)
    gen = DRYTemplateGenerator(os.path.join(ROOT, "templates"))
    gen.supported_builds_file = builds_file
    return gen


def test_tarball_sha256_emitted_into_source_checksum(tmp_path):
    """A matrix entry with tarball_sha256 -> config.asterisk.source.checksum."""
    gen = _generator(tmp_path, [{
        "version": "22.10.1",
        "tarball_sha256": SAMPLE_SHA,
        "os_matrix": [{"os": "debian", "distribution": "trixie",
                       "architectures": ["amd64"]}],
    }])
    config = gen.generate_config("22.10.1", "trixie")
    assert config["asterisk"]["source"]["checksum"] == SAMPLE_SHA


def test_absent_tarball_sha256_means_no_checksum(tmp_path):
    """No tarball_sha256 on the entry -> no checksum key in the config.

    This is the migration-safety contract: the Dockerfile template's
    `{% else %}` unverified branch must render when (and only when) a
    checksum is absent, so a version that has not yet been backfilled
    keeps building unchanged.
    """
    gen = _generator(tmp_path, [{
        "version": "22.10.1",
        "os_matrix": [{"os": "debian", "distribution": "trixie",
                       "architectures": ["amd64"]}],
    }])
    config = gen.generate_config("22.10.1", "trixie")
    assert "checksum" not in config["asterisk"]["source"]


def test_addons_sha256_emitted_into_addons_checksum(tmp_path):
    """A legacy-addons entry with addons_sha256 -> config.asterisk.addons.checksum."""
    gen = _generator(tmp_path, [{
        "version": "1.4.44",
        "tarball_sha256": SAMPLE_SHA,
        "addons_sha256": ADDONS_SHA,
        "os_matrix": [{"os": "debian", "distribution": "jessie",
                       "architectures": ["amd64"]}],
    }])
    config = gen.generate_config("1.4.44", "jessie", variant="legacy-addons")
    assert config["asterisk"]["addons"]["version"] is not None
    assert config["asterisk"]["addons"]["checksum"] == ADDONS_SHA


def test_addons_checksum_absent_when_not_configured(tmp_path):
    """No addons_sha256 and no addons version -> no addons.checksum key."""
    gen = _generator(tmp_path, [{
        "version": "22.10.1",
        "tarball_sha256": SAMPLE_SHA,
        "os_matrix": [{"os": "debian", "distribution": "trixie",
                       "architectures": ["amd64"]}],
    }])
    config = gen.generate_config("22.10.1", "trixie")
    # modern versions have addons.version = None and no checksum
    assert "checksum" not in config["asterisk"].get("addons", {})


def test_checksum_lookup_is_per_version(tmp_path):
    """Two versions with different checksums each resolve to their own."""
    gen = _generator(tmp_path, [
        {"version": "22.10.1", "tarball_sha256": SAMPLE_SHA,
         "os_matrix": [{"os": "debian", "distribution": "trixie",
                        "architectures": ["amd64"]}]},
        {"version": "23.4.1", "tarball_sha256": SAMPLE_SHA_2,
         "os_matrix": [{"os": "debian", "distribution": "trixie",
                        "architectures": ["amd64"]}]},
    ])
    assert gen.generate_config("22.10.1", "trixie")["asterisk"]["source"]["checksum"] == SAMPLE_SHA
    assert gen.generate_config("23.4.1", "trixie")["asterisk"]["source"]["checksum"] == SAMPLE_SHA_2
