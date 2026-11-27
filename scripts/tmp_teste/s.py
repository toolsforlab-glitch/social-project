import sys, re
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
U = ["https://www.ms.senac.br/", "https://ww3.ms.senac.br/", "https://www.ms.senac.br/cursos-gratuitos",
     "https://ww3.ms.senac.br/Cursos-Gratuitos", "https://www.ms.senac.br/psg",
     "https://www.mt.senac.br/", "https://www.mt.senac.br/cursos-gratuitos", "https://www.mt.senac.br/psg",
     "https://www.go.senac.br/", "https://www.go.senac.br/programa-senac-de-gratuidade"]
import os
os.makedirs("../sonda", exist_ok=True)
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace")
        open(f"../sonda/p{i}.html", "w").write(b)
        t = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S))
        t = re.sub("<[^>]+>", " ", t)
        print("OK", len(b), u, "|", re.sub(r"\s+"," ",t)[:200])
        links = sorted(set(m for m in re.findall(r'href="([^"]+)"', b) if re.search(r"gratu|psg|edital|vaga|curso", m, re.I)))
        for l in links[:40]: print("   ", l[:160])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
