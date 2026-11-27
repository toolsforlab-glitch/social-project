import sys, re, os, urllib.parse, html
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
b = baixar("https://www.mt.senac.br/", timeout=25).decode("utf-8", "replace")
for m in re.finditer(r'href="([^"]+)"[^>]*>\s*([^<]{0,60})', b):
    if re.search(r"gratu|unidade|curso", m.group(0), re.I): print("MT", m.group(1)[:150], "|", m.group(2).strip())
b = baixar("https://www.ms.senac.br/Cursos/Gratuitos-PSG/Consulta-de-Vagas", timeout=25).decode("utf-8", "replace")
open("../sonda/ms.html", "w").write(b)
pdfs = ["https://www.ms.senac.br" + urllib.parse.quote(html.unescape(urllib.parse.unquote(h)), safe="/?=&%")
        for h in re.findall(r'href="(/Portals/0/PSG/[^"]+\.pdf[^"]*)"', b)]
GO = ["https://www.go.senac.br/wp-content/uploads/2026/10/9a-Aditivo_Vagas_Edital-PSG-001_2026_20_10_2026-1.pdf",
      "https://www.go.senac.br/wp-content/uploads/2026/01/Edital_001_2026_SEDUC_e_Unidades.pdf"]
for k, u in enumerate(pdfs + GO):
    try:
        d = baixar(u, timeout=30); open(f"../sonda/d{k:02d}.pdf", "wb").write(d); print("PDF", k, len(d), u[:150])
    except Exception as e: print("ERRO PDF", type(e).__name__, str(e)[:100], u[:140])
