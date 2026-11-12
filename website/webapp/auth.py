import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import ExpiredSignatureError, JWTError, jwt

router = APIRouter(prefix="/auth")

# --- Configuratie -----------------------------------------------------------
AUTHENTIK_ISSUER = os.getenv("AUTHENTIK_ISSUER", "http://localhost:9000")
AUTHENTIK_CLIENT_ID = os.getenv("AUTHENTIK_CLIENT_ID", "materialenbuddy")
AUTHENTIK_CLIENT_SECRET = os.getenv("AUTHENTIK_CLIENT_SECRET", "")
AUTHENTIK_REDIRECT_URI = os.getenv("AUTHENTIK_REDIRECT_URI", "http://localhost:8000/auth/callback")
# De issuer blijft browser-gericht (localhost). Server-naar-server calls
# (token + JWKS) lopen via AUTHENTIK_SERVER_URL; in Docker is de host alleen
# bereikbaar via host.docker.internal.
_authentik_server_url = os.getenv("AUTHENTIK_SERVER_URL", "").strip()
if not _authentik_server_url:
    _authentik_server_url = AUTHENTIK_ISSUER
    if os.path.exists("/.dockerenv"):
        _authentik_server_url = _authentik_server_url.replace("localhost", "host.docker.internal", 1)
AUTHENTIK_SERVER_URL = _authentik_server_url.rstrip("/")
# Met per_provider issuer-mode voegt Authentik de applicatie-slug aan de
# issuer-URL toe: http://host:9000/application/o/<client_id>/
# BELANGRIJK: de `iss`-claim in de id_token wordt door Authentik gestempeld op
# basis van het Host-header van de TOKEN-request (server-naar-server), dus de
# verwachte issuer is afgeleid van AUTHENTIK_SERVER_URL, niet van de
# browser-gerichte localhost-issuer.
AUTHENTIK_REAL_ISSUER = (
    AUTHENTIK_SERVER_URL
    + "/application/o/"
    + AUTHENTIK_CLIENT_ID
    + "/"
)
SESSION_SECRET = os.getenv("SESSION_SECRET", "materialenbuddy_dev_session_secret")
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(8 * 3600)))

SESSION_COOKIE = "mb_session"
PKCE_COOKIE = "mb_pkce"

# RP-Initiated Logout: de browser-navigatie naar deze endpoint verwijdert de
# Authentik-browsersessie (niet alleen onze lokale cookie). De URL is
# browser-gericht (localhost), want de browser navigeert er zelf naartoe.
AUTHENTIK_END_SESSION_URL = (
    AUTHENTIK_ISSUER.rstrip("/")
    + f"/application/o/{AUTHENTIK_CLIENT_ID}/end-session/"
)
POST_LOGOUT_REDIRECT_URI = "http://localhost:8000/"


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding.encode())


def _build_jwks() -> Any:
    """Haal het JWKS van Authentik op en zet de open sloten in een cache."""
    jwks_json = None
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"{AUTHENTIK_SERVER_URL}/application/o/{AUTHENTIK_CLIENT_ID}/jwks/",
            timeout=10,
        ) as response:
            jwks_json = response.read()
    except Exception:
        raise HTTPException(status_code=503, detail="Kan JWKS niet ophalen van Authentik")

    jwks = json.loads(jwks_json)
    if not jwks.get("keys"):
        raise HTTPException(status_code=503, detail="JWKS bevat geen sleutels")

    # jose 3.x's jwt.decode accepteert een JWKS-dict ("{"keys": [...]}") direct
    # als key en controleert de signatuur zelf.
    return jwks


_jwks_cache: dict[str, Any] = {}


def _get_jwks() -> dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get("keys")
    if cached is None or now - _jwks_cache.get("fetched_at", 0) > 3600:
        _jwks_cache["keys"] = _build_jwks()
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


def _is_staff(claims: dict[str, Any]) -> bool:
    """Bepaal of de gebruiker de staff-rol heeft.

    Authentik stuurt attributen mee in de ID-token als ze zijn geconfigureerd
    (bv. staff=true) of via de 'authentik_groups' claim. Zonder configuratie
    krijgt iedereen met een geldige login toegang.
    """
    if claims.get("staff") is True:
        return True
    groepen = claims.get("authentik_groups") or claims.get("groups") or []
    return "staff" in {str(groep).lower() for groep in groepen}


def _create_session_cookie(email: str, name: str, staff: bool, id_token: str = "") -> str:
    payload = {
        "email": email,
        "name": name,
        "staff": staff,
        # Bewaard voor RP-Initiated Logout: met deze token kunnen we bij
        # logout ook de Authentik-browsersessie beëindigen, anders blijft die
        # leven en wordt de gebruiker bij de volgende login automatisch
        # herkend (en direct weer aangemeld).
        "id_token": id_token,
        "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
    }
    return jwt.encode(payload, SESSION_SECRET, algorithm="HS256")


