"""Vagas gratuitas regimentais do SENAI Rio Grande do Norte, lidas da lista «Oportunidades» e do edital, sem Claude
(26/11/2026).

A página https://www.rn.senai.br/oportunidades/ («Consulte as oportunidades de vagas gratuitas regimentais
disponíveis…») carrega as turmas abertas de uma lista pública (api-oportunidades.php, abre a partir do GitHub): curso,
carga horária, vagas, link de inscrição, período de inscrição, turno, local, tipo (presencial/EAD), modalidade, período
do curso e pré-requisitos. As regras de cada rodada (gratuidade, forma de seleção, requisitos) estão num edital em PDF
publicado em https://www.rn.senai.br/publicacoes/ (ex.: Edital 012/2026, 4 turmas técnicas em Natal, 25 a 29/11/2026).

Regras (REGRAS.md):
- gratuidade: frase da página «Oportunidades» e frase do edital, conferidas por código a cada leitura (I2);
- forma de seleção: frase do edital com sorteio ou ordem de inscrição (I5); edital com prova, redação, entrevista,
  ENEM ou análise de currículo → as turmas ficam fora (E3);
- edital escolhido: o mais recente da página de publicações que nomeia os cursos da lista e o fim das inscrições;
  sem edital que bata, o curso fica em «Rever» (falta a forma de seleção);
- um curso por nome (as turmas do mesmo curso juntam-se na descrição); situação pelas datas da lista: Aberto,
  Por abrir (até 60 dias antes) ou Encerrado; curso que sai da lista com o prazo passado fica Encerrado;
- linhas «Revisto por pessoa» ou Oculto nunca são alteradas (T2). SECO=1 só mostra o diagnóstico.
"""
import datetime
import html as _html
import json
import os
import re
import sys
import urllib.parse

from base import (VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, exige_prova, frase_de_gratuidade,
                  gratuidade_explicita, registar_pendencia, texto_de_html)
from comum import baixar
from cursos import id_curso
from turmas import chave, hoje_ceara, necessidades

SITE = "https://www.rn.senai.br"
API = SITE + "/transparencia/includes/api/api-oportunidades.php?acao=resultado&modalidade=&produto=&cidade=&area=&curso="
LISTA = SITE + "/oportunidades/"
PUBLICACOES = SITE + "/publicacoes/"
ENTIDADE = "SENAI Rio Grande do Norte (Gratuidade Regimental)"
FRASE_LISTA = "Consulte as oportunidades de vagas gratuitas regimentais disponíveis"
ROTULOS = ["Curso", "Carga Horária", "Quantidade de vagas", "Inscrições", "Período de inscrições", "Turno", "Local",
           "Tipo de Curso", "Modalidade", "Período previsto de realização do curso", "Pré-requisito"]
DIAS_POR_ABRIR = 60
_SELECAO = re.compile(r"sorteio|ordem (?:de|das) inscri[çc]|ordem de chegada|ordem cronol[óo]gica", re.I)


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def iso(d):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def ler_lista():
    """Turmas da lista pública, campo a campo, tal como estão escritas."""
    dados = json.loads(baixar(API, timeout=60).decode("utf-8-sig", "replace"))
    html = dados.get("html") or ""
    if "Nenhuma oportunidade encontrada" in html:
        return []
    linhas = [limpo(x) for x in re.split(r"(?i)</t[dh]>|<br\s*/?>|</p>|</div>|</tr>", html)]
    linhas = [x for x in linhas if x]
    turmas, atual, rotulo = [], {}, None
    for l in linhas:
        if l in ROTULOS:
            rotulo = l
            if l == "Curso" and atual:
                turmas.append(atual)
                atual = {}
            atual.setdefault(rotulo, "")
            continue
        if rotulo:
            atual[rotulo] = (atual.get(rotulo, "") + " " + l).strip()
    if atual:
        turmas.append(atual)
    out = []
    for t in turmas:
        p = re.findall(r"\d{2}/\d{2}/\d{4}", t.get("Período de inscrições", ""))
        c = re.findall(r"\d{2}/\d{2}/\d{4}", t.get("Período previsto de realização do curso", ""))
        pre = [x.strip(" -;") for x in re.split(r"\s+-\s+|^-\s*", t.get("Pré-requisito", "")) if x.strip(" -;")]
        out.append({
            "nome": re.sub(r"\s+", " ", t.get("Curso", "")).strip(), "ch": t.get("Carga Horária", "").strip(),
            "vagas": t.get("Quantidade de vagas", "").strip(), "inscricao": t.get("Inscrições", "").strip(),
            "ini": iso(p[0]) if p else "", "fim": iso(p[-1]) if p else "", "turno": t.get("Turno", "").strip(),
            "local": t.get("Local", "").strip(), "tipo": t.get("Tipo de Curso", "").strip(),
            "modalidade": t.get("Modalidade", "").strip(), "aulas_ini": iso(c[0]) if c else "",
            "aulas_fim": iso(c[-1]) if len(c) > 1 else "", "pre": pre,
            "texto": " | ".join(f"{k}: {t.get(k, '')}" for k in ROTULOS if t.get(k)),
        })
    return [t for t in out if t["nome"]]


