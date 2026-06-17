"""CLI subcommand for WordPress plugins (list / activate / deactivate / install / delete)."""

from client.http import WPClient, json_output
from client.plugins import PluginsClient


def register(subparsers):
    parser = subparsers.add_parser("plugins", help="Manage plugins")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("list")
    p.add_argument("--status", default=None, help="active | inactive")

    for action in ("get", "activate", "deactivate", "delete"):
        p = sub.add_parser(action)
        p.add_argument("--plugin", required=True, help="e.g. 'akismet/akismet'")

    p = sub.add_parser("install")
    p.add_argument("--slug", required=True, help="WordPress.org slug, e.g. 'classic-editor'")
    p.add_argument("--activate", action="store_true")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    plugins = PluginsClient(client)
    if args.action == "list":
        print(json_output(plugins.list(status=args.status)))
    elif args.action == "get":
        print(json_output(plugins.get(args.plugin)))
    elif args.action == "activate":
        print(json_output(plugins.set_status(args.plugin, "active")))
    elif args.action == "deactivate":
        print(json_output(plugins.set_status(args.plugin, "inactive")))
    elif args.action == "install":
        print(json_output(plugins.install(args.slug, activate=args.activate)))
    elif args.action == "delete":
        print(json_output(plugins.delete(args.plugin)))
