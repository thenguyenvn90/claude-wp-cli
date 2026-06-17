"""CLI subcommand for WordPress media."""

from client.http import WPClient, json_output
from client.media import MediaClient


def register(subparsers):
    parser = subparsers.add_parser("media", help="Manage WordPress media library")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("list")
    p.add_argument("--media-type", default=None)
    p.add_argument("--per-page", type=int, default=10)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("get")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("upload")
    p.add_argument("--file", required=True)
    p.add_argument("--alt-text", default=None)
    p.add_argument("--caption", default=None)
    p.add_argument("--title", default=None)

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--force", action="store_true")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    media = MediaClient(client)

    if args.action == "list":
        data, total, total_pages = media.list(media_type=args.media_type, per_page=args.per_page, page=args.page)
        print(json_output(data, total=total, total_pages=total_pages, page=args.page))
    elif args.action == "get":
        print(json_output(media.get(args.id)))
    elif args.action == "upload":
        data = media.upload(args.file, alt_text=args.alt_text, caption=args.caption, title=args.title)
        print(json_output(data))
    elif args.action == "delete":
        print(json_output(media.delete(args.id, force=args.force)))
