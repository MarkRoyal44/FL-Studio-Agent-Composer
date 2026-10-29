"""Commercial license codes.

Agent Composer is free under PolyForm Small Business 1.0.0 for people and companies with fewer
than 100 people and under US$1M a year in revenue. Bigger companies buy a commercial license
and get a code. The code is signed with Ed25519 (RFC 8032, written out below with the standard
library); this file holds only the public key, so it can check codes but never make them.

Code shape: AC1.<payload>.<signature>, both base64url. The payload is JSON: {"to", "id", "on", "until"}.
"until" is the last day the license covers (monthly or yearly plans); a code without it never ends.
"""
import base64
import datetime
import hashlib
import json
import os

import home

PUBLIC_KEY = "3908ec93772cd765d9b8676d3283368bbc6435180e83f9f9fdd3388bff2655e9"

# Ed25519, from RFC 8032 section 6.
_p = 2 ** 255 - 19
_d = -121665 * pow(121666, _p - 2, _p) % _p
_q = 2 ** 252 + 27742317777372353535851937790883648493
_sqrt_m1 = pow(2, (_p - 1) // 4, _p)


def _h(b):
    return int.from_bytes(hashlib.sha512(b).digest(), "little") % _q


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _equal(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _recover_x(y, sign):
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p:
        x = x * _sqrt_m1 % _p
    if (x * x - x2) % _p:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_gy = 4 * pow(5, _p - 2, _p) % _p
_gx = _recover_x(_gy, 0)
_G = (_gx, _gy, 1, _gx * _gy % _p)


def _compress(P):
    zi = pow(P[2], _p - 2, _p)
    x, y = P[0] * zi % _p, P[1] * zi % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _p)


def _expand(secret):
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_from_secret(secret):
    return _compress(_mul(_expand(secret)[0], _G))


def sign(secret, msg):
    a, prefix = _expand(secret)
    A = _compress(_mul(a, _G))
    r = _h(prefix + msg)
    R = _compress(_mul(r, _G))
    s = (r + _h(R + A + msg) * a) % _q
    return R + int.to_bytes(s, 32, "little")


def verify(public, msg, sig):
    if len(public) != 32 or len(sig) != 64:
        return False
    A, R = _decompress(public), _decompress(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if not A or not R or s >= _q:
        return False
    return _equal(_mul(s, _G), _add(R, _mul(_h(sig[:32] + public + msg), A)))


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_code(secret, to, lid, on, until=None):
    lic = {"to": to, "id": lid, "on": on}
    if until:
        lic["until"] = until
    payload = json.dumps(lic, separators=(",", ":")).encode()
    return "AC1." + _b64(payload) + "." + _b64(sign(secret, payload))


def read_code(code):
    """The license inside a code, or None if the code isn't one we signed."""
    try:
        tag, payload, sig = "".join(str(code).split()).split(".")
        payload = _unb64(payload)
        if tag != "AC1" or not verify(bytes.fromhex(PUBLIC_KEY), payload, _unb64(sig)):
            return None
        return json.loads(payload)
    except (ValueError, TypeError):
        return None


def _file():
    return os.path.join(home.path(), "license.json")


def current():
    try:
        with open(_file(), encoding="utf-8") as f:
            lic = read_code(json.load(f).get("code"))
    except (OSError, ValueError, AttributeError):
        lic = None
    if not lic:
        return {"commercial": False}
    out = {"to": lic.get("to"), "id": lic.get("id"), "on": lic.get("on"), "until": lic.get("until")}
    if out["until"] and out["until"] < datetime.date.today().isoformat():
        return {"commercial": False, "expired": True, **out}
    return {"commercial": True, **out}


def activate(code):
    lic = read_code(code)
    if not lic:
        return {"error": "That code didn't check out. Paste the whole thing, starting with AC1."}
    if lic.get("until") and lic["until"] < datetime.date.today().isoformat():
        return {"error": "That code ended on " + lic["until"] + ". Renew to get a new one."}
    with open(_file(), "w", encoding="utf-8") as f:
        json.dump({"code": "".join(str(code).split())}, f)
    return current()
