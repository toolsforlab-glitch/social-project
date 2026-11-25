import sys, re, json, html
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
def t(u, n=60):
    return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
print("##### IF BAIANO")
posts = json.loads(t("https://ifbaiano.edu.br/portal/wp-json/wp/v2/posts?search=FIC&orderby=date&per_page=12&_fields=link,title,date,content"))
for p in posts[:12]:
    c = p["content"]["rendered"]
    print("==", p["date"][:10], limpo(p["title"]["rendered"]), p["link"])
    print("   links:", [x for x in re.findall(r'href="([^"]+)"', c) if re.search(r"pdf|edital|selecao|inscri|forms|doc", x, re.I)][:6])
    print("   texto:", limpo(c)[:900])
print("##### IFCE")
pg = t("https://ifce.edu.br/")
for u, tit in re.findall(r'data-tab="estude-no-ifce">\s*<a href="([^"]+)" class="card-ps-header">\s*<p class="hat">[^<]*</p>\s*<h3 class="title">([^<]+)</h3>', pg):
    print("==", tit, u)
    if "FIC" in tit or "curso" in tit.lower() and "Técnico" not in tit:
        try:
            a = t(u)
            print("   links:", [x for x in re.findall(r'href="([^"]+)"', a) if re.search(r"\.pdf|edital|anexo|inscri|forms", x, re.I)][:15])
            print("   texto:", limpo(re.sub(r"(?s)<(script|style|nav|header|footer).*?</\1>", " ", a))[:2500])
        except Exception as e: print("   ERRO", e)
print("##### IFRN")
pg = t("https://processoseletivo.ifrn.edu.br/")
for u, tit in re.findall(r"<h3><a href='([^']+)'>([^<]+)</a></h3>", pg)[:40]:
    print("==", tit, u)
for u, tit in re.findall(r"<h3><a href='([^']+)'>([^<]+)</a></h3>", pg):
    if re.search(r"\bFIC\b|Forma[çc][ãa]o Inicial|Qualifica", tit, re.I):
        a = t("https://processoseletivo.ifrn.edu.br" + u if u.startswith("/") else u)
        print("#### FIC", tit); print("   links:", re.findall(r"href=['\"]([^'\"]+\.pdf[^'\"]*)", a)[:10]); print("   ", limpo(a)[:1500]); break
