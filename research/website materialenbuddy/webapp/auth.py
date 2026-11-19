"""Authentik OIDC login en server-side controle van rollen."""

import os
import logging
import secrets
import time
from urllib.parse import urlsplit

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware


router = APIRouter()
oauth = OAuth()
SESSION_SECONDS = 3600


def configure_auth(app):
    secret = os.getenv("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET ontbreekt of is korter dan 32 tekens.")
    required = ("AUTHENTIK_DISCOVERY_URL", "AUTHENTIK_CLIENT_ID",
                "AUTHENTIK_CLIENT_SECRET", "AUTHENTIK_REDIRECT_URI")
    if any(not os.getenv(key) for key in required):
        raise RuntimeError("Vul de AUTHENTIK-instellingen uit .env.example in.")
    admin_group = os.getenv("AUTHENTIK_ADMIN_GROUP", "materialenbuddy-admins")
    user_group = os.getenv("AUTHENTIK_USER_GROUP", "materialenbuddy-users")
    if admin_group == user_group:
        raise RuntimeError("De admin- en gebruikersgroep moeten verschillen.")
    oauth.register(
        name="authentik",
        client_id=os.environ["AUTHENTIK_CLIENT_ID"],
        client_secret=os.environ["AUTHENTIK_CLIENT_SECRET"],
        server_metadata_url=os.environ["AUTHENTIK_DISCOVERY_URL"],
        client_kwargs={"scope": "openid profile email", "code_challenge_method": "S256"},
    )
    app.add_middleware(
        SessionMiddleware, secret_key=secret, session_cookie="materialenbuddy_session",
        max_age=None, same_site="lax",
        https_only=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
    )
    app.include_router(router)


def role_from_claims(claims):
    groups = claims.get("groups", [])
    if not isinstance(groups, list):
        return None
    if os.getenv("AUTHENTIK_ADMIN_GROUP", "materialenbuddy-admins") in groups:
        return "admin"
    if os.getenv("AUTHENTIK_USER_GROUP", "materialenbuddy-users") in groups:
        return "user"
    return None


def current_user(request: Request):
    user = request.session.get("user")
    if not user or request.session.get("expires_at", 0) <= time.time():
        request.session.clear()
        raise HTTPException(401, "Log eerst in via Authentik.")
    return user


def require_write(request: Request, user=Depends(current_user)):
    supplied = request.headers.get("X-CSRF-Token", "")
    expected = request.session.get("csrf", "")
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(403, "Ongeldig beveiligingstoken. Herlaad de pagina.")
    return user


def require_admin(user=Depends(require_write)):
    if user["role"] != "admin":
        raise HTTPException(403, "Alleen een admin mag deze actie uitvoeren.")
    return user


@router.get("/auth/login")
async def login(request: Request):
    request.session.clear()
    return await oauth.authentik.authorize_redirect(
        request, os.environ["AUTHENTIK_REDIRECT_URI"],
        prompt="login",
    )


@router.get("/auth/callback")
async def callback(request: Request):
    try:
        # Authlib verifieert state, nonce, handtekening, issuer, audience en vervaltijd.
        token = await oauth.authentik.authorize_access_token(request)
    except (OAuthError, ValueError) as exc:
        logging.getLogger(__name__).warning(
            "OIDC callback failed: %s (error=%s)",
            type(exc).__name__, getattr(exc, "error", "validation_error"),
        )
        request.session.clear()
        raise HTTPException(401, "Aanmelden mislukt. Probeer opnieuw via /auth/login.")
    claims = token.get("userinfo", {})
    role = role_from_claims(claims)
    request.session.clear()
    if not claims.get("sub") or not role:
        raise HTTPException(403, "Je account behoort niet tot een MaterialenBuddy-groep.")
    request.session.update({
        "user": {"sub": claims["sub"], "name": claims.get("name") or
                 claims.get("preferred_username") or "Gebruiker", "role": role},
        "csrf": secrets.token_urlsafe(32),
        "expires_at": min(time.time() + SESSION_SECONDS, claims.get("exp", 0)),
    })
    return RedirectResponse("/", status_code=303)


@router.get("/auth/me")
def me(request: Request, user=Depends(current_user)):
    return {**user, "csrf_token": request.session["csrf"]}


@router.post("/auth/logout")
def logout(request: Request, user=Depends(require_write)):
    request.session.clear()
    authentik_url = urlsplit(os.environ["AUTHENTIK_DISCOVERY_URL"])
    logout_url = (
        f"{authentik_url.scheme}://{authentik_url.netloc}"
        "/if/flow/materialenbuddy-uitloggen/"
    )
    return {"detail": "Uitgelogd bij MaterialenBuddy.", "logout_url": logout_url}
