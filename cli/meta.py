"""CLI subcommand for SEO meta (title/description/focus-keyword) with focus-kw merge."""

from client.http import WPClient, WPAPIError, json_output
from client.meta import MetaClient
from client import seo_router


def register(subparsers):
    parser = subparsers.add_parser("meta", help="Read/write SEO meta (RankMath/Yoast/generic)")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    common = dict()
    p = sub.add_parser("get", help="Read current title/description/focus-keyword")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--plugin", default="auto", help="auto|rankmath|yoast|generic|none")
    p.add_argument("--type", default="post", choices=["post", "page"])

    p = sub.add_parser("set", help="Write meta; focus keywords MERGE unless --focus-set")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--title", default=None)
    p.add_argument("--desc", default=None)
    p.add_argument("--focus-add", default=None, help="Comma-separated; merged with existing")
    p.add_argument("--focus-set", default=None, help="Comma-separated; replaces existing")
    p.add_argument("--plugin", default="auto", help="auto|rankmath|yoast|generic|none")
    p.add_argument("--type", default="post", choices=["post", "page"])

    parser.set_defaults(func=handle)


def _resolve_plugin(requested: str, client: WPClient, config) -> str:
    """Explicit --plugin wins; otherwise auto-detect from the site's WP REST namespaces."""
    if requested and requested != "auto":
        return requested
    if config is not None:
        configured = getattr(config.wordpress, "seo_plugin", "none")
        if configured not in ("none", "auto", ""):
            return configured
    try:
        root = client.request_path("GET", "/wp-json", params={"_fields": "namespaces"})
        return seo_router.detect_plugin(root.get("namespaces", []))
    except WPAPIError:
        return "generic"


def _csv(value):
    return [k.strip() for k in value.split(",") if k.strip()] if value else None


def handle(args, client: WPClient, config):
    post_type = "pages" if args.type == "page" else "posts"
    plugin = _resolve_plugin(args.plugin, client, config)
    meta = MetaClient(client, post_type=post_type)

    if args.action == "get":
        print(json_output({"plugin": plugin, **meta.get_meta(args.id, plugin=plugin)}))
        return

    # action == set
    result = meta.update_meta(
        args.id, plugin=plugin,
        title=args.title, description=args.desc,
        focus_add=_csv(args.focus_add), focus_set=_csv(args.focus_set),
    )
    print(json_output(result))
