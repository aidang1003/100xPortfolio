"""Daily email list: Upstash Redis for storage, Resend for sending. Both over plain HTTP.

Redis keys:
  subs:pending    set of emails awaiting the confirm click
  subs:confirmed  set of emails that get the daily
  subs:sent:<e>   confirm email throttle, expires after a day
  games:<e>       list of scored dailies (JSON), newest last

Links in emails carry a signed token (base64url email + HMAC), so nothing is looked up to trust them.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import urllib.request

from .config import SITE_URL

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PENDING, CONFIRMED = "subs:pending", "subs:confirmed"
RESEND_BATCH = 100  # Resend's batch cap


def _env(*names):
    return next((os.environ[n] for n in names if os.environ.get(n)), None)


def _post(url, body, token):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "User-Agent": "play100x"})  # Resend's Cloudflare blocks urllib's default agent
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read())


def _redis(*cmd):
    url = _env("KV_REST_API_URL", "UPSTASH_REDIS_REST_URL")
    token = _env("KV_REST_API_TOKEN", "UPSTASH_REDIS_REST_TOKEN")
    return _post(url, list(cmd), token)["result"]


def _send(emails):
    """emails: Resend message dicts, sent in batches."""
    key = os.environ["RESEND_API_KEY"]
    for i in range(0, len(emails), RESEND_BATCH):
        _post("https://api.resend.com/emails/batch", emails[i:i + RESEND_BATCH], key)


# --- signed tokens ---

def _sig(email):
    secret = os.environ["LINK_SECRET"].encode()
    return hmac.new(secret, email.encode(), hashlib.sha256).hexdigest()[:24]


def make_token(email):
    return base64.urlsafe_b64encode(email.encode()).decode().rstrip("=") + "." + _sig(email)


def read_token(token):
    """Email for a valid token, else None."""
    try:
        enc, sig = (token or "").split(".")
        email = base64.urlsafe_b64decode(enc + "=" * (-len(enc) % 4)).decode()
    except ValueError:
        return None
    return email if hmac.compare_digest(sig, _sig(email)) else None


# --- list ---

def normalize(email):
    email = (email or "").strip().lower()
    return email if len(email) <= 254 and EMAIL_RE.match(email) else None


def subscribe(email):
    """Queue a confirm email; repeats within a day are dropped so the form can't spam an inbox."""
    if _redis("SISMEMBER", CONFIRMED, email):
        return
    _redis("SADD", PENDING, email)
    if _redis("SET", f"subs:sent:{email}", "1", "NX", "EX", 86400):
        _send([_message(email, "Confirm your Play 100x daily puzzles", "Confirm your email",
                        "Tap below to start getting the daily puzzle.", f"{SITE_URL}/confirm?k={make_token(email)}")])


def confirm(email):
    _redis("SMOVE", PENDING, CONFIRMED, email) or _redis("SADD", CONFIRMED, email)


def unsubscribe(email):
    _redis("SREM", PENDING, email)
    _redis("SREM", CONFIRMED, email)


def record_game(email, result):
    _redis("RPUSH", f"games:{email}", json.dumps({
        "day": result["day"], "dayNumber": result["dayNumber"],
        "multiple": result["multiple"], "gameScore": result["gameScore"]}))


def send_daily(day_number):
    emails = _redis("SMEMBERS", CONFIRMED) or []
    _send([_message(e, f"Play 100x: Daily Puzzle #{day_number}", f"Daily Puzzle #{day_number} is live",
                    "Pick 5 stocks and see how they really played out.",
                    f"{SITE_URL}/d/{day_number}?k={make_token(e)}") for e in emails])
    return len(emails)


def _message(email, subject, heading, body, link):
    unsub = f"{SITE_URL}/unsubscribe?k={make_token(email)}"
    html = f"""<div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#111">
<h2 style="margin:0 0 12px">{heading}</h2>
<p style="margin:0 0 20px">{body}</p>
<p style="margin:0 0 32px"><a href="{link}" style="background:#2ee06b;color:#0b1207;padding:12px 20px;border-radius:10px;font-weight:700;text-decoration:none">Play 100x</a></p>
<p style="font-size:12px;color:#777"><a href="{unsub}" style="color:#777">Unsubscribe</a></p>
</div>"""
    return {
        "from": os.environ.get("EMAIL_FROM", "Play 100x <daily@play100x.com>"),
        "to": [email],
        "subject": subject,
        "html": html,
        "text": f"{heading}\n\n{body}\n\n{link}\n\nUnsubscribe: {unsub}",
        # One-click unsubscribe; Gmail and Yahoo require it for bulk mail.
        "headers": {"List-Unsubscribe": f"<{unsub}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
    }