def _parse_session_cookie(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            SESSION_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None
    if not payload.get("exp") or payload["exp"] < time.time():
        return None
    return payload


# --- Endpoints ---------------------------------------------------------------
@router.get("/login")
async def login() -> RedirectResponse:
    """Start de OAuth2/PKCE-loginflow bij Authentik."""
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    params = urllib.parse.urlencode(
        {
            "client_id": AUTHENTIK_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": AUTHENTIK_REDIRECT_URI,
            "scope": "openid profile email",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    authorize_url = f"{AUTHENTIK_ISSUER}/application/o/authorize/?{params}"

    response = RedirectResponse(authorize_url, status_code=302)
    response.set_cookie(
        PKCE_COOKIE,
        code_verifier,
        httponly=True,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
    code_verifier: str | None = Cookie(default=None, alias=PKCE_COOKIE),
) -> RedirectResponse:
    """Vervolg van de loginflow: wissel de code om voor tokens en zet de sessie."""
    if error:
        raise HTTPException(status_code=400, detail=f"Login mislukt: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Geen code ontvangen van Authentik")
    if not code_verifier:
        raise HTTPException(status_code=400, detail="PKCE-verifier ontbreekt, probeer opnieuw")

    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": AUTHENTIK_REDIRECT_URI,
            "client_id": AUTHENTIK_CLIENT_ID,
            "client_secret": AUTHENTIK_CLIENT_SECRET,
            "code_verifier": code_verifier,
        }
    ).encode()

    try:
        req = urllib.request.Request(
            f"{AUTHENTIK_SERVER_URL}/application/o/token/",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            token_data = json.loads(response.read())
    except Exception:
        raise HTTPException(status_code=502, detail="Tokenverwisseling met Authentik mislukt")

    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="Geen id_token teruggekregen")

    # Eén decode met signatuurverificatie: jose 3.x verifieert de RS256-signatuur
    # tegen het JWKS en controleert automatisch aud/iss/exp.
    try:
        payload = jwt.decode(
            id_token,
            _get_jwks(),
            algorithms=["RS256"],
            audience=AUTHENTIK_CLIENT_ID,
            issuer=AUTHENTIK_REAL_ISSUER,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="id_token is verlopen")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Ongeldige id_token")

    claims = payload
    session_cookie = _create_session_cookie(
        email=claims.get("email", "onbekend"),
        name=claims.get("name", claims.get("preferred_username", "Gebruiker")),
        staff=_is_staff(claims),
        id_token=id_token,
    )

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        session_cookie,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    response.delete_cookie(PKCE_COOKIE)
    return response


@router.get("/me")
async def me(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> JSONResponse:
    """Levert de huidige sessie; leegt de lijst bij niet-geauthoriseerde gebruikers."""
    payload = _parse_session_cookie(session)
    if payload is None:
        return JSONResponse({"authenticated": False})
    return JSONResponse(
        {
            "authenticated": True,
            "name": payload.get("name", "Gebruiker"),
            "email": payload.get("email", ""),
            "staff": bool(payload.get("staff", False)),
        }
    )


@router.get("/logout")
async def logout_get(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> RedirectResponse:
    """RP-Initiated Logout.

    Verwijdert de lokale sessiecookie EN navigeert de browser naar de
    `end-session` endpoint van Authentik. Daarmee wordt de Authentik-
    browsersessie zelf ook beëindigd; zonder deze stap blijft die leven en
    wordt de gebruiker bij de volgende login automatisch herkend (direct
    weer aangemeld).
    """
    payload = _parse_session_cookie(session)
    id_token = (payload or {}).get("id_token", "")

    params = urllib.parse.urlencode(
        {
            "post_logout_redirect_uri": POST_LOGOUT_REDIRECT_URI,
            "id_token_hint": id_token,
        }
    )

    response = RedirectResponse(
        f"{AUTHENTIK_END_SESSION_URL}?{params}", status_code=302
    )
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.post("/logout")
async def logout_post(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> JSONResponse:
    """Compat-variant voor fetch-calls: wist alleen de lokale cookie.

    Voor een volledige logout (ook de Authentik-sessie) moet de browser
    via `GET /auth/logout` navigeren.
    """
    payload = _parse_session_cookie(session)
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(SESSION_COOKIE)
    # Handig voor de frontend: laat weten of er nog een id_token is om de
    # browser met te sturen (valse waarheid niet; we sturen de redirect).
    response.headers["X-MaterialenBuddy-Logout-Redirect"] = (
        f"{AUTHENTIK_END_SESSION_URL}?{urllib.parse.urlencode({'post_logout_redirect_uri': POST_LOGOUT_REDIRECT_URI, 'id_token_hint': (payload or {}).get('id_token', '')})}"
        if payload
        else POST_LOGOUT_REDIRECT_URI
    )
    return response


# --- Dependencies voor beveiligde endpoints -----------------------------------
def require_auth(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, Any]:
    payload = _parse_session_cookie(session)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Niet aangemeld",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return payload


def require_staff(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, Any]:
    payload = _parse_session_cookie(session)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Niet aangemeld",
            headers={"WWW-Authenticate": "Cookie"},
        )
    if not payload.get("staff"):
        raise HTTPException(status_code=403, detail="Alleen personeel mag voorraad aanvullen")
    return payload
