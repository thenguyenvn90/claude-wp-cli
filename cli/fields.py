"""CLI subcommand for ACF / custom fields."""

import json as json_lib
from client.http import WPClient, json_output
from client.fields import FieldsClient


def register(subparsers):
    parser = subparsers.add_parser("fields", help="Manage ACF / custom fields")
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    p = sub.add_parser("get")
    p.add_argument("--post-id", type=int, required=True)

    p = sub.add_parser("update")
    p.add_argument("--post-id", type=int, required=True)
    p.add_argument("--data", required=True, help="JSON string of field data")

    parser.set_defaults(func=handle)


def handle(args, client: WPClient, config):
    fields = FieldsClient(client)
    if args.action == "get":
        print(json_output(fields.get(post_id=args.post_id)))
    elif args.action == "update":
        field_data = json_lib.loads(args.data)
        print(json_output(fields.update(post_id=args.post_id, data=field_data)))
