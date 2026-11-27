import json, re, sys, io
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
from pypdf import PdfReader
B = "https://iema.ma.gov.br/?rest_route=/wp/v2/posts/"
for pid in (6681, 6574):
    try:
        p = json.loads(baixar(B + str(pid), timeout=40))
    except Exception as e:
        print("ERRO", pid, e); continue
    h = p["content"]["rendered"]
    print(f"\n######## {pid} {p['title']['rendered'][:140]}")
    pdfs = list(dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', h, re.I)))
    print("PDFs:", pdfs)
    for u in pdfs[:1]:
        try:
            t = "\n".join(pg.extract_text() or "" for pg in PdfReader(io.BytesIO(baixar(u.replace(" ", "%20"), timeout=60))).pages)
            t = re.sub(r"[ \t]+", " ", t)
            for m in re.finditer(r"(?im)^.*(\d{1,2}/\d{1,2}/20\d\d|\d{1,2} de \w+ de 20\d\d).*$", t):
                print("  DATA:", m.group(0)[:200])
            for m in re.finditer(r"(?i)[^.\n]{0,120}(sorteio|ordem de inscri|an[áa]lise|prova|entrevista|classifica[çc][ãa]o)[^.\n]{0,120}", t):
                print("  SEL:", m.group(0)[:260])
        except Exception as e:
            print("ERRO PDF", u, type(e).__name__, str(e)[:100])
