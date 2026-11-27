import json, re, sys, io
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
B = "https://iema.ma.gov.br/?rest_route=/wp/v2/posts/"
for pid in (6851, 6681, 6574):
    try:
        p = json.loads(baixar(B + str(pid), timeout=60))
    except Exception as e:
        print("ERRO", pid, e); continue
    h = p["content"]["rendered"]
    print(f"\n######## {pid} {p['title']['rendered'][:120]}\n", texto_de_html(h.encode())[:1500])
    pdfs = list(dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', h, re.I)))
    print("PDFs:", pdfs)
    for u in pdfs[:2]:
        try:
            from pypdf import PdfReader
            t = "\n".join(pg.extract_text() or "" for pg in PdfReader(io.BytesIO(baixar(u.replace(" ", "%20"), timeout=90))).pages)
            t = re.sub(r"[ \t]+", " ", t)
            print(f"--- PDF {u} ({len(t)} chars)")
            for k in re.finditer(r"(?i)(inscri[çc][õo]es?|sorteio|an[áa]lise|prova|hist[óo]rico|gratuit|taxa|cronograma|ordem de|classifica)", t):
                pass
            print(t[:6000])
        except Exception as e:
            print("ERRO PDF", u, type(e).__name__, str(e)[:100])
