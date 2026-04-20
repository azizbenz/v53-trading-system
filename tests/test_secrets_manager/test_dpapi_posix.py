from __future__ import annotations

import pytest

from secrets_manager import _dpapi_posix


def test_posix_keyring_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    monkeypatch.setattr(
        _dpapi_posix.keyring,
        "set_password",
        lambda service, token, payload: store.__setitem__((service, token), payload),
    )
    monkeypatch.setattr(
        _dpapi_posix.keyring,
        "get_password",
        lambda service, token: store.get((service, token)),
    )

    token = _dpapi_posix.protect_bytes(
        b"demo-secret",
        entropy=b"entropy",
        description="demo",
    )

    assert _dpapi_posix.unprotect_bytes(token, entropy=b"entropy") == b"demo-secret"


def test_posix_keyring_rejects_wrong_entropy(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    monkeypatch.setattr(
        _dpapi_posix.keyring,
        "set_password",
        lambda service, token, payload: store.__setitem__((service, token), payload),
    )
    monkeypatch.setattr(
        _dpapi_posix.keyring,
        "get_password",
        lambda service, token: store.get((service, token)),
    )

    token = _dpapi_posix.protect_bytes(b"demo-secret", entropy=b"good")

    with pytest.raises(_dpapi_posix.DpapiError, match="provided entropy"):
        _dpapi_posix.unprotect_bytes(token, entropy=b"bad")
