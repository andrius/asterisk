#!/usr/bin/env python3
"""
Dockerfile generator for Asterisk builds.
Uses Jinja2 templates to generate optimized Dockerfiles from YAML configurations.
"""

import os
import json
import yaml
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, Template
from dataclasses import dataclass

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from .menuselect import MenuSelectGenerator
except ImportError:
    from menuselect import MenuSelectGenerator


@dataclass
class BuildContext:
    """Context for Dockerfile generation"""
    config: Dict[str, Any]
    build_packages: List[str]
    runtime_packages: List[str]
    menuselect_config: Any  # MenuSelectConfig
    menuselect_commands: List[str]
    configure_options: List[str]
    is_multi_stage: bool


class DockerfileGenerator:
    """Generates Dockerfiles from YAML configurations"""

    def __init__(self, templates_dir: str, schema_path: str = None):
        self.templates_dir = Path(templates_dir)
        self.schema_path = schema_path
        self.schema = self._load_schema() if schema_path else None

        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        # Add custom filters
        self.jinja_env.filters.update({
            'join_packages': self._join_packages,
            'join_commands': self._join_commands,
            'format_build_arg': self._format_build_arg,
            'quote_shell': self._quote_shell,
            'build_packages_without_ca': self._build_packages_without_ca,
            'unique': lambda x: list(set(x)),
            'sort': lambda x: sorted(x) if isinstance(x, list) else x
        })

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema for validation"""
        if not self.schema_path or not os.path.exists(self.schema_path):
            return None

        with open(self.schema_path, 'r') as f:
            return json.load(f)

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration against schema"""
        if not self.schema or not HAS_JSONSCHEMA:
            return

        try:
            jsonschema.validate(config, self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e.message}")

    def _join_packages(self, packages: List[str], line_length: int = 80) -> str:
        """Format package list for Dockerfile"""
        if not packages:
            return ""

        lines = []
        current_line = "  "

        for pkg in packages:
            if len(current_line + pkg + " \\") > line_length and current_line != "  ":
                lines.append(current_line.rstrip() + " \\")
                current_line = "  "
            current_line += pkg + " "

        if current_line.strip():
            lines.append(current_line.rstrip())

        return "\n".join(lines)

    def _join_commands(self, commands: List[str]) -> str:
        if not commands:
            return ""
        return " && \\\n  ".join(commands)

    def _format_build_arg(self, name: str, value: str) -> str:
        if isinstance(value, bool):
            value = "true" if value else "false"
        return f"ARG {name}={value}"

    def _quote_shell(self, value: str) -> str:
        if ' ' in value or '"' in value or "'" in value:
            escaped_value = value.replace('"', '\\"')
            return f'"{escaped_value}"'
        return value

    def _build_packages_without_ca(self, packages: List[str]) -> List[str]:
        return [pkg for pkg in packages if pkg != 'ca-certificates']

    def _convert_yaml_menuselect_to_commands(self, menuselect_config: Dict[str, Any]) -> List[str]:
        """Convert YAML menuselect configuration to command strings"""
        commands = []

        # Standard menuselect options
        commands.append("menuselect/menuselect --disable BUILD_NATIVE menuselect.makeopts")
        commands.append("menuselect/menuselect --enable BETTER_BACKTRACES menuselect.makeopts")

        # Disable sound/music categories
        commands.append("menuselect/menuselect --disable-category MENUSELECT_CORE_SOUNDS menuselect.makeopts")
        commands.append("menuselect/menuselect --disable-category MENUSELECT_MOH menuselect.makeopts")
        commands.append("menuselect/menuselect --disable-category MENUSELECT_EXTRA_SOUNDS menuselect.makeopts")

        # Enable applications (support both 'apps' and 'enable_apps' keys)
        for app in menuselect_config.get('apps', menuselect_config.get('enable_apps', [])):
            commands.append(f"menuselect/menuselect --enable {app} menuselect.makeopts")

        # Enable channels (support both 'channels' and 'enable_channels' keys)
        for chan in menuselect_config.get('channels', menuselect_config.get('enable_channels', [])):
            commands.append(f"menuselect/menuselect --enable {chan} menuselect.makeopts")

        # Enable resources/drivers (support both 'drivers' and 'enable_resources' keys)
        for res in menuselect_config.get('drivers', menuselect_config.get('enable_resources', [])):
            commands.append(f"menuselect/menuselect --enable {res} menuselect.makeopts")

        # Disable specified modules
        for mod in menuselect_config.get('disable_modules', []):
            commands.append(f"menuselect/menuselect --disable {mod} menuselect.makeopts")

        # Handle exclude list (from old format)
        for mod in menuselect_config.get('exclude', []):
            commands.append(f"menuselect/menuselect --disable {mod} menuselect.makeopts")

        return commands

    def _format_dockerfile(self, dockerfile_content: str) -> str:
        """Format Dockerfile content using dockerfmt"""
        try:
            # Check if Docker is available
            if not shutil.which("docker"):
                print("Warning: Docker not found. Skipping Dockerfile formatting.")
                return dockerfile_content

            # Create temporary file in current working directory (more accessible for Docker)
            current_dir = os.getcwd()
            temp_filename = f".temp_dockerfile_{os.getpid()}_{int(os.urandom(4).hex(), 16)}"
            temp_file_path = os.path.join(current_dir, temp_filename)

            # Write content to file
            with open(temp_file_path, 'w') as f:
                f.write(dockerfile_content)

            try:
                # Run dockerfmt in container
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{current_dir}:/pwd",
                    "ghcr.io/reteps/dockerfmt:latest",
                    "--indent", "4",
                    "--newline",
                    f"/pwd/{temp_filename}"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return result.stdout
                else:
                    print(f"Warning: dockerfmt failed with exit code {result.returncode}: {result.stderr}")
                    return dockerfile_content

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except subprocess.TimeoutExpired:
            print("Warning: dockerfmt timed out. Skipping formatting.")
            return dockerfile_content
        except Exception as e:
            print(f"Warning: dockerfmt formatting failed: {e}. Skipping formatting.")
            return dockerfile_content

    def load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if self.schema:
            self._validate_config(config)

        return config

    def prepare_build_context(self, config: Dict[str, Any]) -> BuildContext:
        """Prepare build context from configuration"""
        try:
            version = config["version"]
            base_config = config["base"]
            build_config = config.get("build", {})
            asterisk_config = config.get("asterisk", {})
            features = config.get("features", {})

            # Get packages from config (support both old and new formats)
            packages_config = config.get("packages", {})
            if packages_config:
                # New template format: packages.build / packages.runtime
                build_packages = packages_config.get("build", [])
                runtime_packages = packages_config.get("runtime", [])
            else:
                # Old generated format: build.stages.builder.packages / build.stages.runtime.packages
                stages = build_config.get("stages", {})
                builder_packages = stages.get("builder", {}).get("packages", [])
                runtime_packages = stages.get("runtime", {}).get("packages", [])
                build_packages = builder_packages

            # Generate menuselect commands
            # Priority: Use YAML menuselect config if available, otherwise generate from features
            yaml_menuselect = asterisk_config.get("menuselect", {})
            if yaml_menuselect and any(yaml_menuselect.get(k) for k in ['apps', 'channels', 'drivers', 'enable_apps', 'enable_channels', 'enable_resources']):
                # Use YAML-based menuselect configuration
                menuselect_commands = self._convert_yaml_menuselect_to_commands(yaml_menuselect)
                menuselect_config = None  # Not needed when using YAML directly
            else:
                # Fall back to MenuSelectGenerator for legacy configs
                menuselect_generator = MenuSelectGenerator(version)
                menuselect_config = menuselect_generator.generate_config(features)
                menuselect_commands = menuselect_generator.generate_menuselect_commands(menuselect_config)

            # Get configure options from config
            configure_options = asterisk_config.get("menuselect", {}).get("configure_options", [])
            if asterisk_config.get("configure", {}).get("options"):
                configure_options = asterisk_config["configure"]["options"]

            # Determine build characteristics from version
            if version == 'git' or version.startswith('git-'):
                # Git versions are always modern (latest)
                major_version = 99
                is_legacy_version = False
            else:
                major_version = int(version.split('.')[0])
                is_legacy_version = major_version < 10

            is_multi_stage = build_config.get("type", "multi-stage") == "multi-stage"

            # Add backward compatibility for templates expecting build.stages structure
            if not build_config.get("stages") and packages_config:
                # Create stages structure for template compatibility
                build_config["stages"] = {
                    "builder": {"packages": build_packages},
                    "runtime": {"packages": runtime_packages, "slim": True}
                }

            # Only override addons if not already configured (preserve legacy addons settings)
            if not asterisk_config.get("addons"):
                asterisk_config["addons"] = {"version": None}

            # Add backward compatibility for templates expecting asterisk.source structure
            if not asterisk_config.get("source"):
                asterisk_config["source"] = {
                    "url_template": "https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-{version}.tar.gz"
                }

            # Add backward compatibility for templates expecting features structure
            if not config.get("features"):
                config["features"] = {
                    "recordings": True,
                    "hep": True,
                    "pjsip": True,
                    "ari": True
                }

            # Add backward compatibility for templates expecting docker.healthcheck structure
            docker_config = config.get("docker", {})
            if not docker_config.get("healthcheck"):
                docker_config["healthcheck"] = {
                    "enabled": True,
                    "command": "/usr/local/bin/healthcheck.sh",
                    "interval": "30s",
                    "timeout": "10s",
                    "start_period": "30s",
                    "retries": 3
                }

            # Add backward compatibility for templates expecting docker.networking structure
            if not docker_config.get("networking"):
                docker_config["networking"] = {
                    "ports": ["5060/udp", "5060/tcp", "5061/tcp", "10000-10099/udp"]
                }

            config["docker"] = docker_config

            return BuildContext(
                config=config,
                build_packages=build_packages,
                runtime_packages=runtime_packages,
                menuselect_config=menuselect_config,
                menuselect_commands=menuselect_commands,
                configure_options=configure_options,
                is_multi_stage=is_multi_stage
            )
        except Exception as e:
            raise ValueError(f"Error preparing build context: {e}")

    def generate_dockerfile(self, config_path: str, output_path: str = None,
                          template_name: str = None, format_dockerfile: bool = True) -> str:
        """Generate Dockerfile from configuration"""
        config = self.load_config(config_path)
        context = self.prepare_build_context(config)

        # Determine template to use
        if not template_name:
            # Check if this is a git build
            if (config.get("asterisk", {}).get("source_type") == "git" or
                config.get("variant") == "git-dev" or
                config.get("version", "").startswith("git-")):
                template_name = "git-dev.dockerfile.j2"
            elif context.is_multi_stage:
                template_name = "multi-stage.dockerfile.j2"
            else:
                template_name = "single-stage.dockerfile.j2"

        # Load template
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception as e:
            raise ValueError(f"Template '{template_name}' not found: {e}")

        # Extract git SHA for git builds
        git_sha = None
        version = context.config["version"]
        if version.startswith("git-"):
            git_sha = version.replace("git-", "")

        # Render Dockerfile
        dockerfile_content = template.render(
            config=context.config,
            menuselect_commands=context.menuselect_commands,
            configure_options=context.configure_options,
            is_multi_stage=context.is_multi_stage,
            # Helper functions
            version=version,
            git_sha=git_sha,
            base_image=context.config["base"]["image"],
            build_packages=context.build_packages,
            runtime_packages=context.runtime_packages,
            # Metadata
            maintainer=context.config.get("metadata", {}).get("maintainer", "Andrius Kairiukstis <k@andrius.mobi>"),
            # Features
            **context.config.get("features", {})
        )

        # Apply formatting if requested
        if format_dockerfile:
            dockerfile_content = self._format_dockerfile(dockerfile_content)

        # Write to file if output path specified
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directory if there is one
                os.makedirs(output_dir, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(dockerfile_content)

        return dockerfile_content

    def generate_docker_compose(self, config_path: str, output_path: str = None) -> str:
        """Generate docker-compose.yml from configuration"""
        config = self.load_config(config_path)

        template = self.jinja_env.get_template("docker-compose.yml.j2")
        compose_content = template.render(config=config)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(compose_content)

        return compose_content

    def generate_build_script(self, config_path: str, output_path: str = None) -> str:
        """Generate build script from configuration"""
        config = self.load_config(config_path)
        context = self.prepare_build_context(config)

        # Check configuration to determine appropriate build script template
        menuselect_config = context.config.get("asterisk", {}).get("menuselect", {})
        is_minimal = menuselect_config.get("minimal", False)
        addons_config = context.config.get("asterisk", {}).get("addons")
        has_addons = addons_config and addons_config.get("version")

        # Use appropriate build script template (addons takes precedence over minimal)
        if has_addons:
            template = self.jinja_env.get_template("partials/build-legacy-addons.sh.j2")
        elif is_minimal:
            template = self.jinja_env.get_template("partials/build-legacy.sh.j2")
        else:
            template = self.jinja_env.get_template("partials/build.sh.j2")

        script_content = template.render(
            config=context.config,
            menuselect_commands=context.menuselect_commands,
            configure_options=context.configure_options,
            # Additional context
            version=context.config["version"],
            build_opt=context.config.get("build", {}).get("optimization", {}),
            # Features
            **context.config.get("features", {})
        )

        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directory if there is one
                os.makedirs(output_dir, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(script_content)
            os.chmod(output_path, 0o755)  # Make executable

        return script_content

    def list_templates(self) -> List[str]:
        """List available templates"""
        templates = []
        for template_file in self.templates_dir.rglob("*.j2"):
            templates.append(str(template_file.relative_to(self.templates_dir)))
        return sorted(templates)

    def validate_template(self, template_name: str) -> bool:
        """Validate that template exists and can be loaded"""
        try:
            self.jinja_env.get_template(template_name)
            return True
        except Exception:
            return False


class BatchGenerator:
    """Batch generator for multiple configurations"""

    def __init__(self, generator: DockerfileGenerator):
        self.generator = generator

    def generate_from_directory(self, configs_dir: str, output_dir: str,
                              template_name: str = None, format_dockerfile: bool = True) -> Dict[str, str]:
        """Generate Dockerfiles for all configs in directory"""
        results = {}
        configs_path = Path(configs_dir)
        output_path = Path(output_dir)

        for config_file in configs_path.glob("*.yml"):
            try:
                # Determine output filename
                output_file = output_path / f"{config_file.stem}.Dockerfile"

                # Generate Dockerfile
                content = self.generator.generate_dockerfile(
                    str(config_file),
                    str(output_file),
                    template_name,
                    format_dockerfile
                )

                results[str(config_file)] = str(output_file)
                print(f"Generated: {config_file.name} -> {output_file.name}")

            except Exception as e:
                print(f"Error generating {config_file.name}: {e}")
                results[str(config_file)] = f"ERROR: {e}"

        return results

    def generate_matrix_builds(self, versions: List[str], distributions: List[str],
                             output_dir: str, base_config: Dict[str, Any] = None) -> List[str]:
        """Generate build matrix for versions x distributions"""
        base_config = base_config or {}
        generated_files = []

        for version in versions:
            for distribution in distributions:
                # Create config for this combination
                config = {
                    "version": version,
                    "base": {
                        "os": "debian",
                        "distribution": distribution,
                        "image": f"debian:{distribution}"
                    },
                    **base_config
                }

                # Write temporary config
                config_file = f"temp_{version}_{distribution}.yml"
                with open(config_file, 'w') as f:
                    yaml.dump(config, f)

                try:
                    # Generate Dockerfile
                    output_file = Path(output_dir) / f"asterisk-{version}-{distribution}.Dockerfile"
                    self.generator.generate_dockerfile(config_file, str(output_file))
                    generated_files.append(str(output_file))

                finally:
                    # Clean up temp file
                    if os.path.exists(config_file):
                        os.remove(config_file)

        return generated_files


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python dockerfile_generator.py <config.yml> <output.Dockerfile>")
        sys.exit(1)

    config_path = sys.argv[1]
    output_path = sys.argv[2]

    # Set up generator
    script_dir = Path(__file__).parent.parent
    templates_dir = script_dir / "templates" / "dockerfile"
    schema_path = script_dir / "schema" / "build-config.schema.json"

    generator = DockerfileGenerator(str(templates_dir), str(schema_path))

    try:
        dockerfile_content = generator.generate_dockerfile(config_path, output_path)
        print(f"Generated Dockerfile: {output_path}")
        print(f"Size: {len(dockerfile_content)} characters")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()