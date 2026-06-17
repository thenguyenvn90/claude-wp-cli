# models/config.py
"""Per-site configuration models."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings


class WordPressConfig(BaseModel):
    """WordPress REST API configuration (non-secret fields)."""
    site_url: str = Field(default="", description="WordPress site URL")
    rest_url: str = Field(default="", description="REST API base URL (auto-derived if omitted)")
    default_status: str = Field(default="draft", description="Default post status")
    editor_type: Literal["classic", "gutenberg"] = Field(default="classic", description="Editor type: classic | gutenberg")
    seo_plugin: Literal["rankmath", "yoast", "generic", "none"] = Field(default="none", description="SEO plugin: rankmath | yoast | generic | none")
    default_category_ids: list[int] = Field(default_factory=list)
    default_tag_ids: list[int] = Field(default_factory=list)
    default_author_id: Optional[int] = Field(default=None)
    timeout: int = Field(default=30, description="HTTP timeout in seconds")

    @model_validator(mode="after")
    def derive_rest_url(self) -> "WordPressConfig":
        if not self.rest_url and self.site_url:
            base = self.site_url.rstrip("/")
            self.rest_url = f"{base}/wp-json/wp/v2"
        return self


class WordPressSecrets(BaseSettings):
    """WordPress credentials loaded from .env.site."""
    wp_username: str = Field(default="")
    wp_app_password: SecretStr = Field(default=SecretStr(""))


class SiteConfig(BaseModel):
    """Full configuration for a single site."""
    site_id: str = Field(description="Unique site identifier")
    site_url: str = Field(description="Primary site URL")
    wordpress: WordPressConfig = Field(default_factory=WordPressConfig)
    _wp_secrets: Optional[WordPressSecrets] = None

    def set_wp_secrets(self, secrets: WordPressSecrets) -> None:
        self._wp_secrets = secrets

    @property
    def wp_secrets(self) -> Optional[WordPressSecrets]:
        return self._wp_secrets
