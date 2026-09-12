import base64
import json
import re
import urllib.parse

import Cryptodome.Cipher.AES

from libflagship.util import unhex, b64d

cachekey = unhex("1b55f97793d58864571e1055838cac97")

_WEBVIEW_USERINFO_KEYS = (
    b"userinfo",
    b"vms-userinfo",
)
_WEBVIEW_FRAGMENT_RE = re.compile(rb"[A-Za-z0-9+/=]{20,}")
_WEBVIEW_TOKEN_RE = re.compile(r"([0-9a-f]{47,48})%")
_WEBVIEW_REGION_RE = re.compile(r'%22ab_code%22%3A%22([A-Z]{2})%22')
_WEBVIEW_JSON_TOKEN_RE = re.compile(r'"auth_token"\s*:\s*"([0-9a-f]{47,48})"')
_WEBVIEW_JSON_REGION_RE = re.compile(r'"ab_code"\s*:\s*"([A-Z]{2})"')
_WEBVIEW_JSON_USER_ID_RE = re.compile(r'"user_id"\s*:\s*"([^"]+)"')
_WEBVIEW_JSON_EMAIL_RE = re.compile(r'"email"\s*:\s*"([^"]+)"')
_WEBVIEW_WINDOW_BYTES = 8192


def guess_region(cc):
    us_regions = {"US", "CA", "MX", "BR", "AR", "CU", "BS", "AU", "NZ"}
    if cc in us_regions:
        return "us"
    else:
        return "eu"


def decrypt(data, key=cachekey):
    raw = b64d(data)

    aes = Cryptodome.Cipher.AES.new(key=key, mode=Cryptodome.Cipher.AES.MODE_ECB)
    pmsg = aes.decrypt(raw)
    return pmsg.rstrip(b"\x00").decode()


def _to_bytes(data):
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8", "ignore")
    return bytes(data)


def has_webview_session_marker(data):
    blob = _to_bytes(data)
    return any(key in blob for key in _WEBVIEW_USERINFO_KEYS)


def _iter_webview_windows(data):
    blob = _to_bytes(data)
    seen = set()

    for key in _WEBVIEW_USERINFO_KEYS:
        start = 0
        while True:
            idx = blob.find(key, start)
            if idx < 0:
                break
            if idx not in seen:
                seen.add(idx)
                yield blob[idx:idx + _WEBVIEW_WINDOW_BYTES]
            start = idx + len(key)


def _iter_webview_fragment_candidates(fragment):
    # WebView LevelDB records often splice a few framing bytes into the
    # payload, so try a small set of trimmed candidates before decoding.
    candidates = []
    seen = set()
    fraglen = len(fragment)
    for left in range(0, 4):
        for right in range(0, 4):
            end = fraglen - right if right else fraglen
            candidate = fragment[left:end]
            if len(candidate) < 12 or candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def _iter_webview_decoded_fragments(data):
    seen = set()

    for window in _iter_webview_windows(data):
        for match in _WEBVIEW_FRAGMENT_RE.finditer(window):
            fragment = match.group(0)

            for candidate in _iter_webview_fragment_candidates(fragment):
                padded = candidate + (b"=" * (-len(candidate) % 4))
                try:
                    decoded = base64.b64decode(padded, validate=False).decode("utf-8", "ignore")
                except Exception:
                    continue
                if not decoded or decoded in seen:
                    continue
                seen.add(decoded)
                yield decoded


def _session_from_json_payload(payload):
    try:
        obj = json.loads(payload)
    except Exception:
        return None

    if not isinstance(obj, dict):
        return None

    auth_token = obj.get("auth_token")
    if not auth_token:
        return None

    data = {
        "auth_token": auth_token,
        "ab_code": obj.get("ab_code") or "US",
    }

    for key in ("user_id", "email"):
        value = obj.get(key)
        if value:
            data[key] = value

    return data


def _extract_fragment_fields(fragment):
    candidates = []
    decoded = urllib.parse.unquote(fragment)
    candidates.append(fragment)
    if decoded != fragment:
        candidates.append(decoded)

    merged = {}

    for candidate in candidates:
        if not candidate:
            continue

        stripped = candidate.strip()
        if stripped.startswith("{"):
            data = _session_from_json_payload(stripped)
            if data:
                merged.update(data)

        token_match = _WEBVIEW_JSON_TOKEN_RE.search(candidate)
        if token_match:
            merged["auth_token"] = token_match.group(1)
        elif "auth_token" not in merged:
            token_match = _WEBVIEW_TOKEN_RE.search(candidate)
            if token_match:
                merged["auth_token"] = token_match.group(1)

        region_match = _WEBVIEW_JSON_REGION_RE.search(candidate)
        if region_match:
            merged["ab_code"] = region_match.group(1)
        elif "ab_code" not in merged:
            region_match = _WEBVIEW_REGION_RE.search(candidate)
            if region_match:
                merged["ab_code"] = region_match.group(1)

        user_id_match = _WEBVIEW_JSON_USER_ID_RE.search(candidate)
        if user_id_match:
            merged["user_id"] = user_id_match.group(1)

        email_match = _WEBVIEW_JSON_EMAIL_RE.search(candidate)
        if email_match:
            merged["email"] = email_match.group(1)

    return merged


def _load_webview_session(data):
    merged = {}

    for fragment in _iter_webview_decoded_fragments(data) or ():
        fields = _extract_fragment_fields(fragment)
        if not fields:
            continue

        for key, value in fields.items():
            current = merged.get(key)
            if current is None:
                merged[key] = value
                continue

            if key == "auth_token" and len(value) > len(current):
                merged[key] = value

        if merged.get("auth_token") and len(merged["auth_token"]) == 48 and merged.get("ab_code"):
            break

    auth_token = merged.get("auth_token")
    if not auth_token:
        return None

    if not merged.get("ab_code"):
        # Fall back to US when the WebView session did not expose ab_code
        # cleanly. Region selection is only US/EU in current importer logic.
        merged["ab_code"] = "US"

    return {"data": merged}


def load(data, key=cachekey):
    try:
        raw = decrypt(data, key)
    except Exception:
        # older versions of AnkerMake Slicer (now eufyMake Studio) saved unencrypted login
        # credentials in login, so attempt to decode the file contents as-is
        raw = data

    try:
        return json.loads(raw.strip())
    except Exception as err:
        cache = _load_webview_session(data)
        if cache is not None:
            return cache
        raise err
