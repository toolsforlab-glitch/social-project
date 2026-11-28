import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import senac_sc as m
links, total = m.cursos_abertos()
alvo = [l for l in links if re.search(r"administracao|cuidador|vendas|auriculo", l)]
print(len(links), alvo)
for u in alvo:
    c = m.ler_curso(u)
    print("##", c["titulo"], "| área:", m._AREA.search(c["requisitos"]), "| req:", c["requisitos"][:200])
    for t in c["turmas"]:
        print("   ", t["codigo"], t["gratis"], t["cidade"], t["ini"], "|", t["texto"][:300])
