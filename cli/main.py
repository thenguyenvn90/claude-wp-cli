"""WordPress CLI main entry point."""

import argparse
import sys

from client.http import WPClient, WPAPIError, error_output
from client.auth import resolve_auth
from client.guards import MissingCredentialsError
from models.loader import SiteRegistry
from models.config import SiteConfig, WordPressConfig
from . import posts as posts_cmd
from . import pages as pages_cmd
from . import media as media_cmd
from . import taxonomy as taxonomy_cmd
from . import fields as fields_cmd
from . import schema as schema_cmd
from . import publish as publish_cmd
from . import meta as meta_cmd
from . import comments as comments_cmd
from . import plugins as plugins_cmd
from . import users as users_cmd
from . import search as search_cmd
from . import menus as menus_cmd
from . import widgets as widgets_cmd
from . import settings as settings_cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wp-cli", description="WordPress management CLI for Claude Code")
    parser.add_argument("--site", required=True, help="Site ID")
    subparsers = parser.add_subparsers(dest="resource", help="Resource type")
    subparsers.required = True
    posts_cmd.register(subparsers)
    pages_cmd.register(subparsers)
    media_cmd.register(subparsers)
    taxonomy_cmd.register(subparsers)
    fields_cmd.register(subparsers)
    schema_cmd.register(subparsers)
    publish_cmd.register(subparsers)
    meta_cmd.register(subparsers)
    comments_cmd.register(subparsers)
    plugins_cmd.register(subparsers)
    users_cmd.register(subparsers)
    search_cmd.register(subparsers)
    menus_cmd.register(subparsers)
    widgets_cmd.register(subparsers)
    settings_cmd.register(subparsers)
    return parser


def make_client(site_id: str):
    """Build a WPClient. Auth resolves via the kit no-secret contract (wp-auth.json /
    env / .mcp.json / .env.site). Site config.yaml is optional — a minimal config is
    synthesised when absent so .mcp.json-only sites work."""
    registry = SiteRegistry()
    try:
        config = registry.get_site(site_id)
    except FileNotFoundError:
        config = None
    rest_base, auth_header = resolve_auth(site_id)  # raises MissingCredentialsError if none
    if config is None:
        site_url = rest_base.split("/wp-json")[0]
        config = SiteConfig(site_id=site_id, site_url=site_url,
                            wordpress=WordPressConfig(site_url=site_url, rest_url=rest_base))
    client = WPClient(rest_url=rest_base, auth_header=auth_header, timeout=config.wordpress.timeout)
    return client, config


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        client, config = make_client(args.site)
    except FileNotFoundError as e:
        print(error_output("site_not_found", str(e), 0))
        sys.exit(2)
    except (MissingCredentialsError, ValueError) as e:
        print(error_output("config_error", str(e), 0))
        sys.exit(2)
    try:
        args.func(args, client, config)
    except WPAPIError as e:
        print(error_output(e.code, e.message, e.http_status))
        sys.exit(1)
    except Exception as e:
        print(error_output("internal_error", str(e), 0))
        sys.exit(1)


if __name__ == "__main__":
    main()
