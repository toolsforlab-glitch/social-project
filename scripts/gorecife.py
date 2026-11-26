"""Turmas presenciais gratuitas das Escolas Profissionalizantes da Prefeitura do Recife (GO Recife), sem Claude (26/11/2026).

A plataforma GO Recife (https://gorecife.recife.pe.gov.br/cursos), da Prefeitura do Recife, lista os cursos com inscrições
abertas numa API pública (/api/cursos?course_status__iexact=aberto): nome, descrição, escola (nome, rua, bairro), vagas,
carga horária, idade mínima, prazo de inscrição, início e fim, horário e quem oferece. A Secretaria de Trabalho e
Qualificação Profissional (STQP) abre turmas várias vezes por ano (ex.: 529 vagas em 30 cursos, setembro de 2026), com
inscrição de poucos dias. Abre a partir do GitHub.

Regras (as mesmas das outras fontes de turmas):
- só turmas PRESENCIAIS com escola indicada (os cursos on-line da lista são de outras entidades, ex.: Google, Microsoft,
  com páginas próprias);
- situação pela API e pelas datas: Aberta se «course_status» = aberto e o prazo de inscrição não passou; turma que sai da
  lista fica Encerrada;
- gratuidade: frase da página inicial da plataforma («…qualificação profissional. Tudo gratuito.»), conferida por código a
  cada leitura na lista /api/temas, de onde a página a tira;
- idade mínima, escola, datas e horário copiados da API, sem reescrever;
- AUDITORIA antes de publicar: nome, prazo, início, escola e datas coerentes.
"""
import json
import os
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://gorecife.recife.pe.gov.br"
API = SITE + "/api/cursos?course_status__iexact=aberto&page={p}"
LISTA = SITE + "/cursos"
ENTIDADE = "Prefeitura do Recife (Escolas Profissionalizantes – GO Recife)"
FRASE_GRATUIDADE = "Aqui você vai encontrar serviços voltados para o empreendedorismo e a qualificação profissional. Tudo gratuito."
TEMAS = SITE + "/api/temas"


def iso(d):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", (d or "").strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def texto_da_plataforma():
    """O texto «O nome diz tudo…» da página inicial vem da lista pública /api/temas (campo about_us)."""
    return baixar(TEMAS, timeout=60).decode("utf-8", "replace")


def ler_api():
    itens, p = [], 1
    while p <= 10:
        d = json.loads(baixar(API.format(p=p), timeout=60).decode("utf-8", "replace"))
        itens += d.get("results") or []
        if not d.get("next"):
            break
        p += 1
    return itens


def ler(c):
    loc = c.get("location") or {}
    rua = ", ".join(x for x in [(loc.get("street") or "").strip(), (loc.get("number") or "").strip()] if x)
    onde = " – ".join(x for x in [(loc.get("name") or "").strip(),
                                  ", ".join(x for x in [rua, (loc.get("neighborhood") or "").strip()] if x)] if x)
    idade = c.get("minimum_age") or ""
    return {
        "id": str(c.get("id", "")), "nome": re.sub(r"\s+", " ", c.get("name") or "").strip(),
        "descricao": re.sub(r"\s+", " ", c.get("description") or "").strip(),
        "modalidade": (c.get("modality") or "").upper(), "escola": (loc.get("name") or "").strip(),
        "bairro": (loc.get("neighborhood") or "").strip(), "onde": onde,
        "prazo": iso(c.get("registration_deadline")), "ini": iso(c.get("start_date")), "fim": iso(c.get("end_date")),
        "horario": (c.get("time") or "").strip(), "ch": c.get("workload") or "", "vagas": c.get("vacancies") or "",
        "idade": str(idade) if idade else "", "idade_max": str(c.get("maximum_age") or ""),
        "status": (c.get("course_status") or "").lower(), "org": ((c.get("organization") or {}).get("name") or ""),
    }


