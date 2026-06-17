"""Unit tests for the pure content-safety guards (parity with legacy wp_push_safe)."""

from client.guards import (
    detect_md_leak,
    strip_em_dashes,
    strip_meta_comment,
)


# --------------------------------------------------------------------------- #
# strip_em_dashes
# --------------------------------------------------------------------------- #

def test_emdash_spaced_becomes_comma():
    out, n = strip_em_dashes("<p>fast — clean — done</p>")
    assert out == "<p>fast, clean, done</p>"
    assert n == 2


def test_emdash_bare_residual_becomes_comma():
    out, n = strip_em_dashes("<p>a—b</p>")
    assert out == "<p>a,b</p>"
    assert n == 1


def test_emdash_protected_inside_code_block():
    html = "<p>x — y</p><pre>keep — this</pre><code>and — this</code>"
    out, n = strip_em_dashes(html)
    assert "<pre>keep — this</pre>" in out
    assert "<code>and — this</code>" in out
    assert "<p>x, y</p>" in out
    assert n == 1  # only the unprotected one counted/removed


def test_emdash_none_present():
    out, n = strip_em_dashes("<p>nothing here</p>")
    assert n == 0
    assert out == "<p>nothing here</p>"


# --------------------------------------------------------------------------- #
# detect_md_leak
# --------------------------------------------------------------------------- #

def test_leak_clean_html_is_safe():
    assert detect_md_leak("<h2>Title</h2><p>Body text.</p>") == {}


def test_leak_h2_markdown_above_threshold():
    body = "## one\ntext\n## two\nmore\n## three\n"  # threshold 3
    fails = detect_md_leak(body)
    assert fails.get("h2_md") == 3


def test_leak_h2_below_threshold_is_safe():
    body = "## one\n## two\n"  # below threshold of 3
    assert "h2_md" not in detect_md_leak(body)


def test_leak_inline_code_detected():
    body = "<p>use `a` and `b` and `c` and `d` inline</p>"  # threshold 4
    assert detect_md_leak(body).get("inline_code_md") == 4


def test_leak_code_block_is_exempt():
    # 5 inline-code spans, but all inside <pre> → stripped before scan → safe
    body = "<pre>`a` `b` `c` `d` `e`</pre>"
    assert detect_md_leak(body) == {}


def test_leak_table_rows_detected():
    body = "| a | b |\n| c | d |\n| e | f |\n"  # threshold 3
    assert detect_md_leak(body).get("table_md_row") == 3


# --------------------------------------------------------------------------- #
# strip_meta_comment
# --------------------------------------------------------------------------- #

def test_meta_comment_html_comment_form():
    out = strip_meta_comment("<!-- Meta description: hello there --><h1>T</h1>")
    assert "Meta description" not in out
    assert out.startswith("<h1>T</h1>")


def test_meta_comment_paragraph_form_vietnamese():
    out = strip_meta_comment("<p>Meta description gợi ý: xin chào</p><h1>T</h1>")
    assert "Meta description" not in out
    assert "<h1>T</h1>" in out


def test_meta_comment_blockquote_form():
    out = strip_meta_comment("<blockquote><p>Meta description: x</p></blockquote><h1>T</h1>")
    assert "Meta description" not in out


def test_meta_comment_only_strips_head_zone():
    # A legit later mention (>1500 chars in) must survive.
    filler = "<p>body</p>" * 200  # well over 1500 chars
    html = "<h1>T</h1>" + filler + "<p>Set the Meta description: to 155 chars</p>"
    out = strip_meta_comment(html)
    assert "Meta description" in out  # deep mention preserved


def test_meta_comment_noop_when_absent():
    html = "<h1>Title</h1><p>Normal intro.</p>"
    assert strip_meta_comment(html) == html
