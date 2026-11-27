"""Temporário (27/11/2026): correções da revisão T15 antes do Sudeste."""
import sys
sys.path.insert(0, ".")
from base import Base
from turmas import hoje_ceara
hoje = hoje_ceara()
LDB = "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm"
G37 = f"gratuito (lei, vista no navegador a {hoje}): LDB art. 37, § 1.º, «Os sistemas de ensino assegurarão gratuitamente aos jovens e aos adultos» ({LDB})"
G3 = f"gratuito (lei, vista no navegador a {hoje}): LDB art. 3.º, VI, «gratuidade do ensino público em estabelecimentos oficiais» ({LDB})"
base = Base(); C = base.tabela("Cursos")
pos = {}
for k, r in enumerate(C):
    pos.setdefault(r.get("ID"), (k + 2, r))
def nota(r, txt): return ((r.get("Notas") or "") + f" {hoje} (Claude, revisão T15): {txt}").strip()
alt = []
for i, ref in [("C-c15eceb5", "C-f7e7b708"), ("C-16213969", "C-f7e7b708"), ("C-ac9029b1", "C-2068c698")]:
    n, r = pos[i]
    if r.get("Estado") == "Publicado":
        alt.append((n, {"Estado": "Oculto", "Notas": nota(r, f"Oculto — repetido de {ref} (mesmo curso na API da EV.G).")}))
for i, txt in [("C-45476d65", "Expirado — as inscrições foram só a 23 e 24/11/2026."),
               ("C-c9e9a86c", "Expirado — o prazo da notícia era 24/11/2026 e a página oficial nunca foi confirmada.")]:
    n, r = pos[i]
    alt.append((n, {"Estado": "Expirado", "Situação das inscrições": "Encerrado", "Notas": nota(r, txt)}))
for i, g in [("C-ac2c8a94", G37), ("C-5ace06ed", G37), ("C-3c0037bb", G37), ("C-9189fc08", G37), ("C-3faa52dd", G37),
             ("C-f87d83a8", G3), ("C-cc5db6c6", G3), ("C-bbd64b5d", G3)]:
    n, r = pos[i]
    ev = r.get("Evidência") or ""
    if "LDB" in ev: continue
    campos = [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()]
    if "gratuito" not in campos: campos.append("gratuito")
    alt.append((n, {"Evidência": (g + " | " + ev)[:1800], "Campos comprovados": ", ".join(campos),
                    "Notas": nota(r, "frase de gratuidade da LDB acrescentada (regra F6).")}))
for n, c in alt: print("linha", n, list(c.keys()))
base.atualizar("Cursos", alt); base.guardar(); print("feito:", len(alt))
