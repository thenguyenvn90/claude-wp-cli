"""WordPress Schema / Structured Data client."""
import json
import re
from typing import Optional
from .http import WPClient


class SchemaClient:
    def __init__(self, client: WPClient):
        self._client = client

    def get(self, *, post_id: int) -> dict:
        return self._client.get(f"posts/{post_id}", params={"context": "edit", "_fields": "id,meta"})

    def push(self, *, post_id: int, schema_data: dict, seo_plugin: str,
             expected_slug: Optional[str] = None) -> Optional[dict]:
        if seo_plugin == "none":
            return None
        # Guard against a wrong --post-id clobbering a different post (CWE-807): verify the
        # slug before any write when the caller knows what it should be.
        if expected_slug:
            from .posts import PostsClient
            ok, actual, msg = PostsClient(self._client).verify_slug(post_id, expected_slug)
            if not ok:
                raise ValueError(msg)
        schema_str = json.dumps(schema_data)
        if seo_plugin == "yoast":
            return self._client.post(f"posts/{post_id}", json={"meta": {"_yoast_wpseo_schema_json": schema_str}})
        elif seo_plugin == "generic":
            return self._client.post(f"posts/{post_id}", json={"meta": {"_schema_jsonld": schema_str}})
        elif seo_plugin == "rankmath":
            return self._push_rankmath(post_id, schema_data)
        return None

    def _push_rankmath(self, post_id: int, schema: dict) -> Optional[dict]:
        if schema.get("@type") != "FAQPage":
            return None
        questions = schema.get("mainEntity", [])
        if not questions:
            return None
        faq_items = []
        for q in questions:
            name = q.get("name", "")
            answer = q.get("acceptedAnswer", {}).get("text", "")
            if name and answer:
                faq_items.append(f'<div class="rank-math-faq-item"><h3 class="rank-math-question">{name}</h3><div class="rank-math-answer">{answer}</div></div>')
        if not faq_items:
            return None
        faq_block = '<!-- wp:rank-math/faq-block --><div class="wp-block-rank-math-faq-block">' + "".join(faq_items) + "</div><!-- /wp:rank-math/faq-block -->"
        current = self._client.get(f"posts/{post_id}", params={"context": "edit", "_fields": "id,content"})
        current_content = current["content"]["raw"]
        # Strip a PREVIOUS tool-written FAQ block, anchored to its exact comment delimiters so the
        # regex can't greedily eat adjacent markup (the old `.*?</div></div>` pattern could over-match).
        current_content = re.sub(
            r'<!-- wp:rank-math/faq-block -->.*?<!-- /wp:rank-math/faq-block -->\s*',
            "", current_content, flags=re.DOTALL
        ).rstrip()
        return self._client.post(f"posts/{post_id}", json={"content": current_content + "\n" + faq_block})
