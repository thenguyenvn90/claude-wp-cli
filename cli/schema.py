"""CLI subcommand for structured data / schema."""

import json as json_lib
import sys
from pathlib import Path
from client.http import WPClient, json_output, error_output
from client.schema import SchemaClient


def register(subparsers):
    parser = subparsers.add_parser("schema", help="Manage structured data / schema")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("get")
    p.add_argument("--post-id", type=int, required=True)

    p = sub.add_parser("push")
    p.add_argument("--post-id", type=int, required=True)
    p.add_argument("--schema-file", default=None)
    p.add_argument("--data", default=None)

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    schema = SchemaClient(client)
    seo_plugin = config.wordpress.seo_plugin
    if args.action == "get":
        print(json_output(schema.get(post_id=args.post_id)))
    elif args.action == "push":
        if args.schema_file:
            schema_data = json_lib.loads(Path(args.schema_file).read_text(encoding="utf-8"))
        elif args.data:
            schema_data = json_lib.loads(args.data)
        else:
            print(error_output("missing_input", "Provide --schema-file or --data", 0))
            sys.exit(1)
            return
        result = schema.push(post_id=args.post_id, schema_data=schema_data, seo_plugin=seo_plugin)
        if result is None:
            print(json_output({"skipped": True, "reason": f"seo_plugin={seo_plugin}"}))
        else:
            print(json_output(result))
