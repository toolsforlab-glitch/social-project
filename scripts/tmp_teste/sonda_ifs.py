import sys, re, html, urllib.parse, os
sys.path.insert(0, "scripts")
from comum import baixar
P = "https://portal.ifrn.edu.br"
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
hs = []
for st in ["10", "50", "3"]:
    for pg in range(1, 4):
        a = t(f"{P}/processos-seletivos/buscar/?tipo=3&subtipo={st}&ano_edital=2026&page={pg}")
        novos = 0
        for h in re.findall(r'href="([^"]*/processo-seletivos-estude-no-ifrn/[^"]+)"', a):
            u = urllib.parse.urljoin(P, h)
            if u not in hs: hs.append(u); novos += 1
        if pg == 1:
            i = a.find("processos seletivos encontrados"); print(st, limpo(a[max(0,i-200):i+40])[-80:])
            print("CARD:", limpo(a[a.find('Ver processo')-1500:a.find('Ver processo')])[-600:])
        if not novos: break
print(len(hs))
for u in hs:
    try: a = t(u)
    except Exception as e: print("ERRO", u, e); continue
    m = re.search(r'(?s)<main.*?</main>', a); x = limpo(m.group(0) if m else a)
    pub = re.search(r"Publicada há [^(]*\(em (\d{2}/\d{2}/\d{4})", x)
    ins = re.findall(r"((?:\d{2}/\d{2}(?:/\d{4})?(?: às [\dh:]+)? a |Até |A partir de )?\d{2}/\d{2}(?:/\d{4})?(?: às [\dh:]+)? Inscriç[^ ]*)", x)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", a, re.S)
    print(f"{pub.group(1) if pub else '?':>10} | {ins} | {limpo(h1.group(1)) if h1 else ''} | {u}")
