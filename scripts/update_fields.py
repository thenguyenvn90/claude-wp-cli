"""Bridge script for WordPress ACF / custom fields management."""
import argparse, os, subprocess, sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("action", choices=["get", "update"])
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--data", default=None)
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "cli.main", "--site", args.site, "fields", args.action]
    cmd.extend(["--post-id", str(args.post_id)])
    if args.data: cmd.extend(["--data", args.data])

    env = os.environ.copy()
    env.setdefault("CLAUDE_SKILL_CALLER_CWD", os.getcwd())
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, env=env)
    print(result.stdout, end="")
    if result.stderr: print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
