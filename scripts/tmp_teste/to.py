import json, os, urllib.request, collections
os.makedirs("sonda", exist_ok=True)
H = {"app": "69d4eae4e9d5b", "Accept": "*/*", "User-Agent": "Mozilla/5.0"}
def get(p):
    r = urllib.request.Request("https://app.lms365.com.br/api/v1" + p, headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=90).read())
d = get("/courses?per_page=999999&status=P&page=1")
json.dump(d, open("sonda/to_cursos.json", "w"), ensure_ascii=False)
lista = d.get("data", d) if isinstance(d, dict) else d
print(type(d), (list(d.keys()) if isinstance(d, dict) else ""), len(lista))
if lista:
    c = lista[0]; print(json.dumps(c, ensure_ascii=False)[:2500])
    try:
        x = get(f"/courses/{c['id']}"); json.dump(x, open("sonda/to_curso1.json","w"), ensure_ascii=False); print(json.dumps(x, ensure_ascii=False)[:3000])
    except Exception as e: print("ERRO detalhe", e)
