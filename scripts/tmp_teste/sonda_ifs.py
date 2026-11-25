import sys, re, html, urllib.parse, os
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
P = "https://portal.ifrn.edu.br"
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
os.makedirs("sonda", exist_ok=True)
vistos = []
for st in ["10", "56", "3", "50"]:
    a = t(f"{P}/processos-seletivos/buscar/?tipo=3&subtipo={st}&ano_edital=2026")
    blocos = re.split(r'(?=<div class="[^"]*card)', a)
    hs = []
    for h in re.findall(r'href="([^"]*/processo-seletivos-estude-no-ifrn/[^"]+)"', a):
        u = urllib.parse.urljoin(P, h)
        if u not in hs: hs.append(u)
    print(f"## subtipo {st}: {len(hs)}")
    m = re.search(r'(?s)Processos seletivos</h1>(.*)', a)
    print("   ", limpo(m.group(1) if m else a)[:1500])
    for u in hs[:12]: print("   ", u); vistos.append(u)
for u in vistos:
    if not re.search(r"concomitante|eja|fic|qualifica|extens", u, re.I): continue
    a = t(u); m = re.search(r'(?s)<main.*?</main>', a); txt = limpo(m.group(0) if m else a)
    if "Inscrições Período aberto" not in txt and "Inscrição Período aberto" not in txt: continue
    print("#####", u); print("   ", txt[:1500])
    docs = [urllib.parse.urljoin(P, h) for h in re.findall(r'href="([^"]*/documents/[^"]+)"', a)]
    print("   docs:", docs[:6])
    if docs:
        b = baixar(docs[-1], timeout=60)
        if b[:4] == b"%PDF":
            nome = re.sub(r"\W+", "_", u.rstrip("/").split("/")[-1])[:60]
            open(f"sonda/{nome}.txt", "w").write(texto_de_html(b))
