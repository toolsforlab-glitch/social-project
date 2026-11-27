import re, sys, io, urllib.parse
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
from pypdf import PdfReader
def pag(u, n=2500, filtro=None):
    try:
        b = baixar(u, timeout=25)
    except Exception as e:
        print(f"\n## {u} NÃO ABRIU {type(e).__name__} {str(e)[:80]}"); return None
    if b[:4] == b"%PDF":
        t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
    else:
        t = texto_de_html(b)
    t = re.sub(r"\s+", " ", t)
    print(f"\n## {u} ({len(t)} chars)")
    if filtro:
        for m in re.finditer(filtro, t, re.I): print("  …", t[max(0, m.start()-200):m.end()+300])
    else:
        print(t[:n])
    return b
b = pag("https://rondoniasocial.ro.gov.br/vencer/", 3000)
pag("https://rondonia.ro.gov.br/wp-content/uploads/2026/07/SEI_74690921_Edital_6.pdf", 0, r"gratuit|ordem cronol|inscri[çc][õo]es|pizzaiolo|reabertura|Porto Velho")
for u in ["https://www.fadex.org.br/", "https://fadex.org.br/editais", "https://www.fadex.org.br/editais/"]:
    b = pag(u, 0, r"acredita|qualifica|primeiro passo")
    if b:
        h = b.decode("utf-8", "replace")
        print("  LINKS:", [l for l in re.findall(r'href="([^"]+)"', h) if re.search(r"acredita|qualific|edital", l, re.I)][:20])
