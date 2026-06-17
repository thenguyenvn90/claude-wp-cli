"""CLI subcommand for WordPress content search (/wp/v2/search)."""

from client.http import WPClient, json_output
from client.search import SearchClient


def register(subparsers):
    parser = subparsers.add_parser("search", help="Search site content")
    parser.add_argument("--term", required=True, help="Search query")
    parser.add_argument("--type", default=None, dest="search_type", help="post | term | post-format")
    parser.add_argument("--subtype", default=None, help="e.g. post, page (within type)")
    parser.add_argument("--per-page", type=int, default=10)
    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    search = SearchClient(client)
    data, total, pages = search.query(args.term, search_type=args.search_type,
                                       subtype=args.subtype, per_page=args.per_page)
    print(json_output(data, total=total, total_pages=pages, page=1))
