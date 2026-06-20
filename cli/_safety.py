"""Shared CLI safety helpers — a confirmation gate for irreversible operations.

WordPress writes like delete / user-create / settings-set / plugin-deactivate are
destructive and often driven by an AI agent acting on untrusted input. These helpers
make every such command default-deny: it runs only with an explicit --yes, and --dry-run
prints what *would* happen without touching the site.
"""
from __future__ import annotations

from client.http import error_output, json_output


def add_destructive_flags(parser) -> None:
    """Add --yes / --dry-run to a destructive subparser."""
    parser.add_argument("--yes", action="store_true",
                        help="confirm this irreversible operation (required to proceed)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would happen, without doing it")


def confirm_or_exit(args, description: str) -> bool:
    """Gate a destructive op. Returns True to proceed.

    --dry-run  -> print the plan + return False (caller should NOT execute).
    no --yes   -> print a confirm-required error + exit(2).
    --yes      -> return True.
    """
    if getattr(args, "dry_run", False):
        print(json_output({"dry_run": True, "would": description}))
        return False
    if not getattr(args, "yes", False):
        print(error_output(
            "confirm_required",
            f"{description} is irreversible. Re-run with --yes to confirm, or --dry-run to preview.",
            0,
        ))
        raise SystemExit(2)
    return True
