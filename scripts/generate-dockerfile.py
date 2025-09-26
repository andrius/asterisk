#!/usr/bin/env python3
"""
Generate Dockerfile from YAML configuration.
Main script for the Dockerfile generation system.
"""

import os
import sys
import argparse
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from dockerfile_generator import DockerfileGenerator, BatchGenerator


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate Dockerfiles from YAML configurations",
        epilog="""
Examples:
  %(prog)s config.yml --output Dockerfile
  %(prog)s config.yml --generate-compose --generate-script
  %(prog)s --batch configs/generated --batch-output dockerfiles/
  %(prog)s --list-templates
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("config", nargs="?",
                       help="Path to YAML configuration file")
    parser.add_argument("--output", "-o",
                       help="Output Dockerfile path")
    parser.add_argument("--template", "-t",
                       help="Template to use (default: auto-detect)")
    parser.add_argument("--templates-dir", default="../templates/dockerfile",
                       help="Templates directory")
    parser.add_argument("--schema", default="../schema/build-config.schema.json",
                       help="JSON schema for validation")

    # Batch operations
    parser.add_argument("--batch", "-b",
                       help="Generate from all configs in directory")
    parser.add_argument("--batch-output", default="./dockerfiles",
                       help="Output directory for batch generation")

    # Utility operations
    parser.add_argument("--list-templates", action="store_true",
                       help="List available templates")
    parser.add_argument("--validate", action="store_true",
                       help="Validate configuration only")
    parser.add_argument("--generate-compose", action="store_true",
                       help="Also generate docker-compose.yml")
    parser.add_argument("--generate-script", action="store_true",
                       help="Also generate build script")
    parser.add_argument("--skip-format-dockerfile", action="store_true",
                       help="Skip formatting generated Dockerfile with dockerfmt (default: format enabled)")

    args = parser.parse_args()

    # Show help if no arguments provided and no utility options
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Resolve paths
    script_dir = Path(__file__).parent.parent
    templates_dir = (script_dir / args.templates_dir).resolve()
    schema_path = (script_dir / args.schema).resolve() if args.schema else None

    # Initialize generator
    try:
        generator = DockerfileGenerator(str(templates_dir), str(schema_path) if schema_path else None)
    except Exception as e:
        print(f"Error initializing generator: {e}")
        sys.exit(1)

    # List templates
    if args.list_templates:
        templates = generator.list_templates()
        print("Available templates:")
        for template in templates:
            print(f"  {template}")
        return

    # Batch generation
    if args.batch:
        batch_generator = BatchGenerator(generator)
        print(f"Generating Dockerfiles from configs in: {args.batch}")

        results = batch_generator.generate_from_directory(
            args.batch,
            args.batch_output,
            args.template,
            not args.skip_format_dockerfile
        )

        # Summary
        total = len(results)
        success = len([r for r in results.values() if not r.startswith("ERROR")])
        errors = total - success

        print(f"\nBatch generation summary:")
        print(f"  Total: {total}")
        print(f"  Success: {success}")
        print(f"  Errors: {errors}")

        if errors > 0:
            print(f"\nErrors:")
            for config_file, result in results.items():
                if result.startswith("ERROR"):
                    print(f"  {Path(config_file).name}: {result}")

        return

    # Single config generation
    if not args.config:
        parser.print_help()
        sys.exit(1)

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    # Validate only
    if args.validate:
        try:
            config = generator.load_config(str(config_path))
            print(f"✓ Configuration is valid: {config_path.name}")
            print(f"  Version: {config['version']}")
            print(f"  Base: {config['base']['os']} {config['base']['distribution']}")
            return
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            sys.exit(1)

    # Generate output path if not specified
    if not args.output:
        args.output = config_path.with_suffix('.Dockerfile')

    try:
        # Generate Dockerfile
        print(f"Generating Dockerfile from: {config_path.name}")
        dockerfile_content = generator.generate_dockerfile(
            str(config_path),
            str(args.output),
            args.template,
            not args.skip_format_dockerfile
        )

        print(f"Generated: {args.output}")
        print(f"Size: {len(dockerfile_content)} characters")

        # Generate docker-compose.yml if requested
        if args.generate_compose:
            compose_output = args.output.parent / "docker-compose.yml"
            compose_content = generator.generate_docker_compose(
                str(config_path),
                str(compose_output)
            )
            print(f"Generated: {compose_output}")

        # Generate build script if requested
        if args.generate_script:
            script_output = args.output.parent / "build.sh"
            script_content = generator.generate_build_script(
                str(config_path),
                str(script_output)
            )
            print(f"Generated: {script_output}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()