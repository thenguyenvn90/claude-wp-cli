"""Bridge script for WordPress media management."""
import argparse, os, subprocess, sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("action", choices=["list", "get", "upload", "delete"])
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--file", default=None)
    parser.add_argument("--alt-text", default=None)
    parser.add_argument("--caption", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--media-type", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--per-page", type=int, default=10)
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "cli.main", "--site", args.site, "media", args.action]
    if args.id is not None: cmd.extend(["--id", str(args.id)])
    if args.file: cmd.extend(["--file", args.file])
    if args.alt_text: cmd.extend(["--alt-text", args.alt_text])
    if args.caption: cmd.extend(["--caption", args.caption])
    if args.title: cmd.extend(["--title", args.title])
    if args.media_type: cmd.extend(["--media-type", args.media_type])
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
