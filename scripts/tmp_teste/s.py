import sys, re, os, subprocess, tempfile, urllib.parse, html
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
for i, u in enumerate(["https://www.mt.senac.br/psg/partials/vagas.php", "https://www.mt.senac.br/psg/partials/inscricao.php",
                       "https://www.mt.senac.br/psg/partials/programa.php", "https://www.mt.senac.br/psg/partials/home.php"]):
    try:
        b = baixar(u, timeout=25).decode("utf-8", "replace"); open(f"../sonda/m{i}.html", "w").write(b); print("OK", len(b), u)
    except Exception as e: print("ERRO", type(e).__name__, str(e)[:120], u)
b = open("../sonda/q3.html").read() if os.path.exists("../sonda/q3.html") else baixar("https://www.ms.senac.br/Cursos/Gratuitos-PSG/Consulta-de-Vagas", timeout=25).decode()
pdfs = []
for h in re.findall(r'href="(/Portals/0/PSG/[^"]+\.pdf[^"]*)"', b):
    pdfs.append("https://www.ms.senac.br" + urllib.parse.quote(html.unescape(urllib.parse.unquote(h)), safe="/?=&%"))
GO = ["https://www.go.senac.br/wp-content/uploads/2026/10/9a-Aditivo_Vagas_Edital-PSG-001_2026_20_10_2026-1.pdf",
      "https://www.go.senac.br/wp-content/uploads/2026/01/Edital_001_2026_SEDUC_e_Unidades.pdf"]
for k, u in enumerate(pdfs[:6] + pdfs[-3:] + GO):
    try:
        d = baixar(u, timeout=30)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(d); f.flush()
            t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        open(f"../sonda/pdf{k}.txt", "w").write(u + "\n" + t)
        print("PDF", k, len(d), len(t), u[:140])
    except Exception as e: print("ERRO PDF", type(e).__name__, str(e)[:100], u[:140])
