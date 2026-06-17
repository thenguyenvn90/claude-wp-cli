"""CLI subcommand for WordPress site settings (/wp/v2/settings)."""

import json

from client.http import WPClient, json_output
from client.settings import SettingsClient


def register(subparsers):
    parser = subparsers.add_parser("settings", help="Read/update exposed site settings")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("get")
    p.add_argument("--key", default=None, help="Return only this setting")

    p = sub.add_parser("set")
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True, help="Parsed as JSON when possible, else string")

    parser.set_defaults(func=handle)


def _parse(value: str):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def handle(args, client: WPClient, config):
    settings = SettingsClient(client)
    if args.action == "get":
        if args.key:
            print(json_output({args.key: settings.get_one(args.key)}))
        else:
            print(json_output(settings.get()))
    elif args.action == "set":
        print(json_output(settings.update({args.key: _parse(args.value)})))
