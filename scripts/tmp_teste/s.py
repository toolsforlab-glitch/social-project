import sys, os, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://seletivo.ifmt.edu.br/edital/arquivos/6292/", "https://ifmt.edu.br/estude-no-ifmt/sobre/",
     "https://sme.goiania.go.gov.br/site/index.php/institucional/ultimas-noticias/3320-prefeitura-de-goiania-divulga-cronograma-de-matriculas-para-o-ano-letivo-de-2027",
     "https://selecao.ifms.edu.br/perguntas", "https://www.mt.senac.br/Noticias", "https://www.ifb.edu.br/samambaia/49122-curso-tecnico-em-edificacoes-eja-ept-2027"]
for i, u in enumerate(U):
    try:
        d = baixar(u, timeout=30); ok = d[:5] == b"%PDF-"
        open(f"../sonda/g{i}." + ("pdf" if ok else "html"), "wb").write(d); print("OK", "PDF" if ok else "HTML", i, len(d), u[:100])
    except Exception as e:
        print("ERRO", i, type(e).__name__, str(e)[:100], u[:80])
    time.sleep(4)
