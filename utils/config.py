"""
Configuration management for Cleanarr
"""

import configparser
from pathlib import Path
from typing import Any, Dict, Optional

from utils import logger


class Config:
    """Configuration manager for Cleanarr"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path or Path.home() / ".config" / "cleanarr" / "config.cfg"
        )
        self.config = configparser.ConfigParser()
        self.load()

    def load(self) -> bool:
        """Load configuration from file, creating example if missing"""
        if not self.config_path.exists():
            print(f"🔧 No configuration file found at: {self.config_path}")
            print("📝 Creating example configuration file...")
            self.create_example_config()
            print("✅ Example configuration created!")
            print(
                "📋 Please edit the configuration file with your actual server details."
            )
            return True  # Return True since we created a valid config

        try:
            self.config.read(self.config_path)
            return True
        except Exception as e:
            logger.error(f"Error reading config file {self.config_path}: {e}")
            return False

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get all values from a configuration section"""
        if section in self.config:
            return dict(self.config[section])
        return {}

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def has_section(self, section: str) -> bool:
        """Check if configuration section exists"""
        return section in self.config

    def create_example_config(self) -> None:
        """Create an example configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        example_content = """[jellyfin]
server_url = http://localhost:8096
api_key = your_jellyfin_api_key_here
default_user = maateen

[sonarr]
server_url = http://localhost:8989
api_key = your_sonarr_api_key_here

[radarr]
server_url = http://localhost:7878
api_key = your_radarr_api_key_here

[qbittorrent]
server_url = http://localhost:8080
username = your_qbt_username
password = your_qbt_password
# Set to true to use HTTP Basic Auth instead of session-based auth
use_basic_auth = false

[auth]
# HTTP Basic Auth credentials for Radarr/Sonarr (if required)
username = your_username
password = your_password
"""

        with open(self.config_path, "w") as f:
            f.write(example_content)

        # Reload the configuration after creating it
        self.config.read(self.config_path)


# Global config instance
config = Config()
