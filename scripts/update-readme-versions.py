#!/usr/bin/env python3
"""
Update README.md Supported Versions table from supported-asterisk-builds.yml

Usage:
    python3 scripts/update-readme-versions.py           # Update README
    python3 scripts/update-readme-versions.py --dry-run # Preview changes
"""

import yaml
import re
import sys
from pathlib import Path


def version_sort_key(version):
    """
    Generate sort key for version string.
    Returns tuple for sorting: (major, minor, patch, cert_num)
    'git' always sorts first (highest).

    Examples:
      git → (999, 0, 0, 0)
      23.0.0 → (23, 0, 0, 0)
      20.7-cert7 → (20, 7, 0, 7)
      1.2.40 → (1, 2, 40, 0)
    """
    if version == "git":
        return (999, 0, 0, 0)

    try:
        # Split on "-cert" first to separate version from cert number
        if "-cert" in version:
            version_part, cert_part = version.split("-cert")
            cert = int(cert_part)
        else:
            version_part = version
            cert = 0

        # Split version on "." to get major.minor.patch
        parts = version_part.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return (major, minor, patch, cert)
    except (ValueError, IndexError):
        # Fallback for malformed versions
        print(f"⚠️  Warning: Could not parse version '{version}', sorting to end", file=sys.stderr)
        return (0, 0, 0, 0)


def calculate_version_metrics(builds):
    """
    Calculate version statistics from builds data.

    Returns:
        dict with keys: total, oldest, latest, has_git
    """
    # Filter enabled versions (those with os_matrix)
    enabled = [b for b in builds if b.get('os_matrix')]

    # Separate git from versioned releases
    versioned = [b['version'] for b in enabled if b.get('version') != 'git']
    has_git = any(b.get('version') == 'git' for b in enabled)

    # Sort using existing version_sort_key function
    sorted_versions = sorted(versioned, key=version_sort_key)

    return {
        'total': len(enabled),
        'oldest': sorted_versions[0] if sorted_versions else None,
        'latest': sorted_versions[-1] if sorted_versions else None,
        'has_git': has_git
    }


