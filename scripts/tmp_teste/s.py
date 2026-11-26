import sys, re, json
sys.path.insert(0, ".")
from comum import baixar
import noticias_oficiais as n
for f in n.FONTES[-2:]:
    a = n.noticias_da_api(f, "2026-11-26"); inc = re.compile(f["incluir"], re.I)
    print("##", f["nome"], len(a))
    for l, t in a.items(): print("  ", "INCLUI" if inc.search(t) and not n.EXCLUIR.search(t) else "-", t[:100])
for site in ["https://boavista.rr.gov.br", "https://www.portovelho.ro.gov.br", "https://www.palmas.to.gov.br", "https://www.aracaju.se.gov.br",
             "https://teresina.pi.gov.br", "https://www.se.gov.br", "https://www.to.gov.br", "https://portal.rr.gov.br", "https://www.teresina.pi.gov.br"]:
    for path in ["/wp-json/wp/v2/posts?search=cursos%20gratuitos&per_page=5&_fields=date,link,title", "/"]:
        try:
            b = baixar(site + path, timeout=25).decode("utf-8-sig", "replace")
            if b.lstrip().startswith("["):
                print("WP", site, [ (x["date"][:10], re.sub(r"<[^>]+>","",x["title"]["rendered"])[:70]) for x in json.loads(b)[:5]]); break
            else:
                print("HTML", site + path, len(b), re.findall(r'href="([^"]*(?:noticia|news)[^"]*)"', b)[:3])
        except Exception as e:
            print("ERRO", site + path, type(e).__name__, str(e)[:100])
