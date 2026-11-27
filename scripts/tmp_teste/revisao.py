"""Temporário (27/11/2026): revisão T15 antes do Sudeste — só lê, não escreve."""
import sys, re, unicodedata, collections
sys.path.insert(0, ".")
from base import Base, carregar_config, curso_no_site
from turmas import hoje_ceara
hoje = hoje_ceara()
base = Base(); cfg = carregar_config(base) or {}
cfg = cfg if isinstance(cfg, dict) else {}
C = base.tabela("Cursos")
def n(s): return re.sub(r"\W+", " ", unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()).strip()
print("TOTAL", len(C), collections.Counter(r.get("Estado", "") for r in C))
no_site = [r for r in C if curso_no_site(r, cfg)]
print("NO SITE", len(no_site), collections.Counter(r.get("Local", "") for r in no_site).most_common())
def L(r): return f"{r.get('ID')} | {r.get('Estado')} | {(r.get('Título') or '')[:70]} | {r.get('Local')} | até {r.get('Inscrições até')} | {r.get('Situação das inscrições')} | {(r.get('Link') or '')[:90]}"
print("\n== REVER/NOVO")
for r in C:
    if r.get("Estado") in ("Rever", "Novo"): print(" ", (r.get("Entidade") or "")[:40], "||", L(r))
print("\n== MUDANÇA A REVER")
for r in C:
    if str(r.get("Mudança a rever", "")).upper() == "TRUE": print(" ", (r.get("Entidade") or "")[:40], "||", L(r), "||", (r.get("Nota da verificação") or "")[:200])
print("\n== IDS REPETIDOS")
for k, v in collections.Counter(r.get("ID") for r in C).items():
    if v > 1 and k: print(" ", k, v)
print("\n== REPETIDOS (título+entidade normalizados, entre os do site)")
g = collections.defaultdict(list)
for r in no_site: g[(n(r.get("Título")), n(r.get("Entidade")), n(r.get("Cidade")))].append(r)
for k, v in g.items():
    if len(v) > 1:
        for r in v: print(" ", L(r))
        print("  --")
print("\n== MESMO LINK, VÁRIOS CURSOS NO SITE (só links que não sejam listas)")
g = collections.defaultdict(list)
for r in no_site: g[(r.get("Link") or "").strip()].append(r)
for k, v in g.items():
    if len(v) > 1 and k: print(f"  {len(v)} × {k[:110]}  ex.: {(v[0].get('Título') or '')[:50]} / {(v[1].get('Título') or '')[:50]}")
print("\n== NO SITE COM PRAZO JÁ PASSADO")
for r in no_site:
    d = (r.get("Inscrições até") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d < hoje: print(" ", L(r))
print("\n== NO SITE 'Por abrir' com data de abertura passada")
for r in no_site:
    if r.get("Situação das inscrições") == "Por abrir" and (r.get("Inscrições abrem em") or "9")[:10] <= hoje: print(" ", L(r), r.get("Inscrições abrem em"))
print("\n== NO SITE SEM PROVA DE GRATUIDADE (Evidência sem 'gratuit')")
for r in no_site:
    if "gratuit" not in (r.get("Evidência") or "").lower() and "Revisto por pessoa" not in (r.get("Notas") or "") : print(" ", L(r))
print("\n== O QUE FALTA CONFIRMAR (no site), por entidade")
g = collections.defaultdict(list)
for r in no_site:
    f = (r.get("O que falta confirmar") or "").strip()
    if f: g[(r.get("Entidade") or "")[:60]].append((r.get("ID"), f[:220]))
for k, v in sorted(g.items(), key=lambda x: -len(x[1])):
    print(f"  [{len(v)}] {k}")
    vistos = set()
    for i, f in v:
        if f in vistos: continue
        vistos.add(f); print(f"     {i}: {f}")
