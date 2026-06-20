"""Regression tests for wp-auth credential resolution (client.auth._auth_from_cfg).

wp-auth.json may carry either a pre-built ``auth`` (``Basic <base64>``) OR
``username`` + ``app_password`` (the kit builds the Basic header, stripping the
App Password's spaces so it can be pasted exactly as WordPress shows it).
"""

import base64

import pytest

from client.auth import _auth_from_cfg
from client.guards import MissingCredentialsError


def _decode(header):
    assert header.startswith("Basic ")
    return base64.b64decode(header.split(" ", 1)[1]).decode()


def test_prebuilt_auth_passes_through():
    assert _auth_from_cfg({"auth": "Basic ABC123"}) == "Basic ABC123"


def test_username_app_password_builds_basic_header():
    h = _auth_from_cfg({"username": "admin", "app_password": "abcd efgh ijkl"})
    # App Password spaces are stripped before encoding
    assert _decode(h) == "admin:abcdefghijkl"


def test_wp_username_and_password_aliases():
    h = _auth_from_cfg({"wp_username": "u", "password": "p p p"})
    assert _decode(h) == "u:ppp"


def test_prebuilt_auth_wins_when_both_present():
    h = _auth_from_cfg({"auth": "Basic X", "username": "u", "app_password": "p"})
    assert h == "Basic X"


def test_missing_credentials_raises():
    with pytest.raises(MissingCredentialsError):
        _auth_from_cfg({"wp_base": "https://example.com/wp-json/wp/v2/posts"})
