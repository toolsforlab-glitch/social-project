import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://www.ce.gov.br/wp-json/wp/v2/posts?slug=cagece-capacita-matriculas-ocorrem-dia-28-de-novembro&_fields=date,link,title,content",
          "https://iema.ma.gov.br/?rest_route=/wp/v2/posts/6851&_fields=date,link,title,content"]:
    try:
        d = json.loads(baixar(u, timeout=40).decode("utf-8-sig", "replace"))
        d = d[0] if isinstance(d, list) else d
        c = d["content"]["rendered"]
        print("#####", d["link"], d["date"]); print(limpo(c)[:5000])
        print("LINKS:", re.findall(r'href="([^"]+)"', c)[:15])
    except Exception as e: print("ERRO", u, type(e).__name__, str(e)[:100])
