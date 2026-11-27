import sys, collections
sys.path.insert(0, ".")
from base import Base
b = Base(); L = b.tabela("Cursos")
def c(r, k): return (r.get(k) or "").strip()
print("ESTADOS:", dict(collections.Counter(c(r, "Estado") for r in L)))
print("\n== Rever / Novo")
for r in L:
    if c(r, "Estado") in ("Rever", "Novo"):
        print(f"L{r['_linha']} {c(r,'Estado')} {c(r,'ID')} | {c(r,'Título')[:70]} | {c(r,'Entidade')[:45]} | sit={c(r,'Situação das inscrições')} até={c(r,'Inscrições até')} | falta: {c(r,'O que falta confirmar')[:160]} | nota: {c(r,'Nota da verificação')[:120]}")
print("\n== Publicado com Mudança a rever = TRUE")
for r in L:
    if c(r, "Estado") == "Publicado" and c(r, "Mudança a rever").upper() == "TRUE":
        print(f"L{r['_linha']} {c(r,'ID')} | {c(r,'Título')[:70]} | {c(r,'Entidade')[:40]} | {c(r,'Nota da verificação')[:160]}")
print("\n== Publicado com 'O que falta confirmar' (por entidade)")
cnt = collections.Counter(); ex = {}
for r in L:
    f = c(r, "O que falta confirmar")
    if c(r, "Estado") == "Publicado" and f:
        k = c(r, "Entidade")[:50]; cnt[k] += 1; ex.setdefault(k, f[:150])
for k, n in cnt.most_common(40):
    print(f"{n:4} {k} | ex.: {ex[k]}")
print("\n== Publicado com Situação 'Por confirmar' ou vazia (não on-line)")
n = 0
for r in L:
    if c(r, "Estado") == "Publicado" and c(r, "Situação das inscrições") in ("", "Por confirmar") and c(r, "Modalidade") != "online":
        n += 1
        if n <= 30: print(f"L{r['_linha']} {c(r,'ID')} | {c(r,'Título')[:60]} | {c(r,'Entidade')[:40]} | sit='{c(r,'Situação das inscrições')}' | até={c(r,'Inscrições até')}")
print("total:", n)
print("\n== Publicado presencial com 'Inscrições até' no passado mas Situação Aberto")
import datetime; h = datetime.date.today().isoformat()
for r in L:
    if c(r, "Estado") == "Publicado" and c(r, "Situação das inscrições") == "Aberto" and c(r, "Inscrições até") and c(r, "Inscrições até") < h:
        print(f"L{r['_linha']} {c(r,'ID')} | {c(r,'Título')[:60]} | até={c(r,'Inscrições até')}")
