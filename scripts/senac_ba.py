"""Turmas do Programa Senac de Gratuidade na Bahia, lidas da consulta de vagas oficial, sem Claude (25/11/2026).

O portal do Senac Bahia (www.ba.senac.br) é montado no navegador; a página «Consulta de vagas PSG»
(https://www.ba.senac.br/page/psg-consulta-de-vagas) lê a lista pública /api/cursos/turma/psg/consulta-vagas, que traz,
unidade a unidade, as turmas do PSG com vagas: nome, código, forma de execução, início e fim, fim das matrículas
(presencial e online), vagas, vagas disponíveis, carga horária, horários e um texto da turma (pré-requisitos,
documentos, endereço). Abre a partir do GitHub.

Regras (as mesmas das outras fontes de turmas):
- situação pelas datas e pelas vagas: Aberta com vagas disponíveis e o fim das matrículas por vencer; senão Encerrada;
  turma que sai da lista fica Encerrada;
- gratuidade: frase da página do PSG do Senac Bahia (https://www.ba.senac.br/cursos/PSG), conferida por código a cada
  leitura no texto da própria página (o nome do programa não chega, regra de 20/11/2026); renda: frase da mesma
  página; ordem de inscrição: frase do texto da turma;
- requisitos, documentos e endereço copiados do texto da turma, tal como estão escritos (nada reescrito);
- AUDITORIA antes de publicar: nome, fim das matrículas, início, local e datas coerentes.
"""
import html as _html
import os
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://www.ba.senac.br"
API = SITE + "/api/cursos/turma/psg/consulta-vagas"
LISTA = SITE + "/page/psg-consulta-de-vagas"
PAGINA_PSG = SITE + "/cursos/PSG"
ENTIDADE = "Senac Bahia (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = "Educação profissional gratuita para quem busca uma oportunidade real de crescer."
FRASE_RENDA = "Cursos de educação profissional para pessoas com renda familiar mensal per capita de até dois salários mínimos."
REQUISITO_RENDA = "renda familiar mensal per capita de até dois salários mínimos"
FRASE_ORDEM = "o preenchimento das vagas se dará pela ordem de inscrição dos candidatos"


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def linhas(html_turma):
    """Texto da turma em linhas (um parágrafo ou item de lista por linha), sem marcação."""
    t = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h\d>", "\n", html_turma or "")
    return [x for x in (limpo(l) for l in t.split("\n")) if x]


def secao(ls, inicio, fim):
    """Linhas entre a linha que começa por `inicio` e a primeira que começa por um dos `fim` (sem as duas)."""
    dentro, achou = [], False
    for l in ls:
        n = l.lower().strip("* ")
        if not achou:
            if n.startswith(inicio):
                achou = True
                resto = l.split(":", 1)[1].strip() if ":" in l else ""
                if resto:
                    dentro.append(resto)
            continue
        if any(n.startswith(f) for f in fim):
            break
        dentro.append(l)
    return dentro


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def dia(v):
    """«2026-12-01T03:00:00.000Z» é meia-noite na Bahia (UTC-3): fica a data escrita."""
    return (v or "")[:10] if re.match(r"\d{4}-\d{2}-\d{2}", v or "") else ""


def texto_da_pagina_psg():
    """A página do PSG é montada no navegador: o texto está no módulo PSGHome, ligado a partir do módulo principal."""
    inicial = baixar(SITE + "/", timeout=60).decode("utf-8", "replace")
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', inicial)
    principal = baixar(SITE + m.group(1), timeout=60).decode("utf-8", "replace") if m else ""
    m = re.search(r'assets/(PSGHome-[\w-]+\.js)', principal)
    return baixar(SITE + "/assets/" + m.group(1), timeout=60).decode("utf-8", "replace") if m else ""


