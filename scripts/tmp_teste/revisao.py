import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import Base
b = Base()
for aba in ("Pesquisas de cursos", "Sites de confiança"):
    rs = b.tabela(aba)
    print(aba, len(rs), "linhas; última linha:", rs[-1]["_linha"])
    for r in rs:
        if r.get("Local") in ("BR-ES", "BR-MG", "BR-MS"):
            print("  ", {k: v for k, v in r.items() if k != "_linha"})
