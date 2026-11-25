"""Data de matrícula tirada do edital, para o site mostrar «Se for aprovado: matrícula de … a …» (25/11/2026).

Regra do responsável: só o que existe mesmo. Para cada curso presencial visível no site, com a coluna «Matrícula (como o
edital diz)» vazia, lê o documento oficial (Link, Página do curso e o «edital: URL» das Notas, quando é PDF ou página)
e procura a linha do cronograma «Matrícula(s) 04 a 08/01/2027» (base.matricula_do_edital: não contam «convocação para
matrícula», vagas remanescentes nem correções; o fim tem de ser depois do prazo de inscrições). Se encontrar, grava a
data, a frase como prova («matrícula: «…» (url)» na Evidência) e «matrícula» em Campos comprovados. Sem frase, nada.

Por omissão só vê os cursos que entraram na base nos últimos 3 dias (rotina diária); TODOS=1 relê todos (uma vez).
"""
import datetime
import os
import re
import sys

from base import Base, carregar_config, curso_no_site, matricula_do_edital, texto_de_html
from comum import baixar
from turmas import hoje_ceara

COLUNA = "Matrícula (como o edital diz)"


def texto_de(url, cache):
    if url in cache:
        return cache[url]
    t = ""
    try:
        dados = baixar(url, timeout=60)
        t = texto_de_html(dados)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {url[:90]}: {type(e).__name__}")
    cache[url] = t
    return t


def main():
    todos = bool(os.environ.get("TODOS"))
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_ceara()
    limite = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=3)).isoformat()
    cache, alteracoes, vistos = {}, [], 0
    for r in base.tabela("Cursos"):
        if (r.get(COLUNA) or "").strip() or (r.get("Modalidade") or "") == "online" or not curso_no_site(r, cfg):
            continue
        if (r.get("Situação das inscrições") or "") == "Encerrado":
            continue
        if not todos and (r.get("Primeiro visto") or "") < limite:
            continue
        urls = [u for u in [r.get("Link"), r.get("Página do curso")] if u and u.startswith("http")]
        urls += re.findall(r"edital: (https?://\S+)", r.get("Notas") or "")
        vistos += 1
        for u in dict.fromkeys(urls):
            frase, bonito = matricula_do_edital(texto_de(u, cache), (r.get("Inscrições até") or "").strip())
            if not frase:
                continue
            ev = ((r.get("Evidência") or "") + f" | matrícula: «{frase}» ({u})").strip(" |")
            comp = ", ".join(dict.fromkeys([c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()] + ["matrícula"]))
            alteracoes.append((r["_linha"], {COLUNA: bonito, "Evidência": ev[:3000], "Campos comprovados": comp}))
            print(f"  + {r.get('Título', '')[:60]} ({r.get('Cidade', '')}): matrícula {bonito} — «{frase}»")
            break
    base.atualizar("Cursos", alteracoes)
    base.guardar()
    print(f"\nMatrícula: {vistos} cursos vistos, {len(alteracoes)} com data de matrícula no edital.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
