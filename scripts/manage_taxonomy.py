"""Bridge script for WordPress taxonomy management."""
import argparse, os, subprocess, sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--tax-type", required=True, choices=["categories", "tags"])
    parser.add_argument("action", choices=["list", "create", "delete"])
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--parent-id", type=int, default=None)
    parser.add_argument("--per-page", type=int, default=100)
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "cli.main", "--site", args.site, "taxonomy", args.tax_type, args.action]
    if args.id is not None: cmd.extend(["--id", str(args.id)])
    if args.name: cmd.extend(["--name", args.name])
    if args.parent_id is not None: cmd.extend(["--parent-id", str(args.parent_id)])
    if args.action == "list":
        cmd.extend(["--per-page", str(args.per_page)])

    env = os.environ.copy()
    env.setdefault("CLAUDE_SKILL_CALLER_CWD", os.getcwd())
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, env=env)
    print(result.stdout, end="")
    if result.stderr: print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
