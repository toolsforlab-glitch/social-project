import json, re, sys, io
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
from pypdf import PdfReader
p = json.loads(baixar("https://iema.ma.gov.br/?rest_route=/wp/v2/posts/6574", timeout=40))
h = p["content"]["rendered"]
print("LINKS:", re.findall(r'href="([^"]+)"', h))
u = "http://iema.ma.gov.br/wp-content/uploads/2026/07/DITAL_No_13_2026_Cursos_FIC_IEMA_Vocacional.pdf"
t = "\n".join(pg.extract_text() or "" for pg in PdfReader(io.BytesIO(baixar(u, timeout=60))).pages)
print(re.sub(r"[ \t]+", " ", t))
