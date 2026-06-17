"""CLI subcommand for WordPress widgets and sidebars (read-only inventory)."""

from client.http import WPClient, json_output
from client.widgets import WidgetsClient


def register(subparsers):
    parser = subparsers.add_parser("widgets", help="Inspect sidebars and widgets")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    sub.add_parser("sidebars", help="List widget areas (sidebars)")

    p = sub.add_parser("sidebar", help="Get one sidebar with its widgets")
    p.add_argument("--id", required=True, help="Sidebar id, e.g. 'sidebar-1'")

    sub.add_parser("list", help="List configured widget instances")
    sub.add_parser("types", help="List available widget types")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    widgets = WidgetsClient(client)
    if args.action == "sidebars":
        print(json_output(widgets.list_sidebars()))
    elif args.action == "sidebar":
        print(json_output(widgets.get_sidebar(args.id)))
    elif args.action == "list":
        print(json_output(widgets.list_widgets()))
    elif args.action == "types":
        print(json_output(widgets.list_types()))
