import sys, os, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
B = "https://www.sistemafibra.org.br/senai/editais/gratuidade/"
U = [B+"edital-01-2027-cursos-de-aperfeicoamento-e-qualificacao-de-gratuidade-regimental/download",
     B+"edital-04-2026-cursos-de-aperfeicoamento-e-qualificacao-de-gratuidade-regimental/download",
     "https://www.sistemafibra.org.br/senai/educacao/educacao-profissional/cursos"]
for i, u in enumerate(U):
    try:
        d = baixar(u, timeout=40); ok = d[:5] == b"%PDF-"
        open(f"../sonda/f{i}." + ("pdf" if ok else "html"), "wb").write(d); print("OK" if ok else "NAO-PDF", i, len(d), d[:80])
    except Exception as e:
        print("ERRO", i, type(e).__name__, str(e)[:120])
    time.sleep(3)
