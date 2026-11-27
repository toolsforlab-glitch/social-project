import json, re, sys
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
B = "https://iema.ma.gov.br/?rest_route=/wp/v2/"
def api(q):
    try:
        return json.loads(baixar(B + q, timeout=60))
    except Exception as e:
        print("ERRO", q, type(e).__name__, str(e)[:120]); return []
print("== 60 posts mais recentes")
for p in api("posts&per_page=60&_fields=date,link,title"):
    print(p["date"][:10], p["title"]["rendered"][:150], p["link"])
for q in ["vocacional", "inscri%C3%A7%C3%B5es", "edital", "curso"]:
    print("\n== pesquisa", q)
    for p in api(f"posts&search={q}&per_page=30&_fields=date,link,title"):
        if p["date"] >= "2026-09":
            print(p["date"][:10], p["title"]["rendered"][:150], p["link"])
print("\n== páginas")
for p in api("pages&per_page=100&_fields=link,title,modified"):
    print(p["modified"][:10], p["title"]["rendered"][:100], p["link"])
