#!/usr/bin/env python3
"""
Generate YAML config files from DRY templates for Asterisk Docker builds.

This script uses the enhanced template system with inheritance support,
automatically detecting variants and distributions for optimal configuration.
"""

import argparse
import os
import sys
from pathlib import Path

# Add lib directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
lib_dir = os.path.join(project_dir, 'lib')
sys.path.insert(0, lib_dir)

from template_generator import DRYTemplateGenerator


# DRY template system handles all template logic internally


def main():
    parser = argparse.ArgumentParser(
        description="Generate Asterisk Docker build config from DRY templates"
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
        help='Specific template name to use (for backward compatibility, ignored in DRY mode)'
    )

    args = parser.parse_args()

    try:
        # Initialize DRY template generator
        generator = DRYTemplateGenerator(args.templates_dir)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            output_filename = f"asterisk-{args.version}-{args.distribution}.yml"
            output_path = os.path.join(args.output_dir, output_filename)

        # Create output directory if it doesn't exist (skip if output_path is just a filename)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Generate and save config using DRY template system
        success = generator.generate_and_save_config(args.version, args.distribution, output_path)

        if success:
            print(f"Generated config: {output_path}")
            return 0
        else:
            print("ERROR: Failed to generate config", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())