import json, random, urllib.request

BASE = "http://localhost:8000"
email = f"smoke-{random.randint(1000,99999)}@test.com"

def post(path, body, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

s, reg = post("/auth/register", {"email": email, "password": "Sup3rSecret99", "full_name": "Smoke"})
print("register:", s, reg)

s, login = post("/auth/login", {"email": email, "password": "Sup3rSecret99"})
tok = login.get("access_token")
print("login:", s, "token OK" if tok else login)

s, me = post("/x", {}) if False else (200, {})
import urllib.request as u
req = u.Request(BASE + "/auth/me", headers={"Authorization": f"Bearer {tok}"})
me = json.loads(u.urlopen(req).read())
print("me:", me.get("email"), "| plan:", me.get("plan_code"), "| quota:", me.get("quota_used"), "/", me.get("quota_limit"))

s, ask = post("/ask", {"query": "What is lung cancer screening?", "mode": "patient"}, token=tok)
print("ask:", s, "| answer chars:", len(ask.get("answer", "")), "| sources:", ask.get("sources"))
print("triage:", ask.get("triage", {}).get("level"))
print("answer preview:", ask.get("answer", "")[:200])
