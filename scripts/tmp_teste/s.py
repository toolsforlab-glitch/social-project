import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://iema.ma.gov.br/?rest_route=/wp/v2/posts&per_page=15&_fields=date,link,title",
          "https://iema.ma.gov.br/?rest_route=/wp/v2/posts&search=vocacional&per_page=15&_fields=date,link,title",
          "https://iema.ma.gov.br/?rest_route=/wp/v2/posts&search=inscri%C3%A7%C3%B5es&per_page=15&_fields=date,link,title"]:
    try:
        d = json.loads(baixar(u, timeout=40).decode("utf-8-sig", "replace"))
        print("#####", u); [print("  ", p["date"], limpo(p["title"]["rendered"])[:110], p["link"]) for p in d]
    except Exception as e: print("ERRO", u, type(e).__name__, str(e)[:100])
for u in ["http://iema.ma.gov.br/?page_id=17", "https://vocacional.ibutumy.iema.ma.gov.br/"]:
    try:
        b = baixar(u, timeout=40).decode("utf-8", "replace")
        print("#####", u, len(b)); print(limpo(b)[:1500])
        print("SCRIPTS:", re.findall(r'<script[^>]+src="([^"]+)"', b)[:8])
        for h, t in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', b, re.S)[:400]:
            if re.search(r"edital|vocacion|curso|inscri|oficina|fic|2026", h + limpo(t), re.I): print("  ", limpo(t)[:90], "|", h)
    except Exception as e: print("ERRO", u, type(e).__name__, str(e)[:100])
