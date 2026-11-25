"""Temporário (25/11/2026): o botão dos cursos de EJA de AL e RN abre o site de matrícula (não o PDF da prova)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import Base
base = Base()
alt = [(r["_linha"], {"Página do curso": r["Link"]}) for r in base.tabela("Cursos")
       if r.get("Origem") == "chatgpt" and r.get("Local") in ("BR-AL", "BR-RN") and "EJA" in r.get("Título", "")
       and r.get("Link", "").lower().find(".pdf") < 0]
base.atualizar("Cursos", alt)
print(len(alt), "cursos com o botão para o site de matrícula")
