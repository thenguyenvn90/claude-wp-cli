"""CLI subcommand for WordPress pages."""

from client.http import WPClient, json_output, error_output
from client.pages import PagesClient
from client.posts import PostsClient
from converter.markdown import convert_markdown
from client.guards import safe_read_text
from ._safety import add_destructive_flags, confirm_or_exit


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
    p.add_argument("--slug", default=None, help="expected slug; verified before AND after the write")
    p.add_argument("--raw", action="store_true", help="bypass push-safe guards on the content write")
    p.add_argument("--force", action="store_true", help="bypass markdown-leak refusal")
    p.add_argument("--no-emdash-strip", action="store_true")
    p.add_argument("--allow-drift", action="store_true")
    p.add_argument("--no-drift-check", action="store_true")
    p.add_argument("--expect-modified", default=None,
                   help="refuse if the page's 'modified' changed since this timestamp")

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="hard delete (skip trash)")
    add_destructive_flags(p)

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
            content = convert_markdown(safe_read_text(args.content_file), editor_type=wp_cfg.editor_type)
        data = pages.create(title=args.title, content=content or "", status=getattr(args, "post_status", None), parent_id=args.parent_id, template=args.template)
        print(json_output(data))
    elif args.action == "update":
        content = None
        if args.content_file:
            content = convert_markdown(safe_read_text(args.content_file), editor_type=wp_cfg.editor_type)
        if content is not None and not args.raw:
            # Pages get the SAME guarded write as posts (push_safe is post_type-parameterised).
            res = PostsClient(client).push_safe(
                args.id, content, expected_slug=args.slug, force=args.force,
                strip_emdash=not args.no_emdash_strip, check_drift_enabled=not args.no_drift_check,
                allow_drift=args.allow_drift, status=getattr(args, "post_status", None),
                post_type="pages", expected_modified=args.expect_modified)
            if not res.get("pushed"):
                print(error_output("push_refused", res.get("refused", "refused"), 0))
                raise SystemExit(2)
            extra = {k: v for k, v in (
                ("title", args.title), ("parent_id", getattr(args, "parent_id", None)),
                ("template", getattr(args, "template", None))) if v is not None}
            if extra:
                pages.update(args.id, **extra)
            print(json_output(res))
        else:
            data = pages.update(args.id, title=getattr(args, "title", None), content=content, status=getattr(args, "post_status", None), parent_id=getattr(args, "parent_id", None), template=getattr(args, "template", None))
            print(json_output(data))
    elif args.action == "delete":
        if confirm_or_exit(args, f"delete page {args.id}" + (" (hard delete)" if args.force else "")):
            print(json_output(pages.delete(args.id, force=args.force)))
