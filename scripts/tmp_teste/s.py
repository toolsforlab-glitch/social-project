import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
q = "cursos%20gratuitos"
for u in ["https://www.ma.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q,
          "https://www.ma.gov.br/noticias", "https://www.saoluis.ma.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q,
          "https://www.saoluis.ma.gov.br/noticias", "https://www.pe.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q,
          "https://www.pe.gov.br/noticias", "https://www2.recife.pe.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q,
          "https://www2.recife.pe.gov.br/noticias", "https://www.recife.pe.gov.br/noticias", "https://iema.ma.gov.br/",
          "https://www.sedepe.pe.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q,
          "https://www.sectet.ma.gov.br/", "https://setres.ma.gov.br/wp-json/wp/v2/posts?search=%s&per_page=5&_fields=date,link,title" % q]:
    try:
        b = baixar(u, timeout=25).decode("utf-8-sig", "replace")
        print("#####", u, len(b))
        if b.lstrip().startswith("["):
            for p in json.loads(b)[:5]: print("  ", p.get("date"), limpo(p["title"]["rendered"])[:100], p.get("link"))
        else:
            t = limpo(b); print("  ", t[:300])
            print("  LINKS:", [limpo(x)[:80] for x in re.findall(r"<a[^>]+>(.*?)</a>", b, re.S) if re.search(r"curso|qualifica|vaga", limpo(x), re.I)][:8])
    except Exception as e:
        print("ERRO", u, type(e).__name__, str(e)[:120])