def ler_turma(unidade, t):
    ls = linhas(t.get("DetalhesHtml", ""))
    texto = " ".join(ls)
    pre = secao(ls, "pré-requisito", ("documenta", "endereço", "informações", "local"))
    pre += [] if pre else secao(ls, "pré - requisito", ("documenta", "endereço", "informações"))
    docs = secao(ls, "documenta", ("endereço", "informações", "alunos", "maiores", "local"))
    end = next((l.split(":", 1)[1].strip() for l in ls if re.match(r"\*?\s*endereço\s*:", l, re.I)), "")
    beneficios = secao(ls, "alunos/as do curso", ("maiores", "informações", "endereço"))
    idade = next((m.group(1) for l in pre for m in [re.search(r"idade mínima(?: de)?:?\s*(\d{2})", l, re.I)] if m), "")
    esc = next((re.split(r":\s*", l, 1)[1].strip(" .") for l in pre
                if re.match(r"escolaridade(?: mínima| a partir de)?\s*:", l, re.I)), "")
    prazos = [d for d in (dia(t.get("EncerramentoPresencial")), dia(t.get("EncerramentoOnline"))) if d]
    return {
        "id": str(t.get("Id", "")), "codigo": t.get("CodigoFormatado", ""), "nome": limpo(t.get("Nome", "")),
        "unidade": limpo(unidade.get("Nome", "")), "cidade": limpo(unidade.get("Cidade", "")),
        "bairro": limpo(unidade.get("Bairro", "")), "forma": t.get("FormaExecucao") or "",
        "ini": dia(t.get("ExecucaoInicial")), "fim": dia(t.get("ExecucaoFinal")),
        "prazo": max(prazos) if prazos else "", "prazo_online": dia(t.get("EncerramentoOnline")),
        "prazo_presencial": dia(t.get("EncerramentoPresencial")),
        "vagas": t.get("Vagas"), "livres": t.get("VagasDisponiveis"), "ch": t.get("CargaHoraria"),
        "horario": limpo(t.get("Horarios", "")), "pre": pre, "idade": idade, "esc": esc, "docs": docs,
        "endereco": end, "beneficios": beneficios, "texto": texto, "linhas": ls,
        "ordem": FRASE_ORDEM if citacao_valida(FRASE_ORDEM, texto) else "",
    }


def auditar(c):
    p = []
    if not c["nome"]:
        p.append("a turma não tem nome")
    if not c["prazo"]:
        p.append("sem fim das matrículas")
    if not c["ini"]:
        p.append("sem data de início")
    elif c["fim"] and c["fim"] < c["ini"]:
        p.append(f"a data final ({c['fim']}) é anterior ao início ({c['ini']})")
    if not (c["endereco"] or c["unidade"]):
        p.append("a turma não indica onde são as aulas")
    return p


