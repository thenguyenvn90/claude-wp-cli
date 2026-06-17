"""Bridge script for WordPress post management."""
import argparse, os, subprocess, sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("action", choices=["list", "get", "create", "update", "delete", "revisions"])
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--content-file", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--category-ids", default=None)
    parser.add_argument("--tag-ids", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--per-page", type=int, default=10)
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "cli.main", "--site", args.site, "posts", args.action]
    if args.id is not None: cmd.extend(["--id", str(args.id)])
    if args.title: cmd.extend(["--title", args.title])
    if args.content_file: cmd.extend(["--content-file", args.content_file])
    if args.status: cmd.extend(["--status", args.status])
    if args.category_ids: cmd.extend(["--category-ids", args.category_ids])
    if args.tag_ids: cmd.extend(["--tag-ids", args.tag_ids])
    if args.force: cmd.append("--force")
    if args.action == "list":
        cmd.extend(["--per-page", str(args.per_page), "--page", str(args.page)])

    env = os.environ.copy()
    env.setdefault("CLAUDE_SKILL_CALLER_CWD", os.getcwd())
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, env=env)
    print(result.stdout, end="")
    if result.stderr: print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
