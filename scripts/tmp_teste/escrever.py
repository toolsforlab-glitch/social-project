"""Temporário (28/11/2026): contagem das turmas/cursos dos cartões gerais (regra M12, pedido do responsável).
Números contados pelo Claude nas fontes a 27/11/2026 (Brasília): Firjan pelo PDF lido por código no GitHub;
os outros no navegador."""
import sys
sys.path.insert(0, ".")
from base import Base, carregar_config
base = Base(); carregar_config(base)
Q = "2026-11-27"
C = {"C-b454c3ac": (456, "turmas", "edital da Firjan lido por código: 456 turmas (somam as 11.260 vagas), início entre janeiro e abril de 2027"),
     "C-6cbf89e6": (260, "turmas", "lista do SENAI DF no Chrome: 80 cursos (44 de qualificação, 36 de aperfeiçoamento), 260 ofertas por escola e turno"),
     "C-f87d83a8": (4, "cursos", "página do IF Baiano: Informática, Multimeios Didáticos, Secretaria Escolar e Vendas (230 vagas)"),
     "C-cc5db6c6": (5, "cursos", "página do IF Baiano: Informática, Multimeios Didáticos, Redes de Computadores, Secretaria Escolar e Vendas (380 vagas)"),
     "C-bbd64b5d": (4, "cursos", "página do IF Baiano: Informática, Redes de Computadores, Secretaria Escolar e Vendas (160 vagas)"),
     "C-1fba6d23": (8, "cursos", "edital 29/2026 da FADEX: 8 cursos"),
     "C-f928d51a": (6, "cursos (3 cursos em cada um dos 2 locais)", "notícia da Agência Brasília: 3 cursos no Itapoã (79 vagas) e 3 em Sobradinho II (86 vagas)")}
alt = []
for r in base.tabela("Cursos"):
    if r.get("ID") in C:
        n, u, nota = C[r["ID"]]
        alt.append((r["_linha"], {"Turmas abertas (cartão geral)": n, "Turmas contadas em": Q, "O que se contou": u,
                                  "Notas": ((r.get("Notas") or "") + f"\n{Q}: contagem para o mapa (regra M12): {nota}.").strip()}))
base.atualizar("Cursos", alt); base.guardar()
for l, c in alt: print(l, c["Turmas abertas (cartão geral)"], c["O que se contou"])