def auditar(c):
    p = []
    if not c["nome"]:
        p.append("a turma não tem nome")
    if not c["prazo"]:
        p.append("sem prazo de inscrição")
    if not c["ini"]:
        p.append("sem data de início")
    elif c["fim"] and c["fim"] < c["ini"]:
        p.append(f"a data final ({c['fim']}) é anterior ao início ({c['ini']})")
    if not c["escola"]:
        p.append("a turma não indica a escola")
    return p


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
        garantir_aba(base)
    hoje = hoje_ceara()
    try:
        lidas = [ler(c) for c in ler_api()]
        gratuito = citacao_valida(FRASE_GRATUIDADE, texto_da_plataforma())
    except Exception as e:  # noqa: BLE001
        print(f"GO Recife: a lista de cursos não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"GO Recife: a lista de cursos não abriu ({type(e).__name__}).",
                               "Se a página abre no seu navegador.", LISTA, origem="gorecife.py")
            base.guardar()
        return 0
    presenciais = [c for c in lidas if c["modalidade"] == "PRESENCIAL" and c["escola"]]
    print(f"GO Recife: {len(lidas)} cursos abertos na lista, {len(presenciais)} presenciais; gratuidade "
          f"{'conferida' if gratuito else 'NÃO conferida'}.")
    if seco:
        for c in presenciais:
            print(f"  {c['nome'][:40]} | {c['onde'][:60]} | inscrições até {c['prazo']} | início {c['ini']} | "
                  f"{c['vagas']} vagas | idade {c['idade'] or '-'} | {'; '.join(auditar(c)) or 'ok'}")
        return 0
    if not gratuito:
        registar_pendencia(base, "GO Recife: a frase de gratuidade saiu da plataforma; as turmas novas não são publicadas.",
                           "Se os cursos continuam gratuitos.", SITE, origem="gorecife.py")

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(LISTA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(LISTA)}
    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for c in presenciais:
        k = chave(c["nome"])
        if not c["nome"] or k in ocultos or not c["id"]:
            continue
        link = f"{LISTA}#curso-{c['id']}"
        if link in vistos:
            continue
        vistos.add(link)
        problemas = auditar(c)
        situacao = "Aberta" if c["status"] == "aberto" and c["prazo"] and hoje <= c["prazo"] else "Encerrada"
        idade_txt = f"A partir de {c['idade']} anos" if c["idade"] else ""
        campos = {
            "Título na fonte": c["nome"], "Unidade na fonte": c["escola"][:200], "Unidade": "", "Cidade": "Recife",
            "Link de matrícula": LISTA, "Início": c["ini"], "Fim": c["fim"], "Horário": c["horario"][:200], "Dias": "",
            "Carga horária": f"{c['ch']} horas" if c["ch"] else "", "Vagas": str(c["vagas"]),
            "Prazo de inscrição": c["prazo"], "Idade mínima": c["idade"], "Escolaridade": "", "Documentos": "",
            "Mais informações": (f"Inscrições até {br(c['prazo'])}, no botão «Quero me inscrever» da página de cursos do "
                                 f"GO Recife. {c['vagas']} vagas." if c["vagas"] else
                                 f"Inscrições até {br(c['prazo'])}, no botão «Quero me inscrever» da página de cursos do GO Recife."),
            "Local na fonte": c["onde"][:200], "Modo de inscrição": "online", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"lista de cursos do GO Recife ({SITE}/api/cursos), curso {c['id']}: «{c['nome']} | {c['onde']} | "
                          f"inscrições até {br(c['prazo'])} | {br(c['ini'])} a {br(c['fim'])} | {c['horario']} | "
                          f"idade mínima {c['idade'] or '-'}»")[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, prazo, datas e escola da lista oficial do GO Recife).",
        }
        ex = existentes.get(link)
        if ex:
            if problemas and ex.get("Estado") == "Publicado":
                campos["Estado"] = "Rever"
                historico.append(registo(ex, "Auditoria", "Rever", campos["Auditoria"]))
            elif not problemas and ex.get("Estado") == "Rever" and not (ex.get("Notas") or "").strip():
                campos["Estado"] = "Publicado"
            alteracoes.append((ex["_linha"], campos))
            estado_final[link] = (ex.get("Curso", ""), situacao, campos.get("Estado", ex.get("Estado")) == "Publicado")
        elif situacao == "Aberta":
            curso = cursos.get(k)
            if not curso:
                novo = {
                    "ID": id_curso(LISTA, c["nome"]), "Estado": "Novo", "Título": c["nome"][:200], "Entidade": ENTIDADE,
                    "Link": LISTA, "Local": "BR-PE", "Modalidade": "presencial", "País": "BR", "Região": "Pernambuco",
                    "Cidade": "Recife", "Descrição": c["descricao"][:1500], "Origem da descrição": "Texto da página" if c["descricao"] else "",
                    "Necessidades": necessidades("", c["nome"]), "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": idade_txt, "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                    "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma da lista do GO Recife.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": f"gratuito: «{FRASE_GRATUIDADE}» ({SITE}/)" if gratuito else "",
                    "Campos comprovados": "gratuito" if gratuito else "",
                    "O que falta confirmar": "" if gratuito else "A plataforma não diz que o curso é gratuito.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {c['nome'][:45]} | {c['escola'][:40]} | inscrições até {c['prazo'] or '?'} "
              f"| {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da lista de cursos abertos do GO Recife."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade escrita na plataforma GO Recife."
    for n in cursos_novos:
        if pode_publicar(n):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        n_abertas = por_curso.get(r["ID"].strip(), []).count("Aberta")
        campos = {}
        if pode_publicar(r):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
        nova = "Aberto" if n_abertas else "Encerrado"
        if nova != (r.get("Situação das inscrições") or ""):
            campos["Situação das inscrições"] = nova
        if n_abertas:
            campos["Última verificação"] = hoje
        if campos:
            alteracoes_cursos.append((r["_linha"], campos))

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nGO Recife: {len(presenciais)} turmas presenciais lidas; {len(novas)} turmas novas, {len(alteracoes)} "
          f"atualizadas; {len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
