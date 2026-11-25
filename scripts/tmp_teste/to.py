import json, os, re, sys, urllib.request
sys.path.insert(0, "scripts")
from comum import baixar
os.makedirs("sonda", exist_ok=True)
t = baixar("https://www.to.senac.br/_nuxt/D5yJezQ4.js", 60).decode()
for k in ["/courses?", "/search?"]:
    i = t.find(k); print("=====", k); print(t[max(0, i-1500):i+300])
H = {"app": "69d4eae4e9d5b", "Accept": "*/*", "User-Agent": "Mozilla/5.0"}
def get(p):
    r = urllib.request.Request("https://app.lms365.com.br/api/v1" + p, headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=90).read())
for p in ["/courses?page=1", "/courses?per_page=50&page=1", "/search?type=1", "/operationals-gerals"]:
    try:
        d = get(p); s = json.dumps(d, ensure_ascii=False); print("OK", p, len(s), s[:600])
        open("sonda/to_" + re.sub(r"\W+", "_", p) + ".json", "w").write(s)
    except Exception as e: print("ERRO", p, e)
