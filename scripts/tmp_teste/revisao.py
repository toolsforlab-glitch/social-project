"""Temporário (27/11/2026): revisão T15 — detalhe de alguns cursos (só leitura)."""
import sys
sys.path.insert(0, ".")
from base import Base
IDS = "C-c15eceb5 C-debe292b C-16213969 C-ac9029b1 C-2068c698 C-1c54d19f C-50ce7a69 C-85b562ac C-9201cd18 C-45476d65 C-c9e9a86c C-f3ab9761 C-f87d83a8 C-cc5db6c6 C-bbd64b5d C-ac2c8a94 C-5ace06ed C-3c0037bb C-9189fc08 C-3faa52dd C-cf77f502 C-c17ca7cd C-66dce181 C-6a66b244 C-f7e7b708 C-79321995".split()
C = Base().tabela("Cursos")
for i in IDS:
    for k, r in enumerate(C):
        if r.get("ID") != i: continue
        print(f"### {i} (linha {k+2}) | {r.get('Estado')} | {r.get('Título')} | {r.get('Entidade')} | {r.get('Modalidade')} | {r.get('Local')} | {r.get('Cidade')}")
        for c in ["Link", "Situação das inscrições", "Inscrições até", "Origem", "Primeiro visto", "Última verificação", "Campos comprovados", "Verificar automaticamente"]:
            print(f"   {c}: {r.get(c)}")
        print("   Evidência:", (r.get("Evidência") or "")[:500])
        print("   Notas:", (r.get("Notas") or "")[-400:])
        print("   Nota da verificação:", (r.get("Nota da verificação") or "")[:300])
gnr = [r for r in C if "gorecife" in (r.get("Link") or "") and r.get("Estado") == "Publicado"]
for r in gnr: print("GORECIFE", r.get("ID"), r.get("Título"), r.get("Situação das inscrições"), r.get("Inscrições até"), r.get("Cidade"))
