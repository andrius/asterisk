#!/usr/bin/env python3
"""
Generate YAML config files from templates for Asterisk Docker builds.

This script processes template files by replacing {{VERSION}} placeholders
with actual Asterisk version numbers and outputs the generated configuration
to the configs/generated/ directory.
"""

import argparse
import os
import sys
import yaml
from pathlib import Path


def get_addons_version(asterisk_version):
    """
    Map Asterisk version to correct addons version.

    Args:
        asterisk_version (str): Asterisk version (e.g., "1.4.44", "1.6.2.18")

    Returns:
        str: Corresponding addons version
    """
    major_version = asterisk_version.split('.')[0] + '.' + asterisk_version.split('.')[1]

    addons_mapping = {
        '1.2': '1.2.9',
        '1.4': '1.4.9',
        '1.6': '1.6.2.4'
    }

    return addons_mapping.get(major_version, asterisk_version)


def generate_config_from_template(template_path, version, output_path):
    """
    Generate a config file from a template by replacing version placeholder.

    Args:
        template_path (str): Path to the template file
        version (str): Asterisk version to substitute
        output_path (str): Path where generated config should be saved

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read template file
        with open(template_path, 'r') as f:
            template_content = f.read()

        # Determine addons version for legacy versions
        addons_version = get_addons_version(version)

        # Replace version placeholder
        config_content = template_content.replace('{{VERSION}}', version)

        # Handle addons version mapping for legacy templates
        if '{{ADDONS_VERSION}}' in config_content:
            config_content = config_content.replace('{{ADDONS_VERSION}}', addons_version)

        # Validate generated YAML and modify for certified versions
        try:
            config_data = yaml.safe_load(config_content)
        except yaml.YAMLError as e:
            print(f"ERROR: Generated config is not valid YAML: {e}", file=sys.stderr)
            return False

        # Add certified Asterisk URL template logic
        if 'asterisk' not in config_data:
            config_data['asterisk'] = {}

        if 'source' not in config_data['asterisk']:
            # Detect certified versions and use appropriate URL
            if '-cert' in version:
                url_template = 'https://downloads.asterisk.org/pub/telephony/certified-asterisk/releases/asterisk-certified-{version}.tar.gz'
            else:
                url_template = 'https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-{version}.tar.gz'

            config_data['asterisk']['source'] = {
                'url_template': url_template
            }

        # Disable addons for certified versions (they're self-contained)
        if '-cert' in version and 'addons' in config_data['asterisk']:
            config_data['asterisk']['addons'] = {'version': None}

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write generated config with URL template
        with open(output_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        return True

    except FileNotFoundError:
        print(f"ERROR: Template file not found: {template_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Failed to generate config: {e}", file=sys.stderr)
        return False


def find_template_for_distribution(templates_dir, distribution, template_name=None):
    """
    Find the appropriate template file for a given distribution.

    Args:
        templates_dir (str): Directory containing template files
        distribution (str): Distribution name (e.g., 'trixie', 'bookworm')
        template_name (str, optional): Specific template name to use

    Returns:
        str: Path to template file, or None if not found
    """
    # If specific template name is provided, use it directly
    if template_name:
        template_file = f"{template_name}.yml.template"
        template_path = os.path.join(templates_dir, template_file)
        if os.path.exists(template_path):
            return template_path
        # If specific template doesn't exist, it's an error
        return None

    # Default behavior: look for distribution-specific template
    template_name = f"debian-{distribution}.yml.template"
    template_path = os.path.join(templates_dir, template_name)

    if os.path.exists(template_path):
        return template_path

    # Fallback to base template if specific distribution template doesn't exist
    base_template = os.path.join(templates_dir, "base.yml.template")
    if os.path.exists(base_template):
        return base_template

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate Asterisk Docker build config from template"
    )
    parser.add_argument(
        'version',
        help='Asterisk version (e.g., 18.26.4, 22.5.2)'
    )
    parser.add_argument(
        'distribution',
        help='Distribution name (e.g., trixie, bookworm)'
    )
    parser.add_argument(
        '--templates-dir',
        default='templates',
        help='Directory containing template files (default: templates)'
    )
    parser.add_argument(
        '--output-dir',
        default='configs/generated',
        help='Output directory for generated configs (default: configs/generated)'
    )
    parser.add_argument(
        '--output',
        help='Specific output file path (overrides --output-dir)'
    )
    parser.add_argument(
        '--template',
        help='Specific template name to use (without .yml.template extension)'
    )

    args = parser.parse_args()

    # Find template file
    template_path = find_template_for_distribution(args.templates_dir, args.distribution, args.template)
    if not template_path:
        if args.template:
            print(f"ERROR: Specified template '{args.template}' not found", file=sys.stderr)
            print(f"Looked for: {args.template}.yml.template", file=sys.stderr)
        else:
            print(f"ERROR: No template found for distribution '{args.distribution}'", file=sys.stderr)
            print(f"Looked for: debian-{args.distribution}.yml.template", file=sys.stderr)
        return 1

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_filename = f"asterisk-{args.version}-{args.distribution}.yml"
        output_path = os.path.join(args.output_dir, output_filename)

    # Generate config
    if generate_config_from_template(template_path, args.version, output_path):
        print(f"Generated config: {output_path}")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())