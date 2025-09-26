#!/usr/bin/env python3
"""
Get expected image name for Asterisk version based on build matrix
"""

import yaml
import sys

def get_image_name(version, builds_file="asterisk/supported-asterisk-builds.yml"):
    """Get the expected Docker image name for a given Asterisk version"""
    try:
        with open(builds_file, 'r') as f:
            data = yaml.safe_load(f)

        for build in data.get('latest_builds', []):
            if build['version'] == version:
                os_matrix = build.get('os_matrix', [])
                if os_matrix:
                    # Get the first (and usually only) matrix entry
                    matrix_entry = os_matrix[0]
                    distribution = matrix_entry['distribution']
                    return f"{version}_debian-{distribution}"

        # Fallback - shouldn't happen for supported versions
        return f"{version}_debian-unknown"

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return f"{version}_debian-unknown"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 get-image-name.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    image_name = get_image_name(version)
    print(image_name)