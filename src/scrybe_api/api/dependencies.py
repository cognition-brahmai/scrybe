from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from scrybe_api.config import Settings, get_settings


def get_app_state(request: Request):
    return request.app.state


def require_api_key(
    settings: Settings = Depends(get_settings),
    provided_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not settings.enable_auth:
        return
    if not settings.api_key_secret or provided_key != settings.api_key_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