def main():
    seco = bool(os.environ.get("SECO"))  # ensaio: só lê e mostra, sem a folha
    base = None if seco else Base()
    if base:
        carregar_config(base)
        garantir_aba(base)
    hoje = hoje_ceara()
    try:
        import json
        dados = json.loads(baixar(API, timeout=60).decode("utf-8", "replace"))
        texto_psg = texto_da_pagina_psg()
    except Exception as e:  # noqa: BLE001
        print(f"Senac Bahia: a consulta de vagas do PSG não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"Senac Bahia (PSG): a consulta de vagas não abriu ({type(e).__name__}).",
                               "Se a página abre no seu navegador.", LISTA, origem="senac_ba.py")
            base.guardar()
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_psg)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_psg) else ""
    lidas = [ler_turma(u, t) for u in dados.get("unidades", []) for t in (u.get("Turmas") or [])]
    print(f"Senac Bahia: {len(lidas)} turmas na consulta de vagas ({dados.get('totalTurmas')} segundo a lista); "
          f"gratuidade {'conferida' if gratuito else 'NÃO conferida'}; renda {'conferida' if renda else 'não'}.")
    if seco:
        for c in lidas:
            print(f"  {c['nome'][:40]} | {c['unidade']} ({c['cidade']}) | início {c['ini']} | matrículas até {c['prazo']} "
                  f"| {c['livres']} vagas | idade {c['idade'] or '-'} | esc. {c['esc'][:50] or '-'} | ordem "
                  f"{'sim' if c['ordem'] else 'não'} | {'; '.join(auditar(c)) or 'ok'}")
        return 0
    if not gratuito:
        registar_pendencia(base, "Senac Bahia (PSG): a frase de gratuidade saiu da página do PSG; "
                                 "as turmas novas não são publicadas.", "Se o PSG continua gratuito.",
                           PAGINA_PSG, origem="senac_ba.py")

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
    for c in lidas:
        k = chave(c["nome"])
        if not c["nome"] or k in ocultos or not c["id"]:
            continue
        link = f"{LISTA}#turma-{c['id']}"
        if link in vistos:
            continue
        vistos.add(link)
        problemas = auditar(c)
        situacao = "Aberta" if c["prazo"] and hoje <= c["prazo"] and (c["livres"] or 0) > 0 else "Encerrada"
        a_distancia = bool(re.search(r"distância|ead|on-?line", c["forma"], re.I))
        onde = (f"{c['unidade']} – {c['endereco']}" if c["endereco"] else f"{c['unidade']} ({c['bairro']}, {c['cidade']})")
        info = [f"Fim das matrículas: {br(c['prazo_presencial'])} (presencial)" if c["prazo_presencial"] else "",
                f"{br(c['prazo_online'])} (online)" if c["prazo_online"] else "",
                f"Vagas disponíveis na consulta: {c['livres']} de {c['vagas']}" if c["vagas"] is not None else "",
                f"Turma {c['codigo']}" if c["codigo"] else ""]
        campos = {
            "Título na fonte": c["nome"], "Unidade na fonte": c["unidade"][:200], "Unidade": "", "Cidade": c["cidade"],
            "Link de matrícula": LISTA, "Início": c["ini"], "Fim": c["fim"], "Horário": c["horario"][:200], "Dias": "",
            "Carga horária": f"{c['ch']} horas" if c["ch"] else "", "Vagas": str(c["vagas"] or ""),
            "Prazo de inscrição": c["prazo"], "Idade mínima": c["idade"], "Escolaridade": c["esc"][:400],
            "Documentos": "; ".join(c["docs"])[:400],
            "Mais informações": ("; ".join(x for x in info if x) + ". " + " ".join(
                l for l in linhas_texto(c) if l)).strip()[:900],
            "Local na fonte": onde[:200], "Modo de inscrição": "online" if c["prazo_online"] else "presencial",
            "Situação": situacao, "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": f"consulta de vagas do PSG ({API}), turma {c['codigo']}: «{c['texto'][:500]}»"[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, fim das matrículas, datas e local da consulta de vagas oficial do PSG do Senac Bahia).",
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
                reqs = "; ".join(x for x in [*c["pre"], REQUISITO_RENDA if renda else ""] if x)
                beneficio = "; ".join(b for b in c["beneficios"] if re.search(r"transporte|ajuda de custo", b, re.I))
                novo = {
                    "ID": id_curso(LISTA, c["nome"]), "Estado": "Novo", "Título": c["nome"][:200], "Entidade": ENTIDADE,
                    "Link": LISTA, "Local": "BR-BA", "Modalidade": "online" if a_distancia else "presencial",
                    "País": "BR", "Região": "Bahia", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                    "Necessidades": necessidades("", c["nome"]), "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": reqs[:500], "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                    "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma da consulta de vagas do PSG do Senac Bahia.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto",
                    "Verificar automaticamente": "FALSE",
                    "Evidência": " | ".join(x for x in [
                        f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA_PSG})" if gratuito else "",
                        f"renda: «{renda}» ({PAGINA_PSG})" if renda else "",
                        f"vagas: «{c['ordem']}» (texto da turma)" if c["ordem"] else "",
                        f"ajuda: «{beneficio}» (texto da turma)" if beneficio else ""] if x),
                    "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else "",
                                                                "ajuda" if beneficio else ""] if x),
                    "Renda máxima": REQUISITO_RENDA if renda else "",
                    "Ajuda de custo ou transporte": beneficio[:300],
                    "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {c['nome'][:45]} | {c['cidade']} | matrículas até {c['prazo'] or '?'} "
              f"| {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da consulta de vagas do PSG do Senac Bahia."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = (f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade escrita na página "
            f"oficial do PSG do Senac Bahia.")
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
    print(f"\nSenac Bahia: {len(lidas)} turmas lidas; {len(novas)} turmas novas, {len(alteracoes)} atualizadas; "
          f"{len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


def linhas_texto(c):
    """Avisos da turma copiados como estão (matrícula, ordem de inscrição), sem os blocos já postos noutras colunas."""
    fora = set(c["pre"] + c["docs"] + c["beneficios"])
    out = [l for l in c["linhas"] if l not in fora and len(l) < 250
           and re.search(r"matrícula|ordem de", l, re.I) and not re.match(r"\*?\s*(endereço|documenta)", l, re.I)]
    return list(dict.fromkeys(out))[:3]


if __name__ == "__main__":
    sys.exit(main())
