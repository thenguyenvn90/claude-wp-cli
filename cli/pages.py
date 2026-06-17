"""CLI subcommand for WordPress pages."""

from pathlib import Path
from client.http import WPClient, json_output
from client.pages import PagesClient
from converter.markdown import convert_markdown


def register(subparsers):
    parser = subparsers.add_parser("pages", help="Manage WordPress pages")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("list")
    p.add_argument("--status", default="any")
    p.add_argument("--per-page", type=int, default=10)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("get")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("create")
    p.add_argument("--title", required=True)
    p.add_argument("--content-file", default=None)
    p.add_argument("--status", default=None, dest="post_status")
    p.add_argument("--parent-id", type=int, default=None)
    p.add_argument("--template", default=None)

    p = sub.add_parser("update")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--title", default=None)
    p.add_argument("--content-file", default=None)
    p.add_argument("--status", default=None, dest="post_status")
    p.add_argument("--parent-id", type=int, default=None)
    p.add_argument("--template", default=None)

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--force", action="store_true")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    wp_cfg = config.wordpress
    pages = PagesClient(client, default_status=wp_cfg.default_status)

    if args.action == "list":
        data, total, total_pages = pages.list(status=args.status, per_page=args.per_page, page=args.page)
        print(json_output(data, total=total, total_pages=total_pages, page=args.page))
    elif args.action == "get":
        print(json_output(pages.get(args.id)))
    elif args.action == "create":
        content = None
        if args.content_file:
            md = Path(args.content_file).read_text(encoding="utf-8")
            content = convert_markdown(md, editor_type=wp_cfg.editor_type)
        data = pages.create(title=args.title, content=content or "", status=getattr(args, "post_status", None), parent_id=args.parent_id, template=args.template)
        print(json_output(data))
    elif args.action == "update":
        content = None
        if args.content_file:
            md = Path(args.content_file).read_text(encoding="utf-8")
            content = convert_markdown(md, editor_type=wp_cfg.editor_type)
        data = pages.update(args.id, title=getattr(args, "title", None), content=content, status=getattr(args, "post_status", None), parent_id=getattr(args, "parent_id", None), template=getattr(args, "template", None))
        print(json_output(data))
    elif args.action == "delete":
        print(json_output(pages.delete(args.id, force=args.force)))
