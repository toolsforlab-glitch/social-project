"""Temporário (25/11/2026): requisitos dos cursos do Ifap com as frases exatas do edital (conferidas antes por código)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import Base
TEXTO = ("Ter idade igual ou superior a 18 anos ATÉ A DATA DA MATRÍCULA; Ter concluído o Ensino Fundamental, sem "
         "dependências, ATÉ A DATA DA MATRÍCULA; Não possuir o Ensino Médio")
base = Base()
alt = [(r["_linha"], {"Requisitos": TEXTO}) for r in base.tabela("Cursos")
       if r.get("Entidade") == "Instituto Federal do Amapá (Ifap)" and r.get("Origem") == "edital"]
base.atualizar("Cursos", alt)
print(len(alt), "cursos do Ifap com os requisitos do edital")
