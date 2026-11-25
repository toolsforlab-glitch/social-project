import sys, re, html, urllib.parse
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
P = "https://portal.ifrn.edu.br"
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
paginas = set()
for q in ["?tipo=tipo%3A2", "?tipo=tipo%3A2&page=2", "?tipo=3", "?q=EJA", "?q=FIC"]:
    try:
        a = t(P + "/processos-seletivos/buscar/" + q)
    except Exception as e:
        print("ERRO", q, e); continue
    for h in re.findall(r'href="([^"]*processo-seletivos-estude-no-ifrn/[^"]+)"', a):
        paginas.add(urllib.parse.urljoin(P, h))
print("PAGINAS:"); [print("  ", p) for p in sorted(paginas)]
for p in sorted(paginas):
    if not re.search(r"formacao-inicial|fic|eja|qualificacao|proeja", p, re.I): continue
    a = t(p); print("#####", p)
    docs = sorted(set(urllib.parse.urljoin(P, h) for h in re.findall(r'href="([^"]*(?:/documents/|\.pdf)[^"]*)"', a)))
    print("  docs:", docs[:12])
    m = re.search(r'(?s)<main.*?</main>', a); print("  ", limpo(m.group(0) if m else a)[:2200])
    for d in docs[:3]:
        try:
            b = baixar(d, timeout=60)
            if b[:4] != b"%PDF": continue
            tx = texto_de_html(b); print("  ## PDF", d, len(tx)); print("    INÍCIO:", tx[:300])
            for pat in [r".{0,250}sortei.{0,300}", r".{0,200}crit[ée]rio.{0,300}", r".{0,150}\bprova\b.{0,150}", r".{0,120}idade.{0,200}", r".{0,200}(requisito|ter conclu[íi]do).{0,300}", r".{0,150}gratuit.{0,150}", r".{0,150}in[íi]cio das aulas.{0,150}"]:
                for mm in list(re.finditer(pat, tx, re.I))[:2]: print("    ", pat[:14], "→", mm.group(0)[:550])
        except Exception as e: print("  ERRO", d, e)
