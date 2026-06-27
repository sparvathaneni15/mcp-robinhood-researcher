import os
import threading
import time
import secrets as _secrets

import requests as _requests
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

load_dotenv()

_lock = threading.Lock()
_logged_in = False
_refresh_thread: threading.Thread | None = None

# Robinhood OAuth client ID (public, same one the official app uses)
_RH_CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"
_RH_TOKEN_URL = "https://api.robinhood.com/oauth2/token/"

_refresh_token: str | None = None
_device_token: str | None = None


def _inject_tokens(access_token: str) -> None:
    rh.helper.update_session("Authorization", f"Bearer {access_token}")
    rh.helper.set_login_state(True)


def _refresh_via_oauth(refresh_tok: str, dev_token: str) -> tuple[str, str]:
    resp = _requests.post(
        _RH_TOKEN_URL,
        json={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": _RH_CLIENT_ID,
            "device_token": dev_token,
            "scope": "internal",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data.get("refresh_token", refresh_tok)


def login() -> None:
    global _logged_in, _refresh_token, _device_token

    access_token = os.getenv("ROBINHOOD_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise EnvironmentError(
            "ROBINHOOD_ACCESS_TOKEN must be set in .env. "
            "Get it from Chrome DevTools while logged into robinhood.com: "
            "Network tab → any api.robinhood.com request → Authorization header."
        )

    _inject_tokens(access_token)

    refresh_tok = os.getenv("ROBINHOOD_REFRESH_TOKEN", "").strip()
    dev = os.getenv("ROBINHOOD_DEVICE_TOKEN", "").strip()
    _device_token = dev or _secrets.token_hex(16)
    if refresh_tok:
        _refresh_token = refresh_tok

    with _lock:
        _logged_in = True
    print("[auth] Injected access token from environment", flush=True)


def _refresh_worker() -> None:
    global _refresh_token, _device_token
    while True:
        time.sleep(23 * 3600)
        try:
            if _refresh_token and _device_token:
                new_access, new_refresh = _refresh_via_oauth(_refresh_token, _device_token)
                _inject_tokens(new_access)
                _refresh_token = new_refresh
                print("[auth] Token refreshed", flush=True)
            else:
                print("[auth] No refresh token available — restart container with a fresh ROBINHOOD_ACCESS_TOKEN", flush=True)
        except Exception as exc:
            print(f"[auth] Token refresh failed: {exc}", flush=True)


def start_refresh_loop() -> None:
    global _refresh_thread
    with _lock:
        if _refresh_thread is None or not _refresh_thread.is_alive():
            _refresh_thread = threading.Thread(
                target=_refresh_worker,
                daemon=True,
                name="rh-token-refresh",
            )
            _refresh_thread.start()


def is_logged_in() -> bool:
    with _lock:
        return _logged_in
