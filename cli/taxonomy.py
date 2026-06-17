"""CLI subcommand for WordPress categories and tags."""

from client.http import WPClient, json_output
from client.taxonomy import TaxonomyClient


def register(subparsers):
    parser = subparsers.add_parser("taxonomy", help="Manage categories and tags")
    sub = parser.add_subparsers(dest="tax_type")
    sub.required = True

    cat_parser = sub.add_parser("categories")
    cat_sub = cat_parser.add_subparsers(dest="action")
    cat_sub.required = True

    p = cat_sub.add_parser("list")
    p.add_argument("--per-page", type=int, default=100)

    p = cat_sub.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--parent-id", type=int, default=None)

    p = cat_sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)

    tag_parser = sub.add_parser("tags")
    tag_sub = tag_parser.add_subparsers(dest="action")
    tag_sub.required = True

    p = tag_sub.add_parser("list")
    p.add_argument("--per-page", type=int, default=100)

    p = tag_sub.add_parser("create")
    p.add_argument("--name", required=True)

    p = tag_sub.add_parser("delete")
    p.add_argument("--id", type=int, required=True)

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    tax = TaxonomyClient(client)
    if args.tax_type == "categories":
        if args.action == "list":
            data, total, pages = tax.list_categories(per_page=args.per_page)
            print(json_output(data, total=total, total_pages=pages, page=1))
        elif args.action == "create":
            print(json_output(tax.create_category(name=args.name, parent_id=args.parent_id)))
        elif args.action == "delete":
            print(json_output(tax.delete_category(args.id)))
    elif args.tax_type == "tags":
        if args.action == "list":
            data, total, pages = tax.list_tags(per_page=args.per_page)
            print(json_output(data, total=total, total_pages=pages, page=1))
        elif args.action == "create":
            print(json_output(tax.create_tag(name=args.name)))
        elif args.action == "delete":
            print(json_output(tax.delete_tag(args.id)))
