#!/usr/bin/env python3
"""
DRY Template Generator for Asterisk Builds

This enhanced generator implements the new DRY template architecture:
- Base package definitions
- Distribution-specific overrides
- Variant-specific templates
- Template inheritance system
- Smart package resolution
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from copy import deepcopy


def build_slug(os_name: str, distribution: str) -> str:
    """Directory/config key for a (os, distribution) pair.

    Debian keeps the bare distribution name (``trixie``) so the 64 existing
    ``asterisk/<version>-<dist>/`` dirs and ``configs/generated`` files are
    untouched. Alpine namespaces the version under ``alpine-`` (``alpine-3.24``,
    ``alpine-edge``) - the raw Alpine version (``3.24``) alone would be an
    unreadable, collision-prone key. See plans/003-alpine-apk-images.md.
    """
    if os_name == "alpine":
        return f"alpine-{distribution}"
    return distribution


def alpine_tree(distribution: str) -> str:
    """Cloudsmith distribution segment for an Alpine version.

    Numeric releases live under ``v<X.Y>`` (``3.24`` -> ``v3.24``); the rolling
    ``edge`` tree keeps its bare name.
    """
    return distribution if distribution == "edge" else f"v{distribution}"


def alpine_pin_tag(base_tag: str, distribution: str) -> str:
    """apk repository pin tag; the edge tree is served under the ``-edge`` tag."""
    return f"{base_tag}-edge" if distribution == "edge" else base_tag


@dataclass
class TemplateContext:
    """Context for template resolution"""
    version: str
    distribution: str
    variant: str
    base_packages: Dict[str, List[str]]
    distribution_config: Dict[str, Any]
    variant_config: Dict[str, Any]
    os_name: str = "debian"

class DRYTemplateGenerator:
    """Enhanced template generator with DRY architecture support"""

    def __init__(self, templates_dry_dir: str = "templates-dry"):
        self.templates_dir = Path(templates_dry_dir)
        self.base_dir = self.templates_dir / "base"
        self.distributions_dir = self.templates_dir / "distributions"
        self.variants_dir = self.templates_dir / "variants"

        # Load base configurations
        self.base_packages = self._load_base_packages()
        self.base_template = self._load_base_template()

        # Optional: path to asterisk/supported-asterisk-builds.yml, used to
        # look up per-version tarball/addons checksums (plan 002). Defaults to
        # <repo-root>/asterisk/supported-asterisk-builds.yml (the templates dir
        # is <repo-root>/templates); tests and callers may override it.
        self.supported_builds_file = None

    def _load_base_packages(self) -> Dict[str, Any]:
        """Load common package definitions"""
        packages_file = self.base_dir / "common-packages.yml"
        try:
            with open(packages_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Base packages file not found: {packages_file}")
            return {}

    def _load_base_template(self) -> Dict[str, Any]:
        """Load base Asterisk template"""
        template_file = self.base_dir / "asterisk-base.yml.template"
        try:
            with open(template_file, 'r') as f:
                content = f.read()
                # Don't replace variables yet - that happens during generation
                return yaml.safe_load(content)
        except FileNotFoundError:
            print(f"Warning: Base template file not found: {template_file}")
            return {}

    def _load_distribution_config(self, distribution: str, os_name: str = "debian") -> Dict[str, Any]:
        """Load distribution-specific configuration.

        Alpine builds share a single ``alpine.yml`` (they consume prebuilt apks
        rather than compile, so there are no per-Alpine-version package lists);
        the specific Alpine version rides the os_matrix entry. Debian keeps its
        per-distribution ``debian-<dist>.yml`` files.
        """
        if os_name == "alpine":
            config_file = self.distributions_dir / "alpine.yml"
        else:
            config_file = self.distributions_dir / f"debian-{distribution}.yml"
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Distribution config not found: {config_file}")
            return {"distribution": distribution}

    def _load_variant_template(self, variant: str) -> Dict[str, Any]:
        """Load variant-specific template"""
        template_file = self.variants_dir / f"{variant}.yml.template"
        try:
            with open(template_file, 'r') as f:
                content = f.read()
                return yaml.safe_load(content)
        except FileNotFoundError:
            print(f"Warning: Variant template not found: {template_file}")
            return {"variant": variant}

    def _determine_variant(self, version: str) -> str:
        """Determine the appropriate variant based on version"""
        # Version-based variant detection
        if version.startswith(('1.2', '1.4', '1.6')):
            return "legacy-addons"
        elif version.startswith(('1.8', '10.')):
            return "legacy"
        elif version.startswith('11.') and not '-cert' in version:
            return "asterisk-11"
        else:
            return "modern"

    def _determine_distribution(self, version: str) -> str:
        """Determine the appropriate distribution based on version"""
        # Distribution mapping based on version compatibility
        if version.startswith(('1.', '10.', '11.', '12.')):
            return "jessie"
        elif version.startswith(('13.', '14.', '15.')):
            return "buster"
        elif version.startswith(('16.', '17.')):
            return "bookworm"
        else:
            return "trixie"

    def _resolve_packages(self, context: TemplateContext) -> Dict[str, List[str]]:
        """Resolve package lists using DRY architecture"""
        # Alpine images install prebuilt apks and compile nothing, so they carry
        # no Debian package lists. Their runtime dependencies come from
        # alpine.yml (read by the Alpine Dockerfile template) plus the apk
        # subpackages named in the os_matrix entry - never from common-packages.yml.
        if context.os_name == "alpine":
            return {"build": [], "runtime": []}

        packages = {
            "build": [],
            "runtime": []
        }

        # Start with common packages
        packages["build"].extend(context.base_packages.get("common_build_packages", []))
        packages["runtime"].extend(context.base_packages.get("common_runtime_packages", []))

        # Add distribution-specific packages
        dist_overrides = context.distribution_config.get("package_overrides", {})
        packages["build"].extend(dist_overrides.get("build", []))
        packages["runtime"].extend(dist_overrides.get("runtime", []))

        # Add variant-specific packages if any
        variant_packages = context.variant_config.get("packages", {})
        packages["build"].extend(variant_packages.get("build", []))
        packages["runtime"].extend(variant_packages.get("runtime", []))

        # Apply per-distribution exclusions (e.g. forky obsoleted libxml2 -> libxml2-16)
        build_exclude = set(dist_overrides.get("exclude_build", []))
        runtime_exclude = set(dist_overrides.get("exclude_runtime", []))
        packages["build"] = [p for p in packages["build"] if p not in build_exclude]
        packages["runtime"] = [p for p in packages["runtime"] if p not in runtime_exclude]

        # Remove duplicates while preserving order
        packages["build"] = list(dict.fromkeys(packages["build"]))
        packages["runtime"] = list(dict.fromkeys(packages["runtime"]))

        # When runtime auto-derivation is enabled, the shared-library packages
        # are discovered from the built binaries at image-build time (ldd +
        # dpkg-query), so drop the hand-pinned lib* entries here and keep only
        # the non-library runtime essentials (curl, ca-certificates, python3,
        # gettext-base, ...). This keeps experimental/rolling distributions
        # (forky) resilient to SONAME-versioned package renames.
        if context.distribution_config.get("runtime_autoderive"):
            packages["runtime"] = [
                p for p in packages["runtime"] if not p.startswith("lib")
            ]

        return packages

    def _resolve_asterisk_config(self, context: TemplateContext) -> Dict[str, Any]:
        """Resolve Asterisk configuration with inheritance"""
        # Alpine does not compile Asterisk: no menuselect, no configure options,
        # no Digium Opus blob, no source tarball. The prebuilt apk already
        # contains the selected modules, so the asterisk config block is empty.
        if context.os_name == "alpine":
            return {}

        # Start with base configuration
        asterisk_config = deepcopy(self.base_template.get("asterisk", {}))

        # Apply variant-specific overrides
        variant_asterisk = context.variant_config.get("asterisk", {})

        # Deep merge configurations
        for key, value in variant_asterisk.items():
            if key in asterisk_config and isinstance(asterisk_config[key], dict) and isinstance(value, dict):
                asterisk_config[key].update(value)
            else:
                asterisk_config[key] = value

        # Handle source URL template based on version type
        if "-cert" in context.version:
            asterisk_config["source"] = {
                "url_template": "https://downloads.asterisk.org/pub/telephony/certified-asterisk/releases/asterisk-certified-{version}.tar.gz"
            }
        elif "source" not in asterisk_config:
            asterisk_config["source"] = {
                "url_template": "https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-{version}.tar.gz"
            }

        # Pin tarball integrity (plan 002): carry the per-version sha256 from
        # supported-asterisk-builds.yml into the generated config, where the
        # Dockerfile template renders a download-verify-extract step. Absent
        # checksum (legacy tail not yet backfilled, or no matrix entry) leaves
        # the config unchanged so the template falls back to its unverified
        # branch and builds keep working during rollout.
        checksums = self._lookup_checksums(context.version)
        if checksums.get("tarball_sha256"):
            asterisk_config["source"]["checksum"] = checksums["tarball_sha256"]
        if checksums.get("addons_sha256"):
            asterisk_config.setdefault("addons", {})
            if isinstance(asterisk_config.get("addons"), dict):
                asterisk_config["addons"]["checksum"] = checksums["addons_sha256"]

        return asterisk_config

    def _resolve_docker_config(self, context: TemplateContext) -> Dict[str, Any]:
        """Resolve Docker configuration with inheritance"""
        # Start with base configuration
        docker_config = deepcopy(self.base_template.get("docker", {}))

        # Apply distribution-specific overrides
        dist_docker = context.distribution_config.get("docker", {})
        for key, value in dist_docker.items():
            docker_config[key] = value

        # Apply variant-specific overrides
        variant_docker = context.variant_config.get("docker", {})
        for key, value in variant_docker.items():
            docker_config[key] = value

        return docker_config

    def _resolve_base_config(self, context: TemplateContext) -> Dict[str, Any]:
        """Resolve base image configuration"""
        base_config = deepcopy(self.base_template.get("base", {}))

        # Apply distribution overrides
        dist_base = context.distribution_config.get("base", {})
        base_config.update(dist_base)

        # Set distribution
        base_config["distribution"] = context.distribution

        # Resolve OS. Debian is the base-template default (re-assigning the same
        # value is a no-op, so Debian output is byte-identical); Alpine flips it
        # and composes its base image from the Alpine version carried in the
        # os_matrix distribution field (3.24 -> alpine:3.24, edge -> alpine:edge).
        base_config["os"] = context.os_name
        if context.os_name == "alpine":
            base_config["image"] = f"alpine:{context.distribution}"

        # Propagate runtime auto-derivation flag. Rolling/experimental suites
        # (e.g. Debian forky) derive their runtime shared-library packages from
        # the built binaries at image-build time instead of hand-pinning them.
        if context.distribution_config.get("runtime_autoderive"):
            base_config["runtime_autoderive"] = True

        return base_config

    def _substitute_variables(self, config: Dict[str, Any], context: TemplateContext) -> Dict[str, Any]:
        """Substitute template variables throughout the configuration"""
        config_str = yaml.dump(config)

        # Substitute variables
        config_str = config_str.replace("{{VERSION}}", context.version)
        config_str = config_str.replace("{{DISTRIBUTION}}", context.distribution)
        config_str = config_str.replace("{{VARIANT}}", context.variant)
        config_str = config_str.replace("{{OS}}", context.os_name)

        # Handle addons version for legacy versions
        if context.variant == "legacy-addons":
            addons_version = self._get_addons_version(context.version)
            config_str = config_str.replace("{{ADDONS_VERSION}}", addons_version)

        return yaml.safe_load(config_str)

    def _get_addons_version(self, asterisk_version: str) -> str:
        """Map Asterisk version to addons version for legacy builds"""
        major_version = '.'.join(asterisk_version.split('.')[:2])

        addons_mapping = {
            '1.2': '1.2.9',
            '1.4': '1.4.9',
            '1.6': '1.6.2.4'
        }

        return addons_mapping.get(major_version, asterisk_version)

    def _resolve_supported_builds_file(self) -> Optional[Path]:
        """Locate asterisk/supported-asterisk-builds.yml for checksum lookups.

        Honors an explicit override (set by tests / advanced callers), else
        falls back to <templates-dir>/../asterisk/supported-asterisk-builds.yml
        (the standard repo layout). Returns None if no file is found, in which
        case checksum plumbing is silently skipped - configs generate exactly
        as before, and the Dockerfile template renders its unverified branch.
        """
        if self.supported_builds_file:
            p = Path(self.supported_builds_file)
            return p if p.exists() else None
        default = self.templates_dir.parent / "asterisk" / "supported-asterisk-builds.yml"
        return default if default.exists() else None

    def _lookup_checksums(self, version: str) -> Dict[str, Optional[str]]:
        """Look up tarball_sha256 / addons_sha256 for a version from the matrix.

        Returns a dict with optional 'tarball_sha256' and 'addons_sha256'
        keys (absent when the version has no entry or no checksum). This is
        the source-of-truth read: the matrix entry is where a new release's
        checksum is reviewed (tag-lifecycle precedent), and it survives
        tag-lifecycle round-trips untouched (unit-tested in
        test_apply_tag_lifecycle.py).
        """
        builds_file = self._resolve_supported_builds_file()
        if not builds_file:
            return {}
        try:
            with open(builds_file, 'r') as f:
                data = yaml.safe_load(f)
        except (FileNotFoundError, OSError):
            return {}

        result: Dict[str, Optional[str]] = {}
        for build in (data or {}).get("latest_builds", []):
            if build.get("version") == version:
                if build.get("tarball_sha256"):
                    result["tarball_sha256"] = build["tarball_sha256"]
                if build.get("addons_sha256"):
                    result["addons_sha256"] = build["addons_sha256"]
                break
        return result

    def _lookup_alpine_facts(self, version: str, distribution: str) -> Dict[str, Any]:
        """Look up the apk pin + subpackages for an Alpine build from the matrix.

        Returns the ``apk_version`` / ``apk_packages`` (and ``architectures``)
        recorded on the ``os: alpine`` os_matrix member for (version,
        distribution). These are resolved from the published APKINDEX by the
        alpine-sync workflow and are the only Alpine facts that are NOT
        derivable locally (tree, pin tag, and repo URL derive from the Alpine
        version). Absent entry -> empty dict (config generates with the
        derivable fields only; validate-generation flags a missing apk_version).
        """
        builds_file = self._resolve_supported_builds_file()
        if not builds_file:
            return {}
        try:
            with open(builds_file, 'r') as f:
                data = yaml.safe_load(f)
        except (FileNotFoundError, OSError):
            return {}

        for build in (data or {}).get("latest_builds", []):
            if build.get("version") != version:
                continue
            for member in build.get("os_matrix", []) or []:
                if member.get("os") == "alpine" and str(member.get("distribution")) == str(distribution):
                    facts: Dict[str, Any] = {}
                    if member.get("apk_version"):
                        facts["apk_version"] = member["apk_version"]
                    if member.get("apk_packages"):
                        facts["apk_packages"] = member["apk_packages"]
                    if member.get("architectures"):
                        facts["architectures"] = member["architectures"]
                    return facts
        return {}

    def _resolve_alpine_config(self, version: str, distribution: str,
                              distribution_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble the ``alpine`` config block consumed by the apk Dockerfile.

        Merges the Cloudsmith constants from alpine.yml with the tree/pin/repo
        URL derived from the Alpine version and the exact apk pin looked up from
        the matrix.
        """
        tree = alpine_tree(distribution)
        facts = self._lookup_alpine_facts(version, distribution)
        block = {
            "tree": tree,
            "repo_url": f"{distribution_config['apk_repo_base']}/{tree}/main",
            "pin_tag": alpine_pin_tag(distribution_config["apk_pin_tag"], distribution),
            "signing_key_file": distribution_config["signing_key_file"],
            "signing_key_dest": distribution_config["signing_key_dest"],
            "runtime_packages": distribution_config.get("runtime_packages", []),
            "apk_packages": facts.get("apk_packages", []),
        }
        if facts.get("apk_version"):
            block["apk_version"] = facts["apk_version"]
        return block

    def _apply_version_overrides(self, config: Dict[str, Any], version: str) -> Dict[str, Any]:
        """Apply version-specific overrides to configuration"""
        import re

        # Alpine builds carry no compile config to override (no menuselect,
        # opus blob, or chan_sip/chan_websocket toggles - the apk is prebuilt).
        if config.get("base", {}).get("os") == "alpine":
            return config

        # Parse version to determine major version
        if version == 'git' or version.startswith('git-'):
            major = 99  # Treat git as latest
            is_certified = False
        else:
            is_certified = '-cert' in version
            base_version = version.split('-cert')[0]
            match = re.match(r'^(\d+)\.(\d+)', base_version)
            if match:
                major = int(match.group(1))
            else:
                return config  # Can't parse, skip overrides

        # Only apply overrides to modern versions (12+)
        if major < 12:
            return config

        # Ensure asterisk structure exists
        if "asterisk" not in config:
            config["asterisk"] = {}

        # Certified versions: Disable XML documentation (fixes build errors)
        # Affects versions like 18.9-cert17 where XML doc generation fails
        if is_certified and major >= 16:
            if "configure_options" not in config["asterisk"]:
                config["asterisk"]["configure_options"] = []
            if "--disable-xmldoc" not in config["asterisk"]["configure_options"]:
                config["asterisk"]["configure_options"].append("--disable-xmldoc")

        # Ensure asterisk.menuselect structure exists
        if "menuselect" not in config["asterisk"]:
            config["asterisk"]["menuselect"] = {}
        if "channels" not in config["asterisk"]["menuselect"]:
            config["asterisk"]["menuselect"]["channels"] = []
        if "exclude" not in config["asterisk"]["menuselect"]:
            config["asterisk"]["menuselect"]["exclude"] = []

        channels = config["asterisk"]["menuselect"]["channels"]
        exclude = config["asterisk"]["menuselect"]["exclude"]

        # v21+: Explicitly disable chan_sip (removed from Asterisk)
        if major >= 21:
            if "chan_sip" not in exclude:
                exclude.append("chan_sip")

        # v23+ and git: Add chan_websocket (mandatory)
        if major >= 23:
            if "chan_websocket" not in channels:
                channels.append("chan_websocket")

            # Update websockets feature flag
            if "features" not in config:
                config["features"] = {}
            config["features"]["websockets"] = True

        # v20+: Enable Digium binary Opus codec (x86-64 only, downloaded at build time)
        if major >= 20:
            opus_major = min(major, 23)  # Cap at 23 (latest Digium codec available)
            config["asterisk"]["opus_codec"] = {
                "enabled": True,
                "major_version": opus_major,
            }

        return config

    def generate_config(self, version: str, distribution: str = None, variant: str = None,
                        os_name: str = "debian") -> Dict[str, Any]:
        """Generate complete configuration using DRY template system"""

        # Auto-detect distribution and variant if not provided
        if distribution is None:
            distribution = self._determine_distribution(version)
        if variant is None:
            variant = self._determine_variant(version)

        print(f"Generating config for {version} (os: {os_name}, distribution: {distribution}, variant: {variant})")

        # Load configurations
        distribution_config = self._load_distribution_config(distribution, os_name)
        variant_config = self._load_variant_template(variant)

        # Create context
        context = TemplateContext(
            version=version,
            distribution=distribution,
            variant=variant,
            base_packages=self.base_packages,
            distribution_config=distribution_config,
            variant_config=variant_config,
            os_name=os_name
        )

        # Build final configuration. Alpine installs prebuilt apks, so it has no
        # build script (no build.sh); it is a single-FROM image (build.type
        # satisfies the schema and reflects the single-stage Dockerfile).
        config = {
            "version": version,
            "base": self._resolve_base_config(context),
            "packages": self._resolve_packages(context),
            "asterisk": self._resolve_asterisk_config(context),
            "docker": self._resolve_docker_config(context),
            "build": {"type": "single-stage"} if os_name == "alpine" else self.base_template.get("build", {})
        }

        # Add EOL setup if needed
        if distribution_config.get("eol"):
            config["packages"]["eol_setup"] = distribution_config.get("eol_setup", [])

        # Add features if defined. These are compile/build toggles (pjsip, hep,
        # websockets, ...) that the Alpine apk resolves at package-build time, so
        # they are irrelevant to an apk-installed image.
        if "features" in variant_config and os_name != "alpine":
            config["features"] = variant_config["features"]

        # Substitute variables
        config = self._substitute_variables(config, context)

        # Apply version-specific overrides
        config = self._apply_version_overrides(config, version)

        # Alpine: attach the apk consumption block (repo URL, pin, key, exact
        # version pin, subpackages) that the alpine-apk Dockerfile renders.
        if os_name == "alpine":
            config["alpine"] = self._resolve_alpine_config(version, distribution, distribution_config)

        return config

    def save_config(self, config: Dict[str, Any], output_path: str):
        """Save generated configuration to file"""
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if there is one
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def generate_and_save_config(self, version: str, distribution: str, output_path: str,
                                 os_name: str = "debian") -> bool:
        """Generate and save configuration in one step"""
        try:
            config = self.generate_config(version, distribution, os_name=os_name)
            self.save_config(config, output_path)
            return True
        except Exception as e:
            print(f"Error generating config: {e}", file=sys.stderr)
            return False

    def generate_all_supported_configs(self, supported_builds_file: str, output_dir: str = "configs/generated-dry"):
        """Generate all configurations from supported builds matrix"""
        with open(supported_builds_file, 'r') as f:
            builds_data = yaml.safe_load(f)

        total_generated = 0

        for build in builds_data.get("latest_builds", []):
            version = build["version"]
            os_matrix = build.get("os_matrix", [])

            for matrix_entry in os_matrix:
                distribution = matrix_entry["distribution"]
                os_name = matrix_entry.get("os", "debian")

                # Use custom template mapping if specified
                variant = None
                if "template" in matrix_entry:
                    template_name = matrix_entry["template"]
                    if "legacy-addons" in template_name:
                        variant = "legacy-addons"
                    elif "legacy" in template_name:
                        variant = "legacy"
                    elif "asterisk-11" in template_name:
                        variant = "asterisk-11"

                try:
                    config = self.generate_config(version, distribution, variant, os_name=os_name)

                    output_file = f"{output_dir}/asterisk-{version}-{build_slug(os_name, distribution)}.yml"
                    self.save_config(config, output_file)

                    print(f"✅ Generated: {output_file}")
                    total_generated += 1

                except Exception as e:
                    print(f"❌ Failed to generate config for {version}-{distribution}: {e}")

        print(f"\n🎉 Generated {total_generated} configurations using DRY template system")
        return total_generated

if __name__ == "__main__":
    # Test the new generator
    generator = DRYTemplateGenerator()

    # Test with a few versions
    test_versions = ["1.2.40", "11.25.3", "17.9.4", "22.5.2"]

    for version in test_versions:
        try:
            config = generator.generate_config(version)
            output_file = f"test-config-{version}.yml"
            generator.save_config(config, output_file)
            print(f"✅ Test config generated: {output_file}")
        except Exception as e:
            print(f"❌ Test failed for {version}: {e}")

    print("\n🔧 Testing complete! Now generating all supported configurations...")
    generator.generate_all_supported_configs("asterisk/supported-asterisk-builds.yml")