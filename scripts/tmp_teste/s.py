import json, re, sys
sys.path.insert(0, ".")
from comum import baixar
B = "https://iema.ma.gov.br/?rest_route=/wp/v2/"
def j(q):
    try: return json.loads(baixar(B + q, timeout=40))
    except Exception as e: print("ERRO", q, type(e).__name__, str(e)[:100]); return []
p = j("posts/6574")
if p:
    for l in re.findall(r'href="([^"]+)"', p["content"]["rendered"]):
        if not re.search(r"\.(css|js)(\?|$)", l): print("LINK13:", l)
for q in ["complementar", "vocacional", "manifesta%C3%A7%C3%A3o"]:
    print("\n== posts", q)
    for x in j(f"posts&search={q}&per_page=30&_fields=date,link,title"): print(x["date"][:10], x["title"]["rendered"][:140], x["link"])
    print("== pages", q)
    for x in j(f"pages&search={q}&per_page=30&_fields=modified,link,title"): print(x["modified"][:10], x["title"]["rendered"][:140], x["link"])
print("\n== media recente (PDF)")
for x in j("media&per_page=60&mime_type=application/pdf&_fields=date,source_url,title"):
    print(x["date"][:10], x["title"]["rendered"][:100], x["source_url"])
for u in ["https://web.iema.ma.gov.br/", "https://web.iema.ma.gov.br/vocacional"]:
    try:
        b = baixar(u, timeout=30); print("\nABRIU", u, len(b), re.sub(r"\s+"," ",b.decode("utf-8","replace"))[:600])
    except Exception as e: print("NÃO ABRIU", u, type(e).__name__)
