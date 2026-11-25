"""Temporário (25/11/2026): publica os 9 cursos do PS Proeja 2027.1 do Ifap (frases conferidas por código no edital)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import Base, hoje_iso
base = Base()
alt = [(r["_linha"], {"Estado": "Publicado",
                      "Nota da verificação": (r.get("Nota da verificação") or "") + f" {hoje_iso()}: publicado (todas as frases conferidas por código no edital oficial)."})
       for r in base.tabela("Cursos")
       if r.get("Entidade") == "Instituto Federal do Amapá (Ifap)" and r.get("Origem") == "edital" and r.get("Estado") == "Novo"]
base.atualizar("Cursos", alt)
print(len(alt), "cursos do Ifap publicados")
