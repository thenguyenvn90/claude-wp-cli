"""CLI subcommand for WordPress users (list / get / create / update / delete)."""

from client.http import WPClient, json_output
from client.users import UsersClient


def register(subparsers):
    parser = subparsers.add_parser("users", help="Manage users")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("list")
    p.add_argument("--per-page", type=int, default=20)

    p = sub.add_parser("get")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("create")
    p.add_argument("--username", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--role", default=None, help="e.g. author, editor, subscriber")

    p = sub.add_parser("update")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--email", default=None)
    p.add_argument("--role", default=None)
    p.add_argument("--name", default=None)

    p = sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--reassign", type=int, default=None, help="User id to reassign content to")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    users = UsersClient(client)
    if args.action == "list":
        data, total, pages = users.list(per_page=args.per_page)
        print(json_output(data, total=total, total_pages=pages, page=1))
    elif args.action == "get":
        print(json_output(users.get(args.id)))
    elif args.action == "create":
        roles = [args.role] if args.role else None
        print(json_output(users.create(username=args.username, email=args.email,
                                        password=args.password, roles=roles)))
    elif args.action == "update":
        roles = [args.role] if args.role else None
        print(json_output(users.update(args.id, email=args.email, roles=roles, name=args.name)))
    elif args.action == "delete":
        print(json_output(users.delete(args.id, reassign=args.reassign)))
