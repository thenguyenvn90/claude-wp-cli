"""CLI subcommand for WordPress posts."""

from pathlib import Path
from typing import Optional

from client.http import WPClient, json_output
from client.posts import PostsClient
from converter.markdown import convert_markdown


def register(subparsers):
    parser = subparsers.add_parser("posts", help="Manage WordPress posts")
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
    p.add_argument("--date", default=None, help="Publish date (ISO 8601, e.g. 2026-03-20T10:00:00)")
    p.add_argument("--category-ids", default=None)
    p.add_argument("--tag-ids", default=None)
    p.add_argument("--featured-media", type=int, default=None, help="Media ID for featured image")

    p = sub.add_parser("update")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--title", default=None)
    p.add_argument("--content-file", default=None)
    p.add_argument("--status", default=None, dest="post_status")
    p.add_argument("--date", default=None, help="Publish date (ISO 8601, e.g. 2026-03-20T10:00:00)")
    p.add_argument("--featured-media", type=int, default=None, help="Media ID for featured image")

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("revisions")
    p.add_argument("--id", type=int, required=True)

    parser.set_defaults(func=handle)


def _parse_ids(value):
    if not value:
        return None
    return [int(x.strip()) for x in value.split(",")]


def _load_content(content_file, editor_type):
    if not content_file:
        return None
    md_text = Path(content_file).read_text(encoding="utf-8")
    return convert_markdown(md_text, editor_type=editor_type)


def handle(args, client: WPClient, config):
    wp_cfg = config.wordpress
    posts = PostsClient(client, default_status=wp_cfg.default_status, default_category_ids=wp_cfg.default_category_ids, default_tag_ids=wp_cfg.default_tag_ids)

    if args.action == "list":
        data, total, total_pages = posts.list(status=args.status, per_page=args.per_page, page=args.page)
        print(json_output(data, total=total, total_pages=total_pages, page=args.page))
    elif args.action == "get":
        print(json_output(posts.get(args.id)))
    elif args.action == "create":
        content = _load_content(getattr(args, "content_file", None), wp_cfg.editor_type)
        data = posts.create(title=args.title, content=content or "", status=getattr(args, "post_status", None), date=getattr(args, "date", None), category_ids=_parse_ids(getattr(args, "category_ids", None)), tag_ids=_parse_ids(getattr(args, "tag_ids", None)), featured_media=getattr(args, "featured_media", None))
        print(json_output(data))
    elif args.action == "update":
        content = _load_content(getattr(args, "content_file", None), wp_cfg.editor_type)
        data = posts.update(args.id, title=getattr(args, "title", None), content=content, status=getattr(args, "post_status", None), date=getattr(args, "date", None), featured_media=getattr(args, "featured_media", None))
        print(json_output(data))
    elif args.action == "delete":
        print(json_output(posts.delete(args.id, force=args.force)))
    elif args.action == "revisions":
        print(json_output(posts.revisions(args.id)))
