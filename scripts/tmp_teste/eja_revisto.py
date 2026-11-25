"""Temporário (25/11/2026): «Revisto por pessoa» com a data; a decisão vai para as Notas."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import Base
base = Base()
alt = [(r["_linha"], {"Revisto por pessoa": "2026-11-25",
                      "Notas": "Decisão do responsável (25/11/2026): EJA da rede pública estadual é gratuita."})
       for r in base.tabela("Cursos") if (r.get("Revisto por pessoa") or "").startswith("Decisão do responsável")]
base.atualizar("Cursos", alt)
print(len(alt), "cursos corrigidos")
