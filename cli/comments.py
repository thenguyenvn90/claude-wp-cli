"""CLI subcommand for WordPress comments (moderate / reply / delete)."""

from client.http import WPClient, json_output
from client.comments import CommentsClient
from ._safety import add_destructive_flags, confirm_or_exit


def register(subparsers):
    parser = subparsers.add_parser("comments", help="Moderate, reply to, and delete comments")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("list")
    p.add_argument("--status", default=None, help="approve | hold | spam | trash")
    p.add_argument("--post", type=int, default=None)
    p.add_argument("--per-page", type=int, default=20)

    p = sub.add_parser("get")
    p.add_argument("--id", type=int, required=True)

    for action in ("approve", "hold", "spam"):
        p = sub.add_parser(action)
        p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("reply")
    p.add_argument("--post", type=int, required=True)
    p.add_argument("--parent", type=int, required=True)
    p.add_argument("--content", required=True)

    p = sub.add_parser("create")
    p.add_argument("--post", type=int, required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--parent", type=int, default=None)

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="hard delete (skip trash)")
    add_destructive_flags(p)

    parser.set_defaults(func=handle)


_STATUS = {"approve": "approved", "hold": "hold", "spam": "spam"}


def handle(args, client: WPClient, config):
    comments = CommentsClient(client)
    if args.action == "list":
        data, total, pages = comments.list(status=args.status, post=args.post, per_page=args.per_page)
        print(json_output(data, total=total, total_pages=pages, page=1))
    elif args.action == "get":
        print(json_output(comments.get(args.id)))
    elif args.action in _STATUS:
        print(json_output(comments.set_status(args.id, _STATUS[args.action])))
    elif args.action == "reply":
        print(json_output(comments.create(post=args.post, content=args.content, parent=args.parent)))
    elif args.action == "create":
        print(json_output(comments.create(post=args.post, content=args.content, parent=args.parent)))
    elif args.action == "delete":
        if confirm_or_exit(args, f"delete comment {args.id}" + (" (hard delete)" if args.force else "")):
            print(json_output(comments.delete(args.id, force=args.force)))
