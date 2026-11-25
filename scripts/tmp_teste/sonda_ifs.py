import sys, re, html, urllib.parse
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
P = "https://portal.ifrn.edu.br"
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
import os; os.makedirs("sonda", exist_ok=True)
b = baixar(P + "/documents/31455/EDITAL_N%C2%BA_68_2026-PROEN_RE_IFRN_-_FIC_Integrado_M%C3%A9dio_EJA.pdf", timeout=60)
open("sonda/ed68.txt", "w").write(texto_de_html(b))
a = t(P + "/processos-seletivos/buscar/")
print("FORM:", re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', a, re.S)[:3] and [(n, re.findall(r'value="([^"]*)"[^>]*>([^<]*)', o)[:40]) for n, o in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', a, re.S)])
paginas = {}
for q in ["?q=concomitante", "?q=EJA", "?q=Qualifica%C3%A7%C3%A3o", "?q=65%2F2026", "?q=66%2F2026", "?q=67%2F2026"]:
    try: a = t(P + "/processos-seletivos/buscar/" + q)
    except Exception as e: print("ERRO", q, e); continue
    for h, tit in re.findall(r'<a[^>]+href="([^"]*processo-seletivos-estude-no-ifrn/[^"]+)"[^>]*>(.*?)</a>', a, re.S):
        paginas[urllib.parse.urljoin(P, h)] = limpo(tit)
for p, tit in sorted(paginas.items()): print("  ", tit[:100], p)
