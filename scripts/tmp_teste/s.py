import sys, re, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://www.mt.senac.br/psg/assets/js/appPSG.js",
     "https://www.mt.senac.br/psg/partials/consulta-de-vagas.php",
     "https://www.mt.senac.br/psg/partials/como-se-inscrever.php",
     "https://www.ms.senac.br/Cursos/Gratuitos-PSG/Consulta-de-Vagas",
     "https://www.ms.senac.br/Cursos/Gratuitos-PSG/Como-se-inscrever",
     "https://www.ms.senac.br/Cursos/Gratuitos-PSG"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=25).decode("utf-8", "replace")
        open(f"../sonda/q{i}.html", "w").write(b)
        print("OK", len(b), u)
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
