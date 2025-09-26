#!/usr/bin/env python3
"""
Asterisk menuselect configuration logic.
Handles module selection based on version and features.
"""

import re
from typing import Dict, List, Set
from dataclasses import dataclass
from enum import Enum


class ModuleCategory(Enum):
    """Asterisk module categories"""
    CHANNELS = "channels"
    APPLICATIONS = "applications"
    RESOURCES = "resources"
    FORMATS = "formats"
    CODECS = "codecs"
    BRIDGES = "bridges"
    CDR = "cdr"
    CEL = "cel"
    FUNCS = "funcs"
    PBX = "pbx"


@dataclass
class MenuSelectConfig:
    """Configuration for Asterisk menuselect"""
    enable: List[str]
    disable: List[str]
    disable_categories: List[str]


class MenuSelectGenerator:
    """Generates Asterisk menuselect configurations"""

    # Module sets by category and version support
    CHANNEL_MODULES = {
        "modern": [
            "chan_pjsip",      # SIP via PJSIP (12+)
            "chan_iax2",       # IAX2 protocol
            "chan_local",      # Local channels
            "chan_bridge_media", # Bridge media channels
            "chan_websocket"   # WebSocket channels (22+)
        ],
        "legacy": [
            "chan_sip",        # Legacy SIP (deprecated in 17+)
            "chan_iax2",       # IAX2 protocol
            "chan_local",      # Local channels
            "chan_zap"         # Zaptel (very old versions)
        ],
        "optional": [
            "chan_dahdi",      # DAHDI hardware
            "chan_audiosocket", # AudioSocket external media
            "chan_console"     # Console channel
        ]
    }

    APPLICATION_MODULES = {
        "core": [
            "app_dial",        # Dial application
            "app_playback",    # Playback audio
            "app_record",      # Record audio
            "app_echo",        # Echo test
            "app_hangup",      # Hangup call
            "app_noop",        # No operation
            "app_verbose",     # Verbose logging
            "app_waitexten"    # Wait for extension
        ],
        "voicemail": [
            "app_voicemail",   # Voicemail system
            "app_voicemailmain" # Voicemail main menu
        ],
        "conferencing": [
            "app_confbridge",  # Conference bridge (10+)
            "app_meetme"       # MeetMe (legacy conferencing)
        ],
        "call_features": [
            "app_queue",       # Call queues
            "app_directory",   # Directory lookup
            "app_followme",    # Follow me
            "app_forkcdr",     # Fork CDR
            "app_mixmonitor",  # Call monitoring
            "app_monitor"      # Legacy monitoring
        ],
        "control": [
            "app_if",          # Conditional execution
            "app_while",       # While loops
            "app_goto",        # Goto application
            "app_gosub",       # Gosub application
            "app_return",      # Return from gosub
            "app_stack"        # Stack operations
        ],
        "integration": [
            "app_system",      # System command execution
            "app_exec",        # Execute application
            "app_audiosocket"  # AudioSocket integration
        ]
    }

    RESOURCE_MODULES = {
        "core": [
            "res_timing_timerfd", # Timer interface
            "res_crypto",         # Cryptographic functions
            "res_format_attr",    # Format attributes
            "res_rtp_asterisk",   # RTP implementation
            "res_musiconhold"     # Music on hold
        ],
        "pjsip": [
            "res_pjsip",                    # PJSIP stack
            "res_pjsip_session",            # PJSIP sessions
            "res_pjsip_registrar",          # PJSIP registrar
            "res_pjsip_outbound_registration", # Outbound registration
            "res_pjsip_endpoint_identifier_user", # User identification
            "res_pjsip_endpoint_identifier_ip",   # IP identification
            "res_pjsip_authenticator_digest",     # Digest authentication
            "res_pjsip_caller_id",              # Caller ID
            "res_pjsip_transport_websocket"     # WebSocket transport
        ],
        "database": [
            "res_config_pgsql",   # PostgreSQL configuration
            "res_config_odbc",    # ODBC configuration
            "res_odbc",           # ODBC resource
            "res_config_curl"     # HTTP configuration
        ],
        "cdr_cel": [
            "res_cdr",            # CDR core
            "res_cel"             # CEL core
        ],
        "monitoring": [
            "res_hep",            # HEP support
            "res_hep_pjsip",      # HEP PJSIP integration
            "res_hep_rtcp",       # HEP RTCP support
            "res_statsd",         # StatsD metrics
            "res_prometheus"      # Prometheus metrics
        ],
        "ari": [
            "res_ari",                # ARI core
            "res_ari_applications",   # ARI applications
            "res_ari_asterisk",      # ARI Asterisk info
            "res_ari_bridges",       # ARI bridges
            "res_ari_channels",      # ARI channels
            "res_ari_device_states", # ARI device states
            "res_ari_endpoints",     # ARI endpoints
            "res_ari_events",        # ARI events
            "res_ari_mailboxes",     # ARI mailboxes
            "res_ari_model",         # ARI data model
            "res_ari_playbacks",     # ARI playbacks
            "res_ari_recordings",    # ARI recordings
            "res_ari_sounds"         # ARI sounds
        ],
        "websocket": [
            "res_http_websocket",     # WebSocket HTTP
            "res_websocket_client"    # WebSocket client
        ],
        "security": [
            "res_srtp",           # SRTP support
            "res_stun_monitor"    # STUN monitoring
        ]
    }

    CDR_MODULES = {
        "core": ["cdr_csv"],
        "database": ["cdr_odbc", "cdr_pgsql", "cdr_mysql"],
        "syslog": ["cdr_syslog"],
        "radius": ["cdr_radius"]
    }

    CEL_MODULES = {
        "core": ["cel_custom"],
        "database": ["cel_odbc", "cel_pgsql", "cel_mysql"]
    }

    # Modules to exclude by default
    EXCLUDE_MODULES = [
        "chan_dahdi",      # Hardware dependency
        "chan_misdn",      # Hardware dependency
        "app_festival",    # External dependency
        "app_flash",       # Legacy
        "res_pjsip_sdp_rtp", # Can cause issues
        "codec_dahdi"      # Hardware dependency
    ]

    # Categories to disable (sounds, documentation)
    DISABLE_CATEGORIES = [
        "MENUSELECT_CORE_SOUNDS",
        "MENUSELECT_MOH",
        "MENUSELECT_EXTRA_SOUNDS"
    ]

    def __init__(self, asterisk_version: str):
        self.asterisk_version = asterisk_version
        self.major, self.minor, self.patch, self.suffix = self._parse_version(asterisk_version)
        self.is_legacy = self._is_legacy_version()

    def _parse_version(self, version: str) -> tuple:
        """Parse version string"""
        # Handle git versions
        if version == 'git' or version.startswith('git-'):
            # For git versions, treat as latest modern version (99.99.99)
            return 99, 99, 99, None

        base_version = version.split('-cert')[0]
        match = re.match(r'^(\d+)\.(\d+)(?:\.(\d+))?(?:-(alpha|beta|rc)\d*)?', base_version)
        if not match:
            raise ValueError(f"Invalid version format: {version}")

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        suffix = match.group(4)

        return major, minor, patch, suffix

    def _is_legacy_version(self) -> bool:
        """Check if this is a legacy version (1.2-1.8)"""
        return self.major == 1 and 2 <= self.minor <= 8

    def _version_supports_pjsip(self) -> bool:
        """Check if version supports PJSIP (12+)"""
        return self.major >= 12

    def _version_supports_websocket(self) -> bool:
        """Check if version supports WebSocket channels (23+, mandatory)"""
        return self.major >= 23

    def _version_supports_ari(self) -> bool:
        """Check if version supports ARI (12+)"""
        return self.major >= 12

    def generate_config(self, features: Dict[str, bool] = None) -> MenuSelectConfig:
        """Generate menuselect configuration"""
        features = features or {}

        enable_modules = []
        disable_modules = list(self.EXCLUDE_MODULES)

        # Channel modules
        if self.is_legacy:
            enable_modules.extend(self.CHANNEL_MODULES["legacy"])
        else:
            enable_modules.extend(self.CHANNEL_MODULES["modern"])

        # Remove WebSocket channels if not supported
        if not self._version_supports_websocket():
            enable_modules = [m for m in enable_modules if m != "chan_websocket"]

        # Application modules
        enable_modules.extend(self.APPLICATION_MODULES["core"])
        enable_modules.extend(self.APPLICATION_MODULES["voicemail"])
        enable_modules.extend(self.APPLICATION_MODULES["call_features"])
        enable_modules.extend(self.APPLICATION_MODULES["control"])

        # Conferencing - prefer ConfBridge for modern versions
        if not self.is_legacy and self.major >= 10:
            enable_modules.extend(self.APPLICATION_MODULES["conferencing"])
        else:
            enable_modules.append("app_meetme")  # Legacy conferencing

        # Resource modules
        enable_modules.extend(self.RESOURCE_MODULES["core"])
        enable_modules.extend(self.RESOURCE_MODULES["cdr_cel"])

        # PJSIP modules for modern versions
        if self._version_supports_pjsip() and not self.is_legacy:
            enable_modules.extend(self.RESOURCE_MODULES["pjsip"])

        # Database modules
        if features.get("postgresql", True):
            enable_modules.extend([m for m in self.RESOURCE_MODULES["database"] if "pgsql" in m])
            enable_modules.extend([m for m in self.CDR_MODULES["database"] if "pgsql" in m])
            enable_modules.extend([m for m in self.CEL_MODULES["database"] if "pgsql" in m])

        if features.get("odbc", True):
            enable_modules.extend([m for m in self.RESOURCE_MODULES["database"] if "odbc" in m])
            enable_modules.extend([m for m in self.CDR_MODULES["database"] if "odbc" in m])
            enable_modules.extend([m for m in self.CEL_MODULES["database"] if "odbc" in m])

        # CDR modules
        enable_modules.extend(self.CDR_MODULES["core"])

        # ARI modules for modern versions
        if self._version_supports_ari() and features.get("ari", True):
            enable_modules.extend(self.RESOURCE_MODULES["ari"])

        # WebSocket and ARI modules (MANDATORY for v23+)
        if self._version_supports_websocket():
            # Force enable all WebSocket modules for v23+
            enable_modules.extend(self.RESOURCE_MODULES["websocket"])
            # Force enable all ARI modules for v23+ (overrides feature flag)
            enable_modules.extend(self.RESOURCE_MODULES["ari"])
        else:
            # Optional WebSocket modules for older versions
            if features.get("websocket", True) and not self.is_legacy:
                enable_modules.extend(self.RESOURCE_MODULES["websocket"])

        # Security modules
        if features.get("srtp", True) and not self.is_legacy:
            enable_modules.extend(self.RESOURCE_MODULES["security"])

        # Monitoring/HEP modules
        if features.get("hep", True) and not self.is_legacy:
            enable_modules.extend(self.RESOURCE_MODULES["monitoring"])

        # Remove duplicates and sort
        enable_modules = sorted(list(set(enable_modules)))
        disable_modules = sorted(list(set(disable_modules)))

        return MenuSelectConfig(
            enable=enable_modules,
            disable=disable_modules,
            disable_categories=self.DISABLE_CATEGORIES.copy()
        )

    def generate_menuselect_commands(self, config: MenuSelectConfig) -> List[str]:
        """Generate menuselect command lines"""
        commands = []

        # Disable BUILD_NATIVE to avoid platform issues
        commands.append("menuselect/menuselect --disable BUILD_NATIVE menuselect.makeopts")

        # Enable BETTER_BACKTRACES for debugging
        commands.append("menuselect/menuselect --enable BETTER_BACKTRACES menuselect.makeopts")

        # Disable categories
        for category in config.disable_categories:
            commands.append(f"menuselect/menuselect --disable-category {category} menuselect.makeopts")

        # Enable modules
        for module in config.enable:
            commands.append(f"menuselect/menuselect --enable {module} menuselect.makeopts")

        # Disable modules
        for module in config.disable:
            commands.append(f"menuselect/menuselect --disable {module} menuselect.makeopts")

        return commands

    def get_required_menuselect_modules(self) -> Set[str]:
        """Get modules that must be selected for basic functionality"""
        base_modules = {
            "chan_local",
            "app_dial",
            "app_playback",
            "app_echo",
            "res_timing_timerfd",
            "res_crypto",
            "res_rtp_asterisk"
        }

        if not self.is_legacy and self._version_supports_pjsip():
            base_modules.update({
                "chan_pjsip",
                "res_pjsip",
                "res_pjsip_session"
            })
        else:
            base_modules.add("chan_sip")

        return base_modules


