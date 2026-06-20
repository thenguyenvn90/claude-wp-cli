"""Site configuration loader — standalone version.

Loads site config directly from YAML + .env files.
No dependency on marvomatic_core.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import dotenv_values

from .config import SiteConfig, WordPressConfig, WordPressSecrets


def _resolve_sites_dir() -> Path:
    """Resolve sites directory using the resolution chain.

    Order:
    1. MARVOMATIC_SITES_DIR environment variable
    2. ./sites/ in current working directory
    3. CLAUDE_SKILL_CALLER_CWD/sites/ (original caller CWD)
    4. ~/.marvomatic/sites/ (global default)
    """
    # 1. Explicit env var
    env_dir = os.environ.get("MARVOMATIC_SITES_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if p.is_dir():
            return p

    # 2. Current working directory
    cwd_sites = Path.cwd() / "sites"
    if cwd_sites.is_dir():
        return cwd_sites

    # 3. Original caller's CWD (when invoked via bridge script that changes cwd)
    original_cwd = os.environ.get("CLAUDE_SKILL_CALLER_CWD") or os.environ.get("CLAUDE_PLUGIN_CALLER_CWD")
    if original_cwd:
        p = Path(original_cwd) / "sites"
        if p.is_dir():
            return p

    # 4. Global default in home directory
    return Path.home() / ".marvomatic" / "sites"


class SiteRegistry:
    def __init__(self, sites_dir: Optional[Path] = None):
        self._sites_dir = sites_dir or _resolve_sites_dir()
        self._cache: dict[str, SiteConfig] = {}

    @property
    def sites_dir(self) -> Path:
        return self._sites_dir

    def list_sites(self) -> list[str]:
        if not self._sites_dir.is_dir():
            return []
        return sorted(
            d.name for d in self._sites_dir.iterdir()
            if d.is_dir() and d.name != "_template" and (d / "config.yaml").is_file()
        )

    def get_site(self, site_id: str) -> SiteConfig:
        if site_id in self._cache:
            return self._cache[site_id]

        site_dir = self._sites_dir / site_id
        config_path = site_dir / "config.yaml"
        if not config_path.is_file():
            raise FileNotFoundError(
                f"Site config not found: {config_path}\n"
                f"Run /core:setup to create a new site."
            )
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Build WordPress config from the wordpress section
        wp_raw = raw.get("wordpress", {})
        if wp_raw:
            # Use site_url as fallback for wordpress.site_url
            if not wp_raw.get("site_url") and raw.get("site_url"):
                wp_raw["site_url"] = raw["site_url"]
            wp_config = WordPressConfig(**wp_raw)
        else:
            wp_config = WordPressConfig(site_url=raw.get("site_url", ""))

        config = SiteConfig(
            site_id=raw.get("site_id", site_id),
            site_url=raw.get("site_url", ""),
            wordpress=wp_config,
        )

        # Load secrets from .env.site
        env_site_path = site_dir / ".env.site"
        if env_site_path.is_file():
            from client.guards import warn_if_world_readable
            warn_if_world_readable(env_site_path)
            env_values = dotenv_values(env_site_path)
            wp_secrets = WordPressSecrets(
                wp_username=env_values.get("WP_USERNAME", ""),
                wp_app_password=env_values.get("WP_APP_PASSWORD", ""),
            )
            config.set_wp_secrets(wp_secrets)

        self._cache[site_id] = config
        return config

    def clear_cache(self) -> None:
        self._cache.clear()


site_registry = SiteRegistry()