def editais_recentes(n=6):
    pagina = baixar(PUBLICACOES, timeout=60).decode("utf-8", "replace")
    links = []
    for href, texto in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', pagina, re.S):
        if limpo(texto).upper() == "EDITAL" and href.lower().endswith(".pdf"):
            url = urllib.parse.urljoin(SITE, _html.unescape(href))
            if url not in links:
                links.append(url)
    return links[:n]


def frase_com(texto, regex):
    for f in re.split(r"(?<=[.;:!?])\s+", texto or ""):
        if regex.search(f) and 15 <= len(f) <= 400:
            return f.strip()
    return ""


def edital_das_turmas(turmas):
    """(url, texto) do edital mais recente que nomeia todos os cursos da lista e o último dia das inscrições."""
    nomes = {chave(t["nome"]) for t in turmas}
    fins = {br(t["fim"])[:5] for t in turmas if t["fim"]}
    for url in editais_recentes():
        try:
            dados = baixar(url, timeout=90)
        except Exception as e:  # noqa: BLE001
            print(f"  ! edital {url.rsplit('/', 1)[-1]}: {type(e).__name__}")
            continue
        texto = texto_de_html(dados) if dados[:4] == b"%PDF" else ""
        k = chave(texto)
        if texto and all(n in k for n in nomes) and all(f in texto for f in fins):
            return url, texto
    return "", ""


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
    hoje = hoje_ceara()
    limite_abertura = (datetime.date.fromisoformat(hoje) + datetime.timedelta(days=DIAS_POR_ABRIR)).isoformat()
    try:
        turmas = ler_lista()
        pagina_lista = texto_de_html(baixar(LISTA, timeout=60))
    except Exception as e:  # noqa: BLE001
        print(f"SENAI RN: a lista de oportunidades não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"SENAI RN: a lista de oportunidades não abriu a partir do GitHub ({type(e).__name__}).",
                               "A tarefa diária do navegador tenta ler esta página no Chrome (regra T10).", LISTA,
                               origem="senai_rn.py")
            base.guardar()
        return 0
    gratis_lista = citacao_valida(FRASE_LISTA, pagina_lista)
    print(f"SENAI RN: {len(turmas)} turmas na lista; frase de gratuidade da página {'conferida' if gratis_lista else 'NÃO conferida'}.")

    abertas = [t for t in turmas if t["fim"] and t["fim"] >= hoje and (t["ini"] <= limite_abertura)]
    edital, texto = edital_das_turmas(abertas) if abertas else ("", "")
    prova = exige_prova(texto) if texto else ""
    f_gratis = ""
    if texto:
        f_gratis = "100% GRATUITO" if re.search(r"100\s*%\s*GRATUITO", texto) else frase_de_gratuidade(texto)
    f_selecao = frase_com(texto, _SELECAO) if texto else ""
    f_renda = frase_com(texto, re.compile(r"baixa renda", re.I)) if texto else ""
    print(f"  edital: {edital.rsplit('/', 1)[-1] if edital else 'nenhum bate com a lista'}"
          + (f" | gratuidade: «{f_gratis[:60]}» | seleção: «{f_selecao[:80]}»" if edital else "")
          + (f" | PROVA: «{prova[:80]}»" if prova else ""))

    cursos = {}
    for t in abertas:
        cursos.setdefault((t["nome"], t["tipo"]), []).append(t)
    existentes = {} if seco else {r["ID"].strip(): r for r in base.tabela("Cursos")
                                  if r.get("ID") and (r.get("Link") or "").startswith(LISTA)}
    novos, alteracoes, vistos = [], [], set()
    for (nome, tipo), ts in cursos.items():
        ident = id_curso(LISTA, nome)
        vistos.add(ident)
        prazo = max(t["fim"] for t in ts)
        abre = min(t["ini"] for t in ts if t["ini"]) if any(t["ini"] for t in ts) else ""
        situacao = "Por abrir" if abre and abre > hoje else "Aberto"
        online = bool(re.search(r"dist[âa]ncia|ead|on-?line", tipo, re.I))
        problemas = []
        if prova:
            problemas.append(f"o edital exige prova («{prova[:120]}»): fica fora (regra E3)")
        if not edital:
            problemas.append("não achei o edital desta rodada em www.rn.senai.br/publicacoes/ (falta a forma de seleção)")
        elif not f_selecao:
            problemas.append("o edital não diz que a seleção é por sorteio ou ordem de inscrição")
        if not (gratis_lista or (f_gratis and gratuidade_explicita(f_gratis))):
            problemas.append("não há frase de gratuidade")
        descr_turmas = "; ".join(
            f"{t['local'] or 'local por confirmar'}" + (f", turno {t['turno']}" if t["turno"] else "")
            + (f", aulas de {br(t['aulas_ini'])} a {br(t['aulas_fim'])}" if t["aulas_ini"] and t["aulas_fim"] else "")
            + (f", {t['vagas']} vagas" if t["vagas"] else "") for t in ts)
        print(f"  {'·' if ident in existentes else '+'} {nome[:45]} | {tipo} | {len(ts)} turma(s) | inscrições até {prazo} "
              f"| {situacao}" + (f" | {'; '.join(problemas)}" if problemas else ""))
        if seco:
            continue
        if ident in existentes:
            r = existentes[ident]
            if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
                continue
            campos = {"Última verificação": hoje}
            if (r.get("Situação das inscrições") or "") != situacao:
                campos["Situação das inscrições"] = situacao
            if (r.get("Inscrições até") or "") != prazo and r.get("Estado") != "Oculto":
                campos["Inscrições até"] = prazo
            alteracoes.append((r["_linha"], campos))
            continue
        if prova:
            continue  # regra E3: não entra
        reqs = ([f_renda.rstrip(";.")] if f_renda else []) + [p for t in ts for p in t["pre"]]
        reqs = list(dict.fromkeys(x for x in reqs if x))
        ev = []
        if gratis_lista:
            ev.append(f"gratuito: «{FRASE_LISTA}» ({LISTA})")
        if f_gratis:
            ev.append(f"gratuito: «{f_gratis}» ({edital})")
        ev.append(f"data: «Período de inscrições {br(abre)} a {br(prazo)}» ({LISTA})")
        if f_selecao:
            ev.append(f"vagas: «{f_selecao}» ({edital})")
        if f_renda:
            ev.append(f"renda: «{f_renda}» ({edital})")
        ev.append(f"turmas: «{' || '.join(t['texto'] for t in ts)[:600]}» ({API})")
        comp = ["gratuito", "data"] + (["vagas"] if f_selecao else []) + (["renda"] if f_renda else [])
        if situacao == "Por abrir":
            ev.append(f"abertura: «Período de inscrições {br(abre)} a {br(prazo)}» ({LISTA})")
            comp.append("abertura")
        novos.append({
            "ID": ident, "Estado": "Rever" if problemas else "Publicado", "Título": nome[:200], "Entidade": ENTIDADE,
            "Link": LISTA, "Página do curso": LISTA, "Destino do link": f"lista | procurar: «{nome}»",
            "Local": "BR-RN", "Modalidade": "online" if online else "presencial", "País": "BR",
            "Região": "Rio Grande do Norte",
            "Cidade": "" if online else ("Natal" if all("natal" in t["local"].lower() for t in ts) else ""),
            "Descrição": (f"{ts[0]['modalidade'] or 'Curso'} do SENAI RN pelo Programa de Gratuidade Regimental"
                          + (f", {ts[0]['ch']} horas" if ts[0]["ch"] else "") + f". {len(ts)} turma(s): {descr_turmas}.")[:1500],
            "Origem da descrição": "Texto da página", "Necessidades": necessidades("", nome), "Perfis": "todos",
            "Condição de acesso": "", "Requisitos": "\n".join(reqs)[:800],
            "Certificado": "desconhecido", "Inscrições até": prazo, "Inscrições abrem em": abre if situacao == "Por abrir" else "",
            "Início": min((t["aulas_ini"] for t in ts if t["aulas_ini"]), default=""),
            "Duração": f"{ts[0]['ch']} horas" if ts[0]["ch"] else "", "Link verificado": "SIM",
            "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "edital",
            "Notas": f"{hoje}: criado por senai_rn.py a partir da lista «Oportunidades»" + (f" e do edital {edital}" if edital else "") + ".",
            "Como me inscrever": (f"1. Entre na página «Oportunidades» do SENAI RN (www.rn.senai.br/oportunidades) entre "
                                  f"{br(abre)} e {br(prazo)} e procure «{nome}».\n2. Siga o link de inscrição da turma e "
                                  f"preencha o formulário on-line.\n3. As regras completas estão no edital"
                                  + (f" ({edital})." if edital else ", na página de publicações do SENAI RN.")),
            "Nota da verificação": f"{hoje}: lista e edital lidos por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": situacao, "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": ", ".join(comp), "Mudança a rever": "FALSE",
            "Precisa de internet": "Sim", "O que falta confirmar": "; ".join(problemas),
        })
    # cursos que saíram da lista (ou com o prazo passado) ficam Encerrado
    if not seco:
        for ident, r in existentes.items():
            if ident in vistos or r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
                continue
            if (r.get("Inscrições até") or "9999") < hoje and r.get("Situação das inscrições") != "Encerrado":
                alteracoes.append((r["_linha"], {"Situação das inscrições": "Encerrado", "Última verificação": hoje}))
        base.atualizar("Cursos", alteracoes)
        base.acrescentar("Cursos", novos)
        base.guardar()
    print(f"\nSENAI RN: {len(cursos)} cursos na lista com inscrição aberta ou por abrir; {len(novos)} novos "
          f"({sum(1 for n in novos if n['Estado'] == 'Publicado')} publicados), {len(alteracoes)} atualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
