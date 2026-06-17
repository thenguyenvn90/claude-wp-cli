"""WordPress ACF / Custom Fields REST API client."""
from .http import WPClient


class FieldsClient:
    def __init__(self, client: WPClient):
        self._client = client

    def get(self, *, post_id: int, post_type: str = "posts") -> dict:
        return self._client.get(f"{post_type}/{post_id}", params={"_fields": "id,acf,meta"})

    def update(self, *, post_id: int, data: dict, post_type: str = "posts") -> dict:
        return self._client.post(f"{post_type}/{post_id}", json={"acf": data})
