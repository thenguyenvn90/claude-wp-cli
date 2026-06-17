"""Pure content-safety guards for WordPress pushes.

Ported from the kit's battle-tested `scripts/wp_push_safe.py` so the wp-cli
publish path inherits the exact protections that were earned from production
incidents:

  - em-dash strip     : smart-text auto-emits ` — ` that violates site bans
  - markdown leak      : raw `## `, tables, fences, inline **bold**/`code` that
                         survived into HTML and render literally
  - meta-comment strip : a leading "Meta description:" writer artifact

These functions are PURE (text in, text/dict out) and therefore unit-testable
with no network. HTTP-dependent guards (slug verify, drift) live on the posts
client. Behavior is kept byte-for-byte identical to the legacy script; parity
tests assert that.
"""

from __future__ import annotations

import re


# (regex, name, threshold) — a pattern is a "leak" only at/above its threshold.
LEAK_PATTERNS = [
    (r"(?m)^## ",                       "h2_md",          3),
    (r"(?m)^### ",                      "h3_md",          4),
    (r"(?m)^\| .*\|\s*$",               "table_md_row",   3),
    (r"(?m)^```",                       "fence_md",       2),
    (r"(?m)^- \*\*[^*]+\*\*",           "bullet_bold_md", 3),
    (r"(?m)^\*\*[^*\n]{1,80}\*\*\s*$",  "bold_only_line", 5),
    # Inline markdown that survived into HTML (**bold** / `code` inside <td>/<li>) —
    # wpautop does NOT convert these; they render literal. Line-start patterns miss them.
    (r"\*\*[^*\n]{1,80}\*\*",           "inline_bold_md", 3),
    (r"(?<!`)`[^`\n]{1,60}`(?!`)",      "inline_code_md", 4),
]


class MarkdownLeakError(RuntimeError):
    """Raised when raw-markdown patterns exceed threshold in content meant to be HTML."""


class SlugMismatchError(RuntimeError):
    """Raised when a post's live slug does not match the expected slug."""


class MissingCredentialsError(RuntimeError):
    """Raised when no WordPress credentials can be resolved."""


def _strip_safe_blocks(content: str) -> str:
    """Remove <pre>, <code>, and HTML comments before leak scanning (legit md there)."""
    content = re.sub(r"<pre[^>]*>.*?</pre>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<code[^>]*>.*?</code>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return content


def detect_md_leak(content: str) -> dict:
    """Return {pattern_name: count} for every pattern at/above threshold. Empty = safe."""
    cleaned = _strip_safe_blocks(content)
    fails = {}
    for pattern, name, threshold in LEAK_PATTERNS:
        count = len(re.findall(pattern, cleaned))
        if count >= threshold:
            fails[name] = count
    return fails


def strip_em_dashes(html: str) -> tuple[str, int]:
    """Replace ` — ` → `, ` and residual `—` → `,`, skipping pre/code/script/style.

    Returns (stripped_html, count_removed).
    """
    protected_blocks: list[str] = []

    def _protect(match: re.Match) -> str:
        protected_blocks.append(match.group(0))
        return f"\x00PROTECTED_{len(protected_blocks) - 1}\x00"

    protected_html = re.sub(
        r"<(pre|code|script|style)[^>]*>.*?</\1>",
        _protect,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    count_before = protected_html.count("—")
    stripped = protected_html.replace(" — ", ", ").replace("—", ",")
    count_after = stripped.count("—")

    def _restore(match: re.Match) -> str:
        return protected_blocks[int(match.group(1))]

    final_html = re.sub(r"\x00PROTECTED_(\d+)\x00", _restore, stripped)
    return final_html, count_before - count_after


def strip_meta_comment(html: str) -> str:
    """Strip one leading "Meta description:" writer artifact from the document head.

    Handles three rendered forms (HTML comment, blockquote, plain <p>) across
    en/vi/es/de/ja, only within the first 1500 chars, and only once.
    """
    meta_prefix = (
        r"(?:Meta\s+description(?:\s+(?:suggestion|gợi\s+ý))?|"
        r"Sugerencia\s+de\s+meta\s+descripci[óo]n|"
        r"Descripci[óo]n\s+meta|"
        r"Meta-Beschreibung(?:\s+Vorschlag)?|"
        r"メタディスクリプション)"
    )

    head_zone_len = min(1500, len(html))
    head = html[:head_zone_len]
    tail = html[head_zone_len:]

    # 1: HTML comment
    head = re.sub(
        rf"<!--\s*{meta_prefix}\s*:.*?-->\s*",
        "", head, count=1, flags=re.DOTALL | re.IGNORECASE,
    )
    # 2: blockquote (rendered from markdown `> Meta description ...`)
    head = re.sub(
        rf"<blockquote>\s*(?:<p>\s*)?{meta_prefix}\s*:.*?(?:</p>\s*)?</blockquote>\s*",
        "", head, count=1, flags=re.DOTALL | re.IGNORECASE,
    )
    # 3: plain leading <p>
    head = re.sub(
        rf"<p>\s*{meta_prefix}\s*:.*?</p>\s*",
        "", head, count=1, flags=re.DOTALL | re.IGNORECASE,
    )
    return (head + tail).lstrip("\n")


def strip_body_h1(html: str) -> str:
    """Remove every <h1>…</h1> from the body. WordPress renders the post TITLE as the page's
    <h1>, so a body H1 ships a duplicate H1 (an SEO + accessibility defect). The markdown source
    keeps its `# Title`; only the rendered body POSTed to WP is cleaned. (Ported from the kit's
    blog-publish wp_push_safe.strip_body_h1 so the publish path keeps enforcing it.)"""
    return re.sub(r"<h1\b[^>]*>.*?</h1>\s*", "", html, flags=re.DOTALL | re.IGNORECASE).lstrip("\n")
