import sys
sys.path.insert(0, "scripts")
from comum import baixar
for u in ["https://www.to.senac.br/cursos/psg-programa-senac-de-gratuidade", "https://www.to.senac.br/curso/1743"]:
    try:
        b = baixar(u, 60).decode("utf-8", "replace"); print("OK", u, len(b), "Gratuidade" in b, "Vendedor" in b)
    except Exception as e: print("ERRO", u, e)
