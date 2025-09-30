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

@dataclass
class TemplateContext:
    """Context for template resolution"""
    version: str
    distribution: str
    variant: str
    base_packages: Dict[str, List[str]]
    distribution_config: Dict[str, Any]
    variant_config: Dict[str, Any]

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

    def _load_distribution_config(self, distribution: str) -> Dict[str, Any]:
        """Load distribution-specific configuration"""
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

        # Remove duplicates while preserving order
        packages["build"] = list(dict.fromkeys(packages["build"]))
        packages["runtime"] = list(dict.fromkeys(packages["runtime"]))

        return packages

    def _resolve_asterisk_config(self, context: TemplateContext) -> Dict[str, Any]:
        """Resolve Asterisk configuration with inheritance"""
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

        return base_config

    def _substitute_variables(self, config: Dict[str, Any], context: TemplateContext) -> Dict[str, Any]:
        """Substitute template variables throughout the configuration"""
        config_str = yaml.dump(config)

        # Substitute variables
        config_str = config_str.replace("{{VERSION}}", context.version)
        config_str = config_str.replace("{{DISTRIBUTION}}", context.distribution)
        config_str = config_str.replace("{{VARIANT}}", context.variant)

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

    def _apply_version_overrides(self, config: Dict[str, Any], version: str) -> Dict[str, Any]:
        """Apply version-specific overrides to configuration"""
        import re

        # Parse version to determine major version
        if version == 'git' or version.startswith('git-'):
            major = 99  # Treat git as latest
        else:
            base_version = version.split('-cert')[0]
            match = re.match(r'^(\d+)\.(\d+)', base_version)
            if match:
                major = int(match.group(1))
            else:
                return config  # Can't parse, skip overrides

        # Only apply overrides to modern versions (12+)
        if major < 12:
            return config

        # Ensure asterisk.menuselect structure exists
        if "asterisk" not in config:
            config["asterisk"] = {}
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

        return config

    def generate_config(self, version: str, distribution: str = None, variant: str = None) -> Dict[str, Any]:
        """Generate complete configuration using DRY template system"""

        # Auto-detect distribution and variant if not provided
        if distribution is None:
            distribution = self._determine_distribution(version)
        if variant is None:
            variant = self._determine_variant(version)

        print(f"Generating config for {version} (distribution: {distribution}, variant: {variant})")

        # Load configurations
        distribution_config = self._load_distribution_config(distribution)
        variant_config = self._load_variant_template(variant)

        # Create context
        context = TemplateContext(
            version=version,
            distribution=distribution,
            variant=variant,
            base_packages=self.base_packages,
            distribution_config=distribution_config,
            variant_config=variant_config
        )

        # Build final configuration
        config = {
            "version": version,
            "base": self._resolve_base_config(context),
            "packages": self._resolve_packages(context),
            "asterisk": self._resolve_asterisk_config(context),
            "docker": self._resolve_docker_config(context),
            "build": self.base_template.get("build", {})
        }

        # Add EOL setup if needed
        if distribution_config.get("eol"):
            config["packages"]["eol_setup"] = distribution_config.get("eol_setup", [])

        # Add features if defined
        if "features" in variant_config:
            config["features"] = variant_config["features"]

        # Substitute variables
        config = self._substitute_variables(config, context)

        # Apply version-specific overrides
        config = self._apply_version_overrides(config, version)

        return config

    def save_config(self, config: Dict[str, Any], output_path: str):
        """Save generated configuration to file"""
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if there is one
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def generate_and_save_config(self, version: str, distribution: str, output_path: str) -> bool:
        """Generate and save configuration in one step"""
        try:
            config = self.generate_config(version, distribution)
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
                    config = self.generate_config(version, distribution, variant)

                    output_file = f"{output_dir}/asterisk-{version}-{distribution}.yml"
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