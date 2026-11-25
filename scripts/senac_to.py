"""Turmas do Programa Senac de Gratuidade no Tocantins, lidas da lista oficial de cursos do site, sem Claude (25/11/2026).

O site do Senac Tocantins (www.to.senac.br) é montado no navegador a partir da lista pública
https://app.lms365.com.br/api/v1/courses (a mesma que o site lê, com o identificador do site no cabeçalho «app», escrito
no próprio código público do site). Cada curso traz as turmas (class_sigs) com unidade, cidade, datas, período de
inscrição, horários e os «recursos financeiros»: «Comercial» (pago) e «PSG» (tipo «Gratuito»), cada um com vagas e vagas
disponíveis e o link de matrícula. Só entram as turmas com recurso PSG. Abre a partir do GitHub.

Regras (as mesmas das outras fontes de turmas):
- situação: Aberta com vagas PSG disponíveis e o fim das inscrições por vencer; senão Encerrada; turma que sai da lista
  (ou fica sem recurso PSG) fica Encerrada;
- gratuidade, renda e ordem de inscrição: frases da página «Programa Senac de Gratuidade» do site, conferidas por código
  a cada leitura (o nome do programa não chega, regra de 20/11/2026);
- pré-requisitos copiados do curso, tal como estão escritos (nada reescrito);
- AUDITORIA antes de publicar: nome, fim das inscrições, início, local e datas coerentes.
"""
import html as _html
import json
import os
import re
import sys
import urllib.request

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

API = "https://app.lms365.com.br/api/v1"
APP = "69d4eae4e9d5b"  # identificador público do site do Senac TO (está no código que o site serve a qualquer visitante)
LISTA = "https://www.to.senac.br/cursos/abertos"
PAGINA_PSG = "https://www.to.senac.br/cursos/psg-programa-senac-de-gratuidade"
ENTIDADE = "Senac Tocantins (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = "o Programa Senac de Gratuidade (PSG) oferece gratuitamente cursos em diversas áreas de conhecimento à população"
FRASE_RENDA = "cuja renda familiar mensal per capita não ultrapasse 2 salários mínimos"
REQUISITO_RENDA = "renda familiar mensal per capita não ultrapasse 2 salários mínimos"
FRASE_ORDEM = "O ingresso nos cursos do PSG se dá por ordem de inscrição do candidato."


def api(caminho):
    r = urllib.request.Request(API + caminho, headers={"app": APP, "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read())


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def dia(v):
    return (v or "")[:10] if re.match(r"\d{4}-\d{2}-\d{2}", v or "") else ""


def itens(html_lista):
    return [x for x in (limpo(i).strip(" ;.") for i in re.findall(r"<li[^>]*>(.*?)</li>", html_lista or "", re.S)) if x] or \
        ([limpo(html_lista)] if limpo(html_lista) else [])


def texto_da_pagina_psg():
    d = api("/pages/psg-programa-senac-de-gratuidade/contents")
    return limpo(re.sub(r"\\[nrt]", " ", json.dumps(d, ensure_ascii=False)))


def ler_turmas(cursos):
    lidas = []
    for c in cursos:
        pre = itens(c.get("prerequisite"))
        idade = next((m.group(1) for l in pre for m in [re.search(r"idade (?:maior ou igual a|mínima(?: de)?:?)\s*(\d{2})", l, re.I)] if m), "")
        esc = next((l.split(":", 1)[1].strip(" .;") for l in pre if re.match(r"escolaridade[^:]*:", l, re.I)), "")
        for t in c.get("class_sigs") or []:
            psg = [f for f in (t.get("financial_resources") or []) if "PSG" in str(f.get("nome", "")).upper()]
            if not psg:
                continue
            f = psg[0]
            lidas.append({
                "id": str(t.get("external_id") or t.get("class_id") or t.get("id")), "codigo": str(t.get("class_id") or ""),
                "nome": limpo(c.get("name")), "unidade": limpo(t.get("promoter")), "cidade": limpo(t.get("place")),
                "bairro": "", "forma": t.get("method_execution") or "", "ini": dia(t.get("start_date")),
                "fim": dia(t.get("end_date")), "prazo": dia(t.get("end_date_subscription")) or dia(t.get("start_date")),
                "prazo_online": "", "prazo_presencial": "", "vagas": f.get("vagas"), "livres": f.get("vagasDisponiveis"),
                "ch": t.get("workload") or c.get("workload"), "horario": "; ".join(t.get("schedules") or []),
                "pre": pre, "idade": idade, "esc": esc, "docs": [], "endereco": "", "beneficios": [],
                "texto": limpo(c.get("prerequisite"))[:400], "linhas": [], "ordem": "", "tipo": f.get("tipoDeRecursoNome", ""),
                "matricula": f.get("linkMatriculaOnlineDoRecursoFinanceiroNovo") or t.get("url") or "",
                "curso_id": c.get("id"),
            })
    return lidas


def auditar(c):
    p = []
    if not c["nome"]:
        p.append("a turma não tem nome")
    if not c["prazo"]:
        p.append("sem fim das inscrições")
    if not c["ini"]:
        p.append("sem data de início")
    elif c["fim"] and c["fim"] < c["ini"]:
        p.append(f"a data final ({c['fim']}) é anterior ao início ({c['ini']})")
    if not (c["cidade"] or c["unidade"]):
        p.append("a turma não indica onde são as aulas")
    if (c.get("tipo") or "").lower() != "gratuito":
        p.append(f"o recurso PSG não está marcado como «Gratuito» ({c.get('tipo')})")
    return p


def linhas_texto(c):
    return [FRASE_ORDEM] if c.get("ordem") else []


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
        garantir_aba(base)
    hoje = hoje_ceara()
    try:
        d = api("/courses?per_page=500&page=1")
        cursos = d["data"]["data"] if isinstance(d.get("data"), dict) else d.get("data", [])
        texto_psg = texto_da_pagina_psg()
    except Exception as e:  # noqa: BLE001
        print(f"Senac Tocantins: a lista de cursos não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"Senac Tocantins (PSG): a lista de cursos não abriu ({type(e).__name__}).",
                               "Se o site abre no seu navegador.", LISTA, origem="senac_to.py")
            base.guardar()
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_psg)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_psg) else ""
    ordem = citacao_valida(FRASE_ORDEM, texto_psg)
    lidas = ler_turmas(cursos)
    for c in lidas:
        c["ordem"] = FRASE_ORDEM if ordem else ""
    print(f"Senac Tocantins: {len(cursos)} cursos na lista, {len(lidas)} turmas com vagas do PSG; gratuidade "
          f"{'conferida' if gratuito else 'NÃO conferida'}; renda {'conferida' if renda else 'não'}.")
    if seco:
        for c in lidas:
            print(f"  {c['nome'][:40]} | {c['cidade']} | início {c['ini']} | inscrições até {c['prazo']} | {c['livres']} vagas PSG "
                  f"| idade {c['idade'] or '-'} | esc. {c['esc'][:40] or '-'} | {'; '.join(auditar(c)) or 'ok'}")
        return 0
    if not gratuito:
        registar_pendencia(base, "Senac Tocantins (PSG): a frase de gratuidade saiu da página do PSG; "
                                 "as turmas novas não são publicadas.", "Se o PSG continua gratuito.",
                           PAGINA_PSG, origem="senac_to.py")

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
            "Link de matrícula": c["matricula"] or LISTA, "Início": c["ini"], "Fim": c["fim"], "Horário": c["horario"][:200], "Dias": "",
            "Carga horária": f"{c['ch']} horas" if c["ch"] else "", "Vagas": str(c["vagas"] or ""),
            "Prazo de inscrição": c["prazo"], "Idade mínima": c["idade"], "Escolaridade": c["esc"][:400],
            "Documentos": "; ".join(c["docs"])[:400],
            "Mais informações": ("; ".join(x for x in info if x) + ". " + " ".join(
                l for l in linhas_texto(c) if l)).strip()[:900],
            "Local na fonte": onde[:200], "Modo de inscrição": "online" if c["prazo_online"] else "presencial",
            "Situação": situacao, "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": f"lista de cursos do Senac Tocantins ({API}), turma {c['codigo']}: «{c['texto'][:500]}»"[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, fim das matrículas, datas e local da lista oficial de cursos do Senac Tocantins).",
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
                    "Link": LISTA, "Local": "BR-TO", "Modalidade": "online" if a_distancia else "presencial",
                    "País": "BR", "Região": "Tocantins", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                    "Necessidades": necessidades("", c["nome"]), "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": reqs[:500], "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                    "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma da lista oficial de cursos do Senac Tocantins.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto",
                    "Verificar automaticamente": "FALSE",
                    "Evidência": " | ".join(x for x in [
                        f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA_PSG})" if gratuito else "",
                        f"renda: «{renda}» ({PAGINA_PSG})" if renda else "",
                        f"vagas: «{c['ordem']}» ({PAGINA_PSG})" if c["ordem"] else "",
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
                                             "Notas": "Saiu da lista oficial de cursos do Senac Tocantins."}))
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
            f"oficial do PSG do Senac Tocantins.")
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
    print(f"\nSenac Tocantins: {len(lidas)} turmas lidas; {len(novas)} turmas novas, {len(alteracoes)} atualizadas; "
          f"{len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