def main():
    """Example usage"""
    # Modern version
    generator = MenuSelectGenerator("22.6.0")
    config = generator.generate_config({
        "postgresql": True,
        "websocket": True,
        "ari": True,
        "hep": True
    })

    print("Modern Asterisk (22.6.0) configuration:")
    print(f"Enable modules ({len(config.enable)}):")
    for module in config.enable[:10]:  # Show first 10
        print(f"  {module}")
    if len(config.enable) > 10:
        print(f"  ... and {len(config.enable) - 10} more")

    print(f"\nDisable modules ({len(config.disable)}):")
    for module in config.disable:
        print(f"  {module}")

    print("\nMenuselect commands:")
    commands = generator.generate_menuselect_commands(config)
    for cmd in commands[:5]:  # Show first 5
        print(f"  {cmd}")
    if len(commands) > 5:
        print(f"  ... and {len(commands) - 5} more commands")

    # Legacy version
    print("\n" + "="*60)
    legacy_generator = MenuSelectGenerator("1.8.32.3")
    legacy_config = legacy_generator.generate_config()

    print("Legacy Asterisk (1.8.32.3) configuration:")
    print(f"Enable modules ({len(legacy_config.enable)}):")
    for module in legacy_config.enable:
        print(f"  {module}")


if __name__ == "__main__":
    main()