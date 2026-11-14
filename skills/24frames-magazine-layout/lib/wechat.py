"""WeChat OA API with the kit's safety rules (kit.json → safety). Only allow-listed endpoints can be called.
Credentials: env WECHAT_APPID + WECHAT_APPSECRET, or WECHAT_ENV_FILE=<KEY=VALUE file>. Never printed.
Token cache: env WECHAT_TOKEN_CACHE, default ~/.cache/24frames-magazine-layout/wechat_token.json (mode 600)."""
import json, os, re, sys, time, io, hashlib
import requests
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__)); import kit
S = kit.CFG["safety"]; API = "https://api.weixin.qq.com/cgi-bin"; LIMIT_IMG = 1_000_000
def _env():
    d = {}
    f = os.environ.get("WECHAT_ENV_FILE")
    if f:
        for line in open(os.path.expanduser(f)):
            if "=" in line and not line.lstrip().startswith("#"): k, v = line.strip().split("=", 1); d[k.strip()] = v.strip().strip('"\'')
    for k in ("WECHAT_APPID", "WECHAT_APPSECRET"):
        if os.environ.get(k): d[k] = os.environ[k]
    if not (d.get("WECHAT_APPID") and d.get("WECHAT_APPSECRET")): sys.exit("missing credentials: set WECHAT_APPID + WECHAT_APPSECRET, or WECHAT_ENV_FILE")
    return d
TOKEN_CACHE = os.path.expanduser(os.environ.get("WECHAT_TOKEN_CACHE", "~/.cache/24frames-magazine-layout/wechat_token.json"))
def redact(s):
    s = str(s)
    for k in ("access_token", "secret", "appid"): s = re.sub(k + r'=[^&\s"]+', k + "=***", s, flags=re.I)
    return s
def token():
    T = TOKEN_CACHE; os.makedirs(os.path.dirname(T), exist_ok=True)
    if os.path.exists(T):
        t = json.load(open(T))
        if t.get("expires_at", 0) > time.time() + 300: return t["access_token"]
    e = _env()
    r = requests.get(f"{API}/token", params={"grant_type": "client_credential", "appid": e["WECHAT_APPID"], "secret": e["WECHAT_APPSECRET"]}, timeout=30).json()
    if "access_token" not in r: sys.exit(f'token error: errcode={r.get("errcode")} errmsg={redact(r.get("errmsg"))}')
    old = os.umask(0o077); json.dump({"access_token": r["access_token"], "expires_at": time.time() + r["expires_in"]}, open(T, "w")); os.umask(old); os.chmod(T, 0o600)
    print("[token] fetched (cached, not printed)"); return r["access_token"]
def call(method, path, **kw):
    if any(f in path for f in S["forbidden_endpoints"]) or path not in S["allowed_endpoints"]: raise SystemExit(f"BLOCKED endpoint {path} (kit.json safety)")
    params = kw.pop("params", {}); params["access_token"] = token()
    try: r = requests.request(method, f"{API}/{path}", params=params, timeout=120, **kw)
    except requests.RequestException as e: sys.exit("network error: " + redact(e))
    r.encoding = "utf-8"; j = r.json()
    if j.get("errcode") not in (None, 0): sys.exit(f'[ERROR] {path}: errcode={j.get("errcode")} errmsg={redact(j.get("errmsg"))}')
    return j
def jpost(path, obj): return call("POST", path, data=json.dumps(obj, ensure_ascii=False).encode(), headers={"Content-Type": "application/json; charset=utf-8"})
def sha1(p): return hashlib.sha1(open(p, "rb").read()).hexdigest()
def prepare(p):
    """Return (path_to_upload, note). JPG/PNG ≥1 MB re-encoded (pixels kept); GIF untouched (sent via add_material)."""
    size = os.path.getsize(p); ext = p.rsplit(".", 1)[1].lower()
    if ext == "gif" or size < LIMIT_IMG: return p, ""
    os.makedirs("/tmp/oa_kit_reenc", exist_ok=True); im = Image.open(p); out = f"/tmp/oa_kit_reenc/{os.path.basename(p)}"
    if ext in ("jpg", "jpeg"):
        for q, ss in ((92, 0), (92, 2), (90, 2), (88, 2)):
            b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=q, subsampling=ss, optimize=True, progressive=True)
            if len(b.getvalue()) < LIMIT_IMG: open(out, "wb").write(b.getvalue()); return out, f"re-encoded q{q}"
    else:
        b = io.BytesIO(); im.save(b, "PNG", optimize=True)
        if len(b.getvalue()) >= LIMIT_IMG: b = io.BytesIO(); im.quantize(256).save(b, "PNG", optimize=True)
        if len(b.getvalue()) < LIMIT_IMG: open(out, "wb").write(b.getvalue()); return out, "re-encoded png"
    sys.exit(f"cannot get {p} under 1MB")
