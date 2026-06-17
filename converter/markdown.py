"""Markdown-to-HTML and Markdown-to-Gutenberg conversion."""

import re
from typing import Literal

import markdown as md_lib


def markdown_to_html(md_text: str) -> str:
    return md_lib.markdown(md_text, extensions=["fenced_code", "tables", "attr_list"])


def markdown_to_gutenberg(md_text: str) -> str:
    html = markdown_to_html(md_text)
    blocks = []
    elements = _split_top_level_elements(html)
    for element in elements:
        stripped = element.strip()
        if not stripped:
            continue
        blocks.append(_wrap_in_gutenberg_block(stripped))
    return "\n\n".join(blocks)


def strip_frontmatter(md_text: str) -> str:
    stripped = md_text.lstrip()
    if stripped.startswith("---"):
        end = stripped.find("---", 3)
        if end != -1:
            stripped = stripped[end + 3:].lstrip("\n")
    stripped = re.sub(r"^# .+\n*", "", stripped, count=1)
    return stripped


def convert_markdown(md_text: str, editor_type: Literal["classic", "gutenberg"] = "classic") -> str:
    md_text = strip_frontmatter(md_text)
    if editor_type == "gutenberg":
        return markdown_to_gutenberg(md_text)
    return markdown_to_html(md_text)


_BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote", "pre", "table", "figure", "hr", "div"}
_OPEN_TAG_RE = re.compile(r"<(\w+)[\s>/]")
_CLOSE_TAG_RE = re.compile(r"</(\w+)>")
_SELF_CLOSING_TAGS = {"hr", "br", "img", "input"}


def _split_top_level_elements(html: str) -> list[str]:
    text = html.strip()
    if not text:
        return []
    elements = []
    lines = text.split("\n")
    current = []
    depth = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        open_match = re.match(r"<(\w+)[\s>/]", stripped)
        is_new_block = open_match and open_match.group(1).lower() in _BLOCK_TAGS and depth == 0
        if is_new_block and current:
            elements.append("\n".join(current))
            current = []
        current.append(line)
        for m in _OPEN_TAG_RE.finditer(stripped):
            tag = m.group(1).lower()
            if tag in _BLOCK_TAGS and tag not in _SELF_CLOSING_TAGS:
                depth += 1
        for m in _CLOSE_TAG_RE.finditer(stripped):
            tag = m.group(1).lower()
            if tag in _BLOCK_TAGS:
                depth = max(0, depth - 1)
    if current:
        elements.append("\n".join(current))
    return elements


def _wrap_in_gutenberg_block(html_element: str) -> str:
    tag_match = re.match(r"<(\w+)", html_element)
    if not tag_match:
        return f"<!-- wp:paragraph -->\n<p>{html_element}</p>\n<!-- /wp:paragraph -->"
    tag = tag_match.group(1).lower()
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = tag[1]
        return f'<!-- wp:heading {{"level":{level}}} -->\n{html_element}\n<!-- /wp:heading -->'
    if tag == "p":
        return f"<!-- wp:paragraph -->\n{html_element}\n<!-- /wp:paragraph -->"
    if tag == "ul":
        return f"<!-- wp:list -->\n{html_element}\n<!-- /wp:list -->"
    if tag == "ol":
        return f'<!-- wp:list {{"ordered":true}} -->\n{html_element}\n<!-- /wp:list -->'
    if tag == "blockquote":
        return f"<!-- wp:quote -->\n{html_element}\n<!-- /wp:quote -->"
    if tag == "pre":
        return f"<!-- wp:code -->\n{html_element}\n<!-- /wp:code -->"
    if tag == "table":
        return f'<!-- wp:table -->\n<figure class="wp-block-table">{html_element}</figure>\n<!-- /wp:table -->'
    if tag == "figure":
        return f"<!-- wp:image -->\n{html_element}\n<!-- /wp:image -->"
    if tag == "hr":
        return '<!-- wp:separator -->\n<hr class="wp-block-separator"/>\n<!-- /wp:separator -->'
    return f"<!-- wp:html -->\n{html_element}\n<!-- /wp:html -->"
