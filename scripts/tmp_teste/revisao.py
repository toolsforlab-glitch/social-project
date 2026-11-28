import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import Base
b = Base()
for aba in ("Pesquisas de cursos", "Sites de confiança"):
    rs = b.tabela(aba)
    print(aba, Counter(r.get("Local") for r in rs))
ps = b.tabela("Pesquisas de cursos")
for r in ps:
    if r.get("ID", "").startswith(("br-rn", "rn-")):
        print("  P", r.get("Ativa"), r.get("ID"), "|", r.get("Local"), "|", r.get("O que procurar"), "|", r.get("Notas"))
for r in b.tabela("Sites de confiança"):
    if r.get("Local") == "BR-RN":
        print("  S", r.get("Ativo"), r.get("Domínio"), "|", r.get("Notas"), "|", r.get("Tudo gratuito"), "|", r.get("Inscrição aberta quando a página mostra"))
