import re, sys, io, urllib.parse
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
from pypdf import PdfReader
P = "https://selecao.ifro.edu.br/extensao-jiparana/2102-edital-n-52-2026-selecao-de-estudantes-curso-de-libras-basico-i-2027-1"
b = baixar(P, timeout=30); h = b.decode("utf-8", "replace")
t = texto_de_html(b); i = t.find("Edital nº 52")
print("PÁGINA:", t[max(0,i-200):i+2500])
links = [urllib.parse.urljoin(P, l) for l in re.findall(r'href="([^"]+)"', h) if re.search(r"\.pdf|download|arquivo|attach|forms|docs\.google|suap", l, re.I)]
print("LINKS:", list(dict.fromkeys(links)))
for u in list(dict.fromkeys(links))[:3]:
    try:
        r = PdfReader(io.BytesIO(baixar(u.replace(" ", "%20"), timeout=30)))
        print(f"\n--- {u}\n", re.sub(r"[ \t]+", " ", "\n".join(p.extract_text() or "" for p in r.pages))[:9000])
    except Exception as e:
        print("ERRO", u, type(e).__name__, str(e)[:80])
