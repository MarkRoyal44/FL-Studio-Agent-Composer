"""Mini Brain: the person's own documents, searchable by whichever brain is plugged in.

Files live in Documents/Agent Composer/Mini Brain. Anything dropped there counts, whether it came
through the app's upload button or Explorer. Text is pulled out once and cached in state/minibrain/.
Standard library only, so it reads .txt .md .csv .json .lrc .srt .html .rtf .docx and most .pdf files.
"""
import base64
import html
import json
import os
import re
import zipfile
import zlib

import home

TEXT = (".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".lrc", ".srt", ".vtt", ".log", ".ini", ".yaml", ".yml")
MARKUP = (".html", ".htm", ".xml")
KINDS = TEXT + MARKUP + (".rtf", ".docx", ".pdf")
MAX_BYTES = 25 * 1024 * 1024
PART = 4000
STOP = set("the and for with that this from your you are was were have has had not but what when where which who how "
           "can will would should could about into over than then them they their there these those its our out any "
           "all one two get got make made just like some more most very also".split())


def folder():
    return home.path("Mini Brain")


def on():
    return bool(home.settings().get("mini_brain", True))


def _safe(name):
    name = os.path.basename(str(name or "")).strip()
    return name if name and not name.startswith(".") else ""


# ---- Pulling text out ----

def _strip_markup(s):
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<(br|/p|/div|/li|/h\d|/tr)\b[^>]*>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _rtf(s):
    s = re.sub(r"\\par[d]?\b", "\n", s)
    s = re.sub(r"\\'([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"\\[a-z]+-?\d* ?", "", s)
    return re.sub(r"[{}]", "", s)


def _docx(p):
    with zipfile.ZipFile(p) as z:
        x = z.read("word/document.xml").decode("utf-8", "replace")
    x = re.sub(r"</w:p>", "\n", x)
    x = re.sub(r"<w:tab/>", "\t", x)
    return html.unescape(re.sub(r"<[^>]+>", "", x))


def _pdf_string(s):
    out, i = [], 0
    esc = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "(": "(", ")": ")", "\\": "\\"}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n in esc:
                out.append(esc[n]); i += 2; continue
            m = re.match(r"[0-7]{1,3}", s[i + 1:])
            if m:
                out.append(chr(int(m.group(), 8))); i += 1 + len(m.group()); continue
            i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def _pdf(p):
    # Best effort: inflate each content stream and keep the text-showing operators.
    # Scanned or font-encoded PDFs come back empty; the person is told to save them as text.
    with open(p, "rb") as f:
        raw = f.read()
    lines = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        data = m.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:
            pass
        s = data.decode("latin-1")
        if "BT" not in s:
            continue
        for block in re.findall(r"BT(.*?)ET", s, re.S):
            parts = []
            for tok in re.finditer(r"\((?:\\.|[^\\)])*\)|T\*|Td|TD|'|\"", block):
                t = tok.group()
                if t.startswith("("):
                    parts.append(_pdf_string(t[1:-1]))
                elif parts:
                    parts.append("\n")
            line = "".join(parts).strip()
            if line:
                lines.append(line)
    return "\n".join(lines)


def _readable(t):
    letters = sum(ch.isalpha() for ch in t)
    return len(t) > 20 and letters / max(len(t), 1) > 0.4


def extract(p):
    ext = os.path.splitext(p)[1].lower()
    if ext == ".docx":
        return _docx(p)
    if ext == ".pdf":
        return _pdf(p)
    with open(p, "rb") as f:
        s = f.read().decode("utf-8-sig", "replace")
    if ext in MARKUP:
        return _strip_markup(s)
    if ext == ".rtf":
        return _rtf(s)
    return s


def _cache_dir():
    return home.path("state", "minibrain")


def text(name):
    """The document's text, pulled out once and re-pulled when the file changes."""
    name = _safe(name)
    p = os.path.join(folder(), name)
    if not name or not os.path.isfile(p):
        return None
    st = os.stat(p)
    key = "%d-%d" % (st.st_mtime, st.st_size)
    c = os.path.join(_cache_dir(), name + ".json")
    try:
        with open(c, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("key") == key:
            return d["text"]
    except (OSError, ValueError):
        pass
    try:
        t = extract(p)
    except Exception:  # a broken file shouldn't take the whole brain down
        t = ""
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t).strip()
    if not _readable(t):
        t = ""
    with open(c, "w", encoding="utf-8") as f:
        json.dump({"key": key, "text": t}, f)
    return t


# ---- The folder ----

def docs():
    out = []
    for n in sorted(os.listdir(folder()), key=str.lower):
        p = os.path.join(folder(), n)
        if not os.path.isfile(p) or n.startswith(".") or not n.lower().endswith(KINDS):
            continue
        t = text(n) or ""
        out.append({"name": n, "kb": round(os.path.getsize(p) / 1024), "chars": len(t),
                    "parts": max(1, -(-len(t) // PART)), "readable": bool(t)})
    return out


def add(name, data_b64):
    name = _safe(name)
    if not name:
        return {"success": False, "error": "That file needs a name."}
    if not name.lower().endswith(KINDS):
        return {"success": False, "error": "Mini Brain reads %s files." % ", ".join(KINDS)}
    try:
        raw = base64.b64decode(data_b64 or "", validate=True)
    except ValueError:
        return {"success": False, "error": "The upload came through broken. Try again."}
    if len(raw) > MAX_BYTES:
        return {"success": False, "error": "That file is over 25 MB."}
    with open(os.path.join(folder(), name), "wb") as f:
        f.write(raw)
    t = text(name) or ""
    return {"success": True, "name": name, "chars": len(t), "readable": bool(t),
            "note": "" if t else "Saved, but no text came out of it. Scanned PDFs need saving as .txt or .docx first."}


def remove(name):
    name = _safe(name)
    p = os.path.join(folder(), name)
    if not name or not os.path.isfile(p):
        return {"success": False, "error": "No document called %r." % name}
    os.remove(p)
    try:
        os.remove(os.path.join(_cache_dir(), name + ".json"))
    except OSError:
        pass
    return {"success": True}


# ---- What the brains call ----

def _stem(w):
    # Rough, so "tune", "tuned", "tuning" and "tunes" all meet at "tun", and "808s" finds "808".
    for suf in ("ing", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[:-len(suf)]
            break
    return w[:-1] if w.endswith("e") and len(w) > 3 else w


def _words(s):
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in STOP]


def search(query, limit=5):
    terms = set(_words(query))
    if not terms:
        return []
    hits = []
    for d in docs():
        t = text(d["name"]) or ""
        title = set(_words(d["name"]))
        for i in range(0, len(t), PART // 2):
            chunk = t[i:i + PART]
            ws = _words(chunk)
            if not ws:
                continue
            found = {w for w in ws if w in terms}
            score = sum(ws.count(w) for w in found) / (len(ws) ** 0.5) + 2 * len(found) + 3 * len(title & terms)
            if found:
                hits.append((score, d["name"], i // PART, chunk))
    hits.sort(key=lambda h: -h[0])
    out, seen = [], set()
    for score, name, part, chunk in hits:
        if (name, part) in seen:
            continue
        seen.add((name, part))
        out.append({"document": name, "part": part, "excerpt": chunk[:900].strip()})
        if len(out) >= limit:
            break
    return out


def read(name, part=0):
    t = text(name)
    if t is None:
        return {"success": False, "error": "No document called %r. Call brain_list to see them." % name}
    parts = max(1, -(-len(t) // PART))
    part = min(max(int(part), 0), parts - 1)
    return {"success": True, "document": _safe(name), "part": part, "parts": parts, "text": t[part * PART:(part + 1) * PART]}
