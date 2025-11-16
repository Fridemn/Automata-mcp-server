"""
Extension Configuration Manager

Manages configuration for MCP extensions:
1. Reads config requirements from extension's config.yaml
2. Syncs with central config/config.json
3. Auto-creates missing config entries with templates
"""

import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class ExtensionConfigManager:
    """Manages extension configurations and syncs with central config.json"""

    def __init__(self, config_json_path: str = "config/config.json"):
        """
        Initialize the configuration manager

        Args:
            config_json_path: Path to the central config.json file
        """
        self.config_json_path = Path(config_json_path)
        self._ensure_config_file()

    def _ensure_config_file(self):
        """Ensure config.json exists, create if not"""
        if not self.config_json_path.exists():
            self.config_json_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_config({})
            logger.info(f"Created config file: {self.config_json_path}")

    def _load_config(self) -> dict:
        """Load the central config.json"""
        try:
            with open(self.config_json_path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load config.json: {e}")
            return {}

    def _save_config(self, config: dict):
        """Save the central config.json"""
        try:
            with open(self.config_json_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved config to {self.config_json_path}")
        except Exception as e:
            logger.error(f"Failed to save config.json: {e}")
            raise

    def _load_extension_yaml(self, extension_name: str) -> dict:
        """
        Load extension's config.yaml

        Args:
            extension_name: Name of the extension (e.g., 'image_generate_midjourney')

        Returns:
            Dictionary containing the YAML config
        """
        yaml_path = Path(f"app/AutoUp-MCP-Extension/{extension_name}/config.yaml")
        if not yaml_path.exists():
            logger.warning(f"Extension config.yaml not found: {yaml_path}")
            return {}

        try:
            with open(yaml_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                return config
        except Exception as e:
            logger.error(f"Failed to load {yaml_path}: {e}")
            return {}

    def _merge_config_requirements(
        self,
        central_config: dict,
        extension_name: str,
        config_requirements: dict,
    ) -> tuple[dict, bool]:
        """
        Merge extension config requirements into central config

        Args:
            central_config: Current central config
            extension_name: Name of the extension
            config_requirements: Config requirements from extension's YAML

        Returns:
            Tuple of (updated_config, was_modified)
        """
        if extension_name not in central_config:
            central_config[extension_name] = {}

        extension_config = central_config[extension_name]
        was_modified = False

        for key, value in config_requirements.items():
            if key not in extension_config:
                # Add missing config with template
                if isinstance(value, dict):
                    # If value is a dict with 'default', 'type', 'description', etc.
                    if "default" in value:
                        extension_config[key] = value["default"]
                    elif "type" in value:
                        # Create empty placeholder based on type
                        type_defaults = {
                            "string": "",
                            "str": "",
                            "int": 0,
                            "float": 0.0,
                            "bool": False,
                            "list": [],
                            "dict": {},
                        }
                        extension_config[key] = type_defaults.get(
                            value["type"].lower(),
                            "",
                        )
                    else:
                        # It's a nested config object
                        extension_config[key] = value
                else:
                    # Simple value
                    extension_config[key] = value

                was_modified = True
                logger.info(
                    f"Added missing config '{key}' for extension '{extension_name}'",
                )

        return central_config, was_modified

    def get_extension_config(
        self,
        extension_name: str,
        auto_create: bool = True,
    ) -> dict[str, Any]:
        """
        Get configuration for an extension

        Args:
            extension_name: Name of the extension (e.g., 'image_generate_midjourney')
            auto_create: If True, automatically create missing config entries

        Returns:
            Dictionary containing the extension's configuration
        """
        # Load extension's config.yaml to check requirements
        extension_yaml = self._load_extension_yaml(extension_name)
        config_requirements = extension_yaml.get("config_requirements", {})

        # Load central config
        central_config = self._load_config()

        # Check if we need to add missing configs
        if auto_create and config_requirements:
            updated_config, was_modified = self._merge_config_requirements(
                central_config,
                extension_name,
                config_requirements,
            )

            if was_modified:
                self._save_config(updated_config)
                logger.warning(
                    f"Added missing config entries for '{extension_name}'. "
                    f"Please fill in the values in {self.config_json_path}",
                )
                central_config = updated_config

        # Return the extension's config section
        return central_config.get(extension_name, {})

    def get_config_value(
        self,
        extension_name: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a specific config value for an extension

        Args:
            extension_name: Name of the extension
            key: Config key to retrieve
            default: Default value if key not found

        Returns:
            The config value or default
        """
        extension_config = self.get_extension_config(extension_name)
        return extension_config.get(key, default)

    def validate_extension_config(self, extension_name: str) -> tuple[bool, list[str]]:
        """
        Validate that all required config values are filled

        Args:
            extension_name: Name of the extension

        Returns:
            Tuple of (is_valid, list_of_missing_or_empty_keys)
        """
        extension_yaml = self._load_extension_yaml(extension_name)
        config_requirements = extension_yaml.get("config_requirements", {})

        if not config_requirements:
            return True, []

        extension_config = self.get_extension_config(extension_name, auto_create=False)
        missing_keys = []

        for key, requirement in config_requirements.items():
            value = extension_config.get(key)

            # Check if required and missing/empty
            is_required = True
            if isinstance(requirement, dict):
                is_required = requirement.get("required", True)

            if is_required:
                if value is None or value == "" or value == [] or value == {}:
                    missing_keys.append(key)

        is_valid = len(missing_keys) == 0
        return is_valid, missing_keys
