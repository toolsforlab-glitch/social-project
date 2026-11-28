import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import senac_sc as m
from concurrent.futures import ThreadPoolExecutor
links, total = m.cursos_abertos()
print(len(links), len(set(links)), [l for l in links if "administracao" in l])
with ThreadPoolExecutor(3) as ex:
    lidos = [r for r in ex.map(lambda u: m._seguro(m.ler_curso, u), links) if r]
for c in lidos:
    if "administracao" in c["url"] or not c["turmas"]:
        print(c["url"], len(c["turmas"]), [t["gratis"] for t in c["turmas"]], c["titulo"])
