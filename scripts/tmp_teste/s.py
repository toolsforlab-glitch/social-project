import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def t(u, n=40): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
testes = {
 "idep_media": "https://rondonia.ro.gov.br/wp-json/wp/v2/media?search=IDEP-ETEC&per_page=20&_fields=date,source_url,title",
 "idep_media2": "https://rondonia.ro.gov.br/wp-json/wp/v2/media?search=Edital%20IDEP&per_page=20&_fields=date,source_url",
 "idep_posts": "https://rondonia.ro.gov.br/wp-json/wp/v2/posts?search=Idep%20cursos&per_page=10&_fields=date,link,title",
 "idep_pag": "https://rondonia.ro.gov.br/idep/",
 "pi_posts": "https://www.pi.gov.br/wp-json/wp/v2/posts?search=Qualifica%20Turismo&per_page=10&_fields=date,link,title",
 "pi_media": "https://www.pi.gov.br/wp-json/wp/v2/media?search=Qualifica%20Turismo&per_page=10&_fields=date,source_url",
 "escolegis": "https://al.rr.leg.br/escolegis/",
 "escolegis2": "https://www.al.rr.leg.br/escolegis/",
 "alerr_posts": "https://al.rr.leg.br/wp-json/wp/v2/posts?search=Escolegis%20cursos&per_page=10&_fields=date,link,title",
}
for k, u in testes.items():
    try:
        a = t(u)
        if a.lstrip().startswith("["):
            for x in json.loads(a)[:12]:
                print(k, "|", x.get("date","")[:10], "|", (x.get("title") or {}).get("rendered","")[:90] if isinstance(x.get("title"), dict) else "", "|", x.get("link") or x.get("source_url"))
        else:
            print(k, "OK", len(a), "|", limpo(a)[:200])
            for h, tx in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', a, re.S):
                tx = limpo(tx)
                if re.search(r"edital|curso|inscri|sele", tx, re.I) and len(tx) > 8: print("   ", tx[:100], h[:150])
    except Exception as e:
        print(k, "ERRO", type(e).__name__, str(e)[:150])
