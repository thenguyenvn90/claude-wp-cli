"""CLI subcommand for the guarded publish path (parity with wp_push_safe / wp_fetch_live)."""

from client.http import WPClient, json_output, error_output
from client.posts import PostsClient
from client.guards import safe_read_text, FileTooLargeError


def register(subparsers):
    parser = subparsers.add_parser("publish", help="Guarded content push + fetch-live")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("push", help="Safe body push (slug-guard, em-dash strip, md-leak, drift)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--content-file", required=True, help="Path to the HTML body file")
    p.add_argument("--slug", default=None, help="Expected slug; refuses push on mismatch")
    p.add_argument("--status", default=None, choices=["draft", "publish", "future", "pending", "private"])
    p.add_argument("--type", default="post", choices=["post", "page"])
    p.add_argument("--force", action="store_true", help="Bypass markdown-leak refusal")
    p.add_argument("--no-emdash-strip", action="store_true")
    p.add_argument("--allow-drift", action="store_true")
    p.add_argument("--no-drift-check", action="store_true")
    p.add_argument("--expect-modified", default=None,
                   help="refuse if the post's 'modified' changed since this timestamp "
                        "(capture it from `publish fetch` for a safe edit-then-push)")

    p = sub.add_parser("fetch", help="Fetch live raw content before editing")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--type", default="post", choices=["post", "page"])

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    posts = PostsClient(client)
    post_type = "pages" if args.type == "page" else "posts"

    if args.action == "fetch":
        print(json_output(posts.fetch_live(args.id, post_type=post_type)))
        return

    # action == push
    try:
        content = safe_read_text(args.content_file)
    except FileNotFoundError:
        print(error_output("file_not_found", f"Content file not found: {args.content_file}", 0))
        raise SystemExit(2)
    except FileTooLargeError as e:
        print(error_output("file_too_large", str(e), 0))
        raise SystemExit(2)
    result = posts.push_safe(
        args.id, content,
        expected_slug=args.slug,
        force=args.force,
        strip_emdash=not args.no_emdash_strip,
        check_drift_enabled=not args.no_drift_check,
        allow_drift=args.allow_drift,
        status=args.status,
        post_type=post_type,
        expected_modified=args.expect_modified,
    )
    if result.get("pushed"):
        print(json_output(result))
    else:
        print(error_output("push_refused", result.get("refused", "refused"), 0))
        raise SystemExit(2)
