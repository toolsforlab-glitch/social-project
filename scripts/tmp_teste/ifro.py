import re, sys
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
for u in ["https://selecao.ifro.edu.br/component/phocadownload/category/2561-edital-n-128-2026-selecao-de-estudantes-curso-de-formacao-continuada-em-corte-e-costura-modelagem?download=27433:edital-n-128-2026-selecao-de-estudantes-curso-de-formacao-continuada-em-corte-e-costura-modelagem",
          "https://selecao.ifro.edu.br/component/phocadownload/category/2562-edital-n-129-2026-selecao-de-estudantes-curso-pratico-oficina-de-sabonete-artesanal?download=27434:edital-n-129-2026-selecao-de-estudantes-curso-pratico-oficina-de-sabonete-artesanal"]:
    try:
        b = baixar(u, 60); print("=====", len(b), b[:5])
        x = texto_de_html(b)
        open("sonda/" + u.split("download=")[1][:20] + ".txt", "w").write(x)
        print(x[:6000])
    except Exception as e: print("ERRO", e)
