import json, os, re, urllib.request, html
os.makedirs("sonda", exist_ok=True)
H = {"app": "69d4eae4e9d5b", "Accept": "*/*", "User-Agent": "Mozilla/5.0"}
def get(p):
    r = urllib.request.Request("https://app.lms365.com.br/api/v1" + p, headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=90).read())
for p in ["/pages/psg-programa-senac-de-gratuidade/contents", "/pages/50/contents?page=1&type=2"]:
    try:
        s = json.dumps(get(p), ensure_ascii=False)
        txt = html.unescape(re.sub(r"\\[nrt]", " ", re.sub(r"<[^>]+>", " ", s)))
        print("OK", p, len(s))
        for k in ["gratuit", "custo zero", "salário", "sem custo"]:
            for m in list(re.finditer(k, txt, re.I))[:3]: print("  ", k, "::", re.sub(r"\s+", " ", txt[max(0, m.start()-250):m.start()+200]))
    except Exception as e: print("ERRO", p, e)
