"""CLI subcommand for WordPress navigation menus."""

from client.http import WPClient, json_output
from client.menus import MenusClient


def register(subparsers):
    parser = subparsers.add_parser("menus", help="Manage navigation menus and items")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    sub.add_parser("list")

    p = sub.add_parser("get")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--locations", default=None, help="Comma-separated theme location slugs")

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("items")
    p.add_argument("--menu-id", type=int, required=True)

    p = sub.add_parser("add-item")
    p.add_argument("--menu-id", type=int, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--object-id", type=int, default=None)
    p.add_argument("--type", default=None, dest="item_type", help="custom | post_type | taxonomy")
    p.add_argument("--object", default=None, dest="object_name", help="post | page | category ...")
    p.add_argument("--parent", type=int, default=None)

    p = sub.add_parser("delete-item")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("assign-location")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--locations", required=True, help="Comma-separated theme location slugs")

    parser.set_defaults(func=handle)


def _csv(value):
    return [x.strip() for x in value.split(",") if x.strip()] if value else None


def handle(args, client: WPClient, config):
    menus = MenusClient(client)
    if args.action == "list":
        print(json_output(menus.list()))
    elif args.action == "get":
        print(json_output(menus.get(args.id)))
    elif args.action == "create":
        print(json_output(menus.create(name=args.name, locations=_csv(args.locations))))
    elif args.action == "delete":
        print(json_output(menus.delete(args.id)))
    elif args.action == "items":
        print(json_output(menus.list_items(args.menu_id)))
    elif args.action == "add-item":
        print(json_output(menus.add_item(
            menu_id=args.menu_id, title=args.title, url=args.url, object_id=args.object_id,
            item_type=args.item_type, object_name=args.object_name, parent=args.parent)))
    elif args.action == "delete-item":
        print(json_output(menus.delete_item(args.id)))
    elif args.action == "assign-location":
        print(json_output(menus.assign_location(args.id, _csv(args.locations))))
