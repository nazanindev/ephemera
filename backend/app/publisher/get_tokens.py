"""One-time helper: run Tumblr's OAuth1 handshake and save your user tokens.

Use this when api.tumblr.com/console renders blank (common). It reads your app's
Consumer Key + Secret from .env (or prompts), and writes the resulting OAuth Token
+ Token Secret back into .env for you.

IMPORTANT: in the app's settings at https://www.tumblr.com/oauth/apps, set the
"Default callback URL" to exactly:
    http://localhost:8080/callback
(Tumblr validates the callback against the registered one.)

    cd backend && .venv/bin/python -m app.publisher.get_tokens
"""
from __future__ import annotations
import getpass
import os
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"
CALLBACK = "http://localhost:8080/callback"

ENV_PATH = Path(__file__).resolve().parent / ".env"


def _update_env(updates: dict[str, str]) -> bool:
    """Replace (or append) the given keys in .env, preserving everything else."""
    if not ENV_PATH.exists():
        return False
    lines = ENV_PATH.read_text().splitlines()
    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            key = s.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)
    for key, val in remaining.items():  # any keys not already present
        out.append(f"{key}={val}")
    ENV_PATH.write_text("\n".join(out) + "\n")
    return True


def main() -> int:
    load_dotenv(ENV_PATH)
    consumer_key = os.getenv("TUMBLR_CONSUMER_KEY", "").strip() or input("Consumer Key: ").strip()
    consumer_secret = os.getenv("TUMBLR_CONSUMER_SECRET", "").strip() or getpass.getpass("Consumer Secret (hidden): ").strip()

    # 1. Get a temporary request token.
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri=CALLBACK)
    req = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    owner_key = req["oauth_token"]
    owner_secret = req["oauth_token_secret"]

    # 2. Authorize in the browser. After you click Allow, Tumblr redirects to the
    #    localhost callback — it WON'T load (no server there), but the URL bar will
    #    contain ?oauth_verifier=... which is all we need. Copy that whole URL.
    auth_url = oauth.authorization_url(AUTHORIZE_URL)
    print("\nOpening this URL — click Allow, then copy the FULL URL it lands on:\n")
    print(auth_url, "\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    pasted = getpass.getpass("Paste the redirected URL (hidden, won't echo): ").strip()
    verifier = pasted
    if "oauth_verifier=" in pasted:
        verifier = parse_qs(urlparse(pasted).query)["oauth_verifier"][0]

    # 3. Exchange request token + verifier for the long-lived access token.
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=owner_key,
        resource_owner_secret=owner_secret,
        verifier=verifier,
    )
    tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    token = tokens["oauth_token"]
    token_secret = tokens["oauth_token_secret"]

    wrote = _update_env({"TUMBLR_OAUTH_TOKEN": token, "TUMBLR_OAUTH_TOKEN_SECRET": token_secret})
    if wrote:
        print("\n✓ saved TUMBLR_OAUTH_TOKEN + TUMBLR_OAUTH_TOKEN_SECRET to .env")
        print("  next:  .venv/bin/python -m app.publisher.publish verify")
    else:
        print("\n.env not found — paste these in manually:")
        print(f"TUMBLR_OAUTH_TOKEN={token}")
        print(f"TUMBLR_OAUTH_TOKEN_SECRET={token_secret}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
