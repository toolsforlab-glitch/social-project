"""Temporário (25/11/2026): aba Necessidades e coluna Necessidades de Cursos. Apagar depois de correr."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import EJA, Base, numero

base = Base()
nec = base.tabela("Necessidades")
print("Necessidades antes:", [(r["ID"], r.get("Texto no site"), r.get("Ordem"), r.get("Ativa")) for r in nec])
por_id = {r["ID"]: r for r in nec}
alt = []
if "mudar" in por_id:
    alt.append((por_id["mudar"]["_linha"], {"Texto no site": "Desenvolvimento pessoal e no trabalho"}))
if "materias" not in por_id and "escola" in por_id:
    o = numero(por_id["escola"].get("Ordem"), 7)
    for r in nec:
        if numero(r.get("Ordem"), 99) > o and r.get("Ordem"):
            alt.append((r["_linha"], {"Ordem": str(numero(r["Ordem"], 99) + 1)}))
    novo = {k: v for k, v in por_id["escola"].items() if k != "_linha"}
    novo.update({"ID": "materias", "Texto no site": "Estudar matérias da escola", "Ordem": str(o + 1)})
    base.atualizar("Necessidades", alt)
    base.acrescentar("Necessidades", [novo])
else:
    base.atualizar("Necessidades", alt)
print("Necessidades depois:", [(r["ID"], r.get("Texto no site"), r.get("Ordem")) for r in base.tabela("Necessidades")])

mud, fica = [], []
for r in base.tabela("Cursos"):
    ids = [x.strip() for x in (r.get("Necessidades") or "").split(",") if x.strip()]
    if "escola" not in ids:
        continue
    texto = " ".join([r.get("Título", ""), r.get("Título na fonte", ""), r.get("Descrição", "")])
    if EJA.search(texto):
        fica.append(r.get("Título", ""))
        continue
    novos = []
    for x in ids:
        x = "materias" if x == "escola" else x
        if x not in novos:
            novos.append(x)
    mud.append((r["_linha"], {"Necessidades": ", ".join(novos)}))
base.atualizar("Cursos", mud)
print(f"Cursos: {len(mud)} passaram de escola para materias; {len(fica)} ficam em escola (EJA/supletivo):")
for t in fica:
    print("   fica:", t)
