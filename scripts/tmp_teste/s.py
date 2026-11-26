import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
b = baixar("https://iema.ma.gov.br/", timeout=40).decode("utf-8", "replace")
print("GERADOR:", re.findall(r'<meta name="generator"[^>]+>', b), "wp-content" in b, "wp-json" in b)
links = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', b, re.S)
for h, t in links:
    if re.search(r"edita|vocacion|fic|curso|inscri|noticia|seletiv|oficina", h + limpo(t), re.I): print("  ", limpo(t)[:70], "|", h)
for u in ["https://iema.ma.gov.br/wp-json/wp/v2/posts?per_page=10&_fields=date,link,title",
          "https://iema.ma.gov.br/wp-json/wp/v2/posts?search=vocacional&per_page=10&_fields=date,link,title"]:
    try:
        d = json.loads(baixar(u, timeout=40).decode("utf-8-sig", "replace"))
        print("#####", u); [print("  ", p["date"], limpo(p["title"]["rendered"])[:110], p["link"]) for p in d]
    except Exception as e: print("ERRO", u, type(e).__name__, str(e)[:100])
