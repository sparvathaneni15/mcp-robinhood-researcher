import os
import threading
import time
import secrets as _secrets

import pyotp
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

# Held in memory for the refresh loop
_refresh_token: str | None = None
_device_token: str | None = None


def _totp_code() -> str | None:
    secret = os.getenv("ROBINHOOD_TOTP_SECRET", "").strip()
    if not secret:
        return None
    return pyotp.TOTP(secret).now()


def _inject_tokens(access_token: str, token_type: str = "Bearer") -> None:
    """Set auth header on the robin_stocks session directly."""
    rh.helper.update_session("Authorization", f"{token_type} {access_token}")
    rh.helper.set_login_state(True)


def _refresh_via_oauth(refresh_tok: str, dev_token: str) -> tuple[str, str]:
    """
    Call the Robinhood OAuth refresh endpoint.
    Returns (new_access_token, new_refresh_token).
    """
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

    # ── Path 1: manual access token (passkey / browser token injection) ──
    access_token = os.getenv("ROBINHOOD_ACCESS_TOKEN", "").strip()
    refresh_tok = os.getenv("ROBINHOOD_REFRESH_TOKEN", "").strip()
    if access_token:
        _inject_tokens(access_token)
        dev = os.getenv("ROBINHOOD_DEVICE_TOKEN", "").strip()
        _device_token = dev or _secrets.token_hex(16)
        if refresh_tok:
            _refresh_token = refresh_tok
        with _lock:
            _logged_in = True
        print("[auth] Injected access token from environment", flush=True)
        return

    # ── Path 2: username/password, optionally with a known device token ──
    username = os.getenv("ROBINHOOD_USERNAME", "").strip()
    password = os.getenv("ROBINHOOD_PASSWORD", "").strip()
    if not username or not password:
        raise EnvironmentError(
            "Set ROBINHOOD_ACCESS_TOKEN (passkey flow) or "
            "ROBINHOOD_USERNAME + ROBINHOOD_PASSWORD in .env"
        )

    # If the user has a previously registered device token, patch it in so
    # Robinhood may recognise the device as trusted and skip MFA.
    env_device = os.getenv("ROBINHOOD_DEVICE_TOKEN", "").strip()
    if env_device:
        import robin_stocks.robinhood.authentication as _rh_auth
        _rh_auth.generate_device_token = lambda: env_device

    mfa_code = _totp_code()
    result = rh.login(
        username=username,
        password=password,
        expiresIn=86400,
        scope="internal",
        mfa_code=mfa_code,
        store_session=True,
    )

    if isinstance(result, dict):
        _refresh_token = result.get("refresh_token")
        _device_token = result.get("device_token") or env_device

    with _lock:
        _logged_in = True
    print("[auth] Logged in via username/password", flush=True)


def _refresh_worker() -> None:
    global _refresh_token, _device_token
    while True:
        time.sleep(23 * 3600)
        try:
            if _refresh_token and _device_token:
                new_access, new_refresh = _refresh_via_oauth(_refresh_token, _device_token)
                _inject_tokens(new_access)
                _refresh_token = new_refresh
                print("[auth] Token refreshed via OAuth refresh endpoint", flush=True)
            else:
                login()
                print("[auth] Token refreshed via re-login", flush=True)
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