def update_readme_intro(readme_path, metrics, dry_run=False):
    """
    Update line 3 of README with dynamic version range.

    Expected format:
    "Production-ready Docker images for Asterisk PBX with advanced DRY
     template system, supporting N versions from X.X.X to Y.Y.Y plus git
     development builds."
    """
    try:
        with open(readme_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {readme_path}", file=sys.stderr)
        return False

    if len(lines) < 3:
        print("❌ ERROR: README.md has fewer than 3 lines", file=sys.stderr)
        return False

    # Build new intro text
    git_suffix = " plus git development builds" if metrics['has_git'] else ""
    new_text = (
        f"supporting {metrics['total']} versions "
        f"from {metrics['oldest']} to {metrics['latest']}{git_suffix}"
    )

    # Replace on line 3 (index 2)
    line = lines[2]
    if 'supporting' in line:
        # Find and replace the "supporting..." portion
        start_idx = line.index('supporting')

        # Find the end: look for period after "builds" or "git" or version number
        # This pattern handles: "supporting X versions from Y to Z plus git development builds."
        # or "supporting X versions from Y to Z."
        remaining = line[start_idx:]
        if 'builds.' in remaining:
            end_offset = remaining.index('builds.') + len('builds.')
        elif 'git development builds' in remaining:
            end_offset = remaining.index('git development builds') + len('git development builds')
            if '.' in remaining[end_offset:end_offset+2]:
                end_offset += 1
        else:
            # Fallback: find first period
            end_offset = remaining.index('.') + 1 if '.' in remaining else len(remaining.rstrip())

        end_idx = start_idx + end_offset

        prefix = line[:start_idx]
        suffix = line[end_idx:] if end_idx < len(line) else '\n'

        lines[2] = f"{prefix}{new_text}.{suffix}"

        if not dry_run:
            with open(readme_path, 'w') as f:
                f.writelines(lines)
            print(f"✅ Updated intro text: {new_text}")
            return True
        else:
            print(f"🔍 Would update intro: {new_text}")
            return False
    else:
        print("⚠️  Warning: Line 3 doesn't contain 'supporting', skipping intro update", file=sys.stderr)
        return False


def load_supported_builds(yaml_path):
    """Load and parse supported-asterisk-builds.yml"""
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        if 'latest_builds' not in data:
            print(f"❌ ERROR: 'latest_builds' not found in {yaml_path}", file=sys.stderr)
            sys.exit(1)

        return data['latest_builds']
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {yaml_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ ERROR: Invalid YAML: {e}", file=sys.stderr)
        sys.exit(1)


def generate_version_table(builds):
    """Generate markdown table from build data"""

    # Extract version data
    versions = []
    for build in builds:
        version = build.get('version')
        if not version:
            continue

        # Get tags
        tags = build.get('additional_tags', '-')

        # Get distribution and architectures from first os_matrix entry
        os_matrix = build.get('os_matrix', [])
        if not os_matrix:
            continue

        # Handle both list and dict os_matrix formats
        if isinstance(os_matrix, dict):
            matrix_entry = os_matrix
        else:
            matrix_entry = os_matrix[0]

        distribution = matrix_entry.get('distribution', 'N/A')
        architectures = matrix_entry.get('architectures', [])

        # Format architectures as comma-separated string
        if isinstance(architectures, list):
            arch_str = ', '.join(architectures)
        else:
            arch_str = str(architectures)

        versions.append({
            'version': version,
            'tags': tags,
            'distribution': distribution.title(),  # Capitalize: trixie → Trixie
            'architectures': arch_str
        })

    # Sort versions (newest first)
    versions.sort(key=lambda v: version_sort_key(v['version']), reverse=True)

    # Generate markdown table
    lines = []
    lines.append("| Version | Tags | Distribution | Architectures |")
    lines.append("| ------- | ---- | ------------ | ------------- |")

    for v in versions:
        # Format tags: if they contain commas, wrap in backticks for readability
        tags = v['tags']
        if ',' in tags and tags != '-':
            tags = f"`{tags}`"

        lines.append(f"| **{v['version']}** | {tags} | {v['distribution']} | {v['architectures']} |")

    return '\n'.join(lines)


def update_readme(readme_path, new_table, dry_run=False):
    """Update README.md with new versions table"""

    try:
        with open(readme_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {readme_path}", file=sys.stderr)
        sys.exit(1)

    # Find the Supported Versions section
    # Pattern: ## Supported Versions ... content ... ## (next section)
    pattern = r'(## Supported Versions\n\n)(.*?)(\n\n## )'

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("❌ ERROR: Could not find '## Supported Versions' section in README.md", file=sys.stderr)
        sys.exit(1)

    # Extract the intro text (before the table)
    intro_text = "All supported Asterisk versions with automatic variant detection. Generated build artifacts are placed in `asterisk/VERSION-DIST/` directories (not tracked in git).\n\n"

    # Build new section content
    new_content = match.group(1) + intro_text + new_table + match.group(3)

    # Replace in content
    updated_content = content[:match.start()] + new_content + content[match.end():]

    if dry_run:
        print("🔍 DRY RUN - Changes that would be made:")
        print("\n" + "="*60)
        print(new_table)
        print("="*60)
        print(f"\n✅ Would update {readme_path}")
        return False
    else:
        # Write updated content
        with open(readme_path, 'w') as f:
            f.write(updated_content)
        print(f"✅ Updated {readme_path}")
        return True


def main():
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv

    # Paths
    repo_root = Path(__file__).parent.parent
    yaml_path = repo_root / 'asterisk' / 'supported-asterisk-builds.yml'
    readme_path = repo_root / 'README.md'

    print(f"📋 Reading {yaml_path}")
    builds = load_supported_builds(yaml_path)
    print(f"✅ Found {len(builds)} versions")

    # Calculate version metrics
    print("📊 Calculating version metrics...")
    metrics = calculate_version_metrics(builds)
    print(f"   Total enabled: {metrics['total']}")
    print(f"   Range: {metrics['oldest']} to {metrics['latest']}")

    # Update intro text
    print(f"📝 Updating intro text in {readme_path}...")
    intro_updated = update_readme_intro(readme_path, metrics, dry_run)

    # Generate and update table
    print("📊 Generating markdown table...")
    table = generate_version_table(builds)

    print(f"📝 Updating table in {readme_path}...")
    table_updated = update_readme(readme_path, table, dry_run)

    if intro_updated or table_updated:
        print("\n✅ README.md updated successfully!")
    elif dry_run:
        print("\n💡 Run without --dry-run to apply changes")

    sys.exit(0)


if __name__ == '__main__':
    main()
