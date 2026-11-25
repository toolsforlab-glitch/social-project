import re, json, sys, os
sys.path.insert(0, "scripts")
from comum import baixar
os.makedirs("sonda", exist_ok=True)
raw = baixar("https://www.to.senac.br/", 60).decode("utf-8", "replace")
d = json.loads(re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', raw, re.S).group(1))
def res(i, dep=0):
    if dep > 8: return "…"
    v = d[i] if isinstance(i, int) else i
    if isinstance(v, dict): return {k: res(x, dep+1) for k, x in v.items()}
    if isinstance(v, list):
        if v and isinstance(v[0], str) and v[0] in ("Reactive","ShallowReactive","Ref","ShallowRef"): return res(v[1], dep)
        return [res(x, dep+1) for x in v]
    return v
pags = []
for i, v in enumerate(d):
    if isinstance(v, dict) and "slug" in v and "type" in v and "name" in v:
        r = res(i, 6)
        pags.append({k: r.get(k) for k in ("id","name","slug","type")})
json.dump(pags, open("sonda/paginas.json","w"), ensure_ascii=False, indent=0)
for p in pags:
    if p.get("type") == 4: print("TIPO4", p)
for path in ["/cursos/abertos", "/Search"]:
    try:
        b = baixar("https://www.to.senac.br" + path, 60); open("sonda/to_" + path.strip("/").replace("/","_") + ".html","wb").write(b); print("OK", path, len(b))
    except Exception as e: print("ERRO", path, e)
