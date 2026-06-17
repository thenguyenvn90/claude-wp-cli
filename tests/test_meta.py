"""Unit tests for meta focus-keyword merge logic + push_safe guard integration."""

from client.meta import _merge_focus, _split_focus
from client.posts import PostsClient


def test_split_focus_trims_and_drops_empty():
    assert _split_focus("a, b ,, c ") == ["a", "b", "c"]
    assert _split_focus("") == []


def test_merge_focus_unions_without_clobber():
    assert _merge_focus(["seo", "wordpress"], ["mcp"]) == ["seo", "wordpress", "mcp"]


def test_merge_focus_dedupes_case_insensitive_keeps_first():
    assert _merge_focus(["SEO"], ["seo", "MCP"]) == ["SEO", "MCP"]


def test_merge_focus_empty_add_is_noop():
    assert _merge_focus(["a", "b"], []) == ["a", "b"]


class _FakeClient:
    """A client whose .post() blows up — proves push_safe refuses BEFORE any network write."""

    def post(self, *a, **k):  # pragma: no cover - must never be called in these tests
        raise AssertionError("push_safe wrote to the network despite a guard refusal")


def test_push_safe_refuses_markdown_leak_without_writing():
    pc = PostsClient(_FakeClient())
    leaky = "## a\n## b\n## c\n## d\n"  # h2_md over threshold
    res = pc.push_safe(1, leaky, check_drift_enabled=False)
    assert res["pushed"] is False
    assert "leak" in res["refused"].lower()


def test_push_safe_force_bypasses_leak(monkeypatch):
    captured = {}

    class _OKClient:
        def post(self, endpoint, *, json):
            captured["json"] = json
            return {"id": 1, "modified": "now", "link": "x", "status": "draft"}

    pc = PostsClient(_OKClient())
    leaky = "## a\n## b\n## c\n"
    res = pc.push_safe(1, leaky, check_drift_enabled=False, force=True)
    assert res["pushed"] is True
    assert "content" in captured["json"]
