"""Revisão T15 (só leitura): Rever/Novo, Mudança a rever, repetidos, pendências abertas."""
import os, sys, re
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import Base, sim
b = Base()
cs = b.tabela("Cursos")
print("Cursos:", len(cs), Counter(r.get("Estado") for r in cs))
print("Situação (publicados):", Counter(r.get("Situação das inscrições") for r in cs if r.get("Estado") == "Publicado"))
for r in cs:
    if r.get("Estado") in ("Rever", "Novo"):
        print(f"  [{r.get('Estado')}] L{r['_linha']} {r.get('ID')} | {r.get('Título','')[:60]} | {r.get('Entidade','')[:40]} | {r.get('Situação das inscrições')} | {(r.get('Nota da verificação') or '')[:140]}")
print("Mudança a rever:")
for r in cs:
    if sim(r.get("Mudança a rever")):
        print(f"  L{r['_linha']} {r.get('ID')} | {r.get('Estado')} | {r.get('Título','')[:60]} | {(r.get('Nota da verificação') or '')[:160]}")
rep = defaultdict(list)
for r in cs:
    if r.get("Estado") == "Publicado" and r.get("Situação das inscrições") in ("Aberto", "Por confirmar", "Por abrir"):
        rep[(re.sub(r'\W+', ' ', (r.get('Título') or '').lower()).strip(), (r.get('Cidade') or '').lower(), (r.get('Link') or '').split('?')[0].rstrip('/'))].append(r)
print("Repetidos (título+cidade+link):")
for k, v in rep.items():
    if len(v) > 1:
        print("  ", [(x['ID'], x['_linha'], x.get('Origem')) for x in v], k[0][:60])
lk = defaultdict(list)
for r in cs:
    if r.get("Estado") == "Publicado" and r.get("Situação das inscrições") in ("Aberto", "Por confirmar", "Por abrir") and r.get("Modalidade") == "online":
        lk[re.sub(r'\W+', ' ', (r.get('Título') or '').lower()).strip()].append(r)
print("Títulos on-line repetidos:")
for k, v in lk.items():
    if len(v) > 1:
        print("  ", k[:60], [(x['ID'], x.get('Origem'), x.get('Entidade','')[:25]) for x in v])
print("Sem gratuidade comprovada (publicados abertos):", sum(1 for r in cs if r.get("Estado")=="Publicado" and r.get("Situação das inscrições")=="Aberto" and "gratuito" not in (r.get("Campos comprovados") or "") and not (r.get("Revisto por pessoa") or "").strip()))
ps = b.tabela("Pendências para verificar")
print("Pendências:", len(ps), list(ps[0].keys()) if ps else "")
abertas = [p for p in ps if not sim(p.get("Feito"))]
print("Abertas:", len(abertas))
for p in abertas:
    print("  ", p["_linha"], p.get("Aberta em"), "|", p.get("Visto pela última vez"), "|", str(p.get("Problema"))[:150], "|", str(p.get("Origem"))[:20])
for r in cs:
    if r.get("ID") in ("C-cec8358a","C-97deea12"):
        print({k: str(v)[:200] for k, v in r.items() if v and k in ("Estado","Situação das inscrições","Nota da verificação","Notas","Inscrições até","Início","Evidência","Campos comprovados","Link")})
