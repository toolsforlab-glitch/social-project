"""Cursos FIC dos campi do IFRO, lidos dos editais oficiais, sem Claude (25/11/2026).

As páginas «Cursos FIC» de cada campus (selecao.ifro.edu.br/extensao-<campus>) listam os editais de seleção de alunos.
Muitos são cursos curtos para a comunidade (ex.: Projeto «Casa da Comunidade», Ji-Paraná, «tendo como prioridade
atendimento aos grupos em situação de vulnerabilidade econômica e social»), com inscrição de dois ou três dias. Este
leitor abre os editais recentes, lê o PDF e cria o curso quando encontra, letra a letra no edital:
- o curso, o município, o requisito de formação e as vagas (Quadro 1);
- o período de inscrição (cronograma) e o local e o horário da inscrição;
- a forma de seleção SEM prova («por ordem de chegada» ou sorteio) — edital com prova, entrevista ou redação fica fora;
- a idade mínima e, se houver, o início das atividades e o local e o horário das aulas.
Gratuidade: o IFRO está marcado «Tudo gratuito» em Sites de confiança (escola pública, decisão do responsável de
23/11/2026). AUDITORIA: datas coerentes (início das aulas depois do fim das inscrições); senão o curso fica em Rever.
Um edital que não segue o modelo não é criado (o vigia do IFRO em vigiar.py abre a pendência).
"""
import datetime
import html as _html
import os
import re
import sys
import urllib.parse

from base import (DESCRICAO_RESUMO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, exige_prova,
                  registar_pendencia, texto_de_html)
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara, necessidades

SITE = "https://selecao.ifro.edu.br"
CAMPI = ["ariquemes", "buritis", "cacoal", "colorado", "guajara-mirim", "jaru", "jiparana", "calama", "zona-norte",
         "saomiguel", "vilhena"]
DIAS = 45  # editais publicados há mais tempo já não têm inscrição aberta
INCLUIR = r"sele[çc][ãa]o de (alunos|cursistas|estudantes|interessados|candidatas)|\bcursos?\b|\bFIC\b|forma[çc][ãa]o inicial"
EXCLUIR = r"professor|bolsista|profissiona|mediador|docente|servidor|ONU|coral|audi[çc]|concurso"
NOMES = {"ariquemes": "Ariquemes", "buritis": "Buritis", "cacoal": "Cacoal", "colorado": "Colorado do Oeste",
         "guajara-mirim": "Guajará-Mirim", "jaru": "Jaru", "jiparana": "Ji-Paraná", "calama": "Porto Velho Calama",
         "zona-norte": "Porto Velho Zona Norte", "saomiguel": "São Miguel do Guaporé", "vilhena": "Vilhena",
         "reitoria": "Reitoria"}
GRATUITO = "gratuito: «entidade marcada como “Tudo gratuito” em Sites de confiança, por uma pessoa» (IFRO: escola pública)"


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def editais_recentes(hoje):
    out = []
    for campus in CAMPI + ["reitoria"]:
        url = f"{SITE}/extensao-{campus}" if campus != "reitoria" else f"{SITE}/reitoria"
        try:
            pagina = baixar(url, timeout=40).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url}: {type(e).__name__}")
            continue
        for bloco in pagina.split('<div class="tileItem">')[1:]:
            m = re.search(r'<h2 class="tileHeadline">\s*<a href="([^"]+)">([^<]+)</a>', bloco)
            d = re.search(r'icon-calendar"></i>\s*(\d{2})/(\d{2})/(\d{2})', bloco)
            if not m or not d:
                continue
            titulo = limpo(m.group(2))
            data = datetime.date(2000 + int(d.group(3)), int(d.group(2)), int(d.group(1)))
            if (hoje - data).days > DIAS or not re.search(INCLUIR, titulo, re.I) or re.search(EXCLUIR, titulo, re.I):
                continue
            out.append({"titulo": titulo, "link": urllib.parse.urljoin(SITE, m.group(1)), "campus": campus,
                        "publicado": data.isoformat()})
    return out


def pdf_do_edital(artigo):
    pagina = baixar(artigo, timeout=40).decode("utf-8", "replace")
    links = re.findall(r'href="(/component/phocadownload/[^"]+download=[^"]+)"', pagina)
    if not links:
        return "", ""
    url = urllib.parse.urljoin(SITE, _html.unescape(links[0]))
    dados = baixar(url, timeout=60)
    return (url, texto_de_html(dados)) if dados[:4] == b"%PDF" else (url, "")


def iso(d, m, a):
    return f"{a}-{int(m):02d}-{int(d):02d}"


def ler_edital(t):
    """Campos do modelo de edital FIC do IFRO; devolve (campos, faltas)."""
    c, faltas = {}, []
    q = re.search(r"Vagas\s+1\s+(.+?)\s*-\s*\(\s*(\d+)\s*h\s*\)\s+([A-ZÀ-Ý][\wÀ-ÿ' -]+?)\s*/\s*RO\s+(.+?)\s+(\d+)\s+Total de vagas", t)
    if q:
        c.update({"curso": q.group(1).strip(), "ch": q.group(2), "cidade": q.group(3).strip(),
                  "formacao": q.group(4).strip(), "vagas": q.group(5), "frase_quadro": q.group(0)})
    else:
        faltas.append("quadro do curso")
    p = re.search(r"Período\s+(?:de\s+)?Inscrição dos\s*\(as\)\s*candidatos\s*\(as\)\s+(\d{2})\s*(?:a|e)\s*(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{4})", t)
    if p:
        c.update({"insc_ini": iso(p.group(1), p.group(3), p.group(4)), "prazo": iso(p.group(2), p.group(3), p.group(4)),
                  "frase_periodo": p.group(0)})
    else:
        faltas.append("período de inscrição")
    s = re.search(r"[^.]{0,200}por ordem de chegada[^.]{0,80}\.", t) or re.search(r"[^.]{0,200}sortei[oa][^.]{0,120}\.", t)
    if s:
        c["frase_selecao"] = s.group(0).strip()
    else:
        faltas.append("forma de seleção (ordem de chegada ou sorteio)")
    if exige_prova(t) or re.search(r"\bentrevista\b|\breda[çc][ãa]o\b", t, re.I):
        faltas.append("o edital fala de prova, entrevista ou redação")
    i = re.search(r"A idade mínima para realizar a inscrição é de (\d+) anos[^.]*\.", t)
    if i:
        c.update({"idade": i.group(1), "frase_idade": i.group(0)})
    loc = re.search(r"ocorrerão exclusivamente\s*n\s*[ao]\s+(.+?)\s*,\s*no horário\s+(?:das\s+)?(.+?)\s*,\s*(?:de segunda|por meio)", t)
    if loc:
        c.update({"local_insc": loc.group(1).strip(), "horario_insc": loc.group(2).strip()})
    aula = re.search(r"exclusivamente presencial\s*,\s*n\s*[ao]\s+(.+?)\s*,\s*((?:de |no |aos? )[^.]+?(?:\d{1,2}[:h]\d{0,2}h?|\d{1,2}h))\s*\.", t)
    if aula:
        c.update({"local_aula": aula.group(1).strip(), "horario_aula": aula.group(2).strip()})
    ini = re.search(r"Previsão de inic[ií]o\s+(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{4})", t)
    if ini:
        c["inicio"] = iso(ini.group(1), ini.group(2), ini.group(3))
    vul = re.search(r"tendo como prioridade atendimento aos grupos em situação de vulnerabilidade econômica e social", t)
    c["prioridade"] = vul.group(0) if vul else ""
    cert = re.search(r"Receberão certificado de qualificação[^.]+\.", t)
    c["frase_cert"] = cert.group(0) if cert else ""
    return c, faltas


def auditar(c):
    p = []
    if c.get("inicio") and c.get("prazo") and c["inicio"] < c["prazo"]:
        p.append(f"o início das atividades ({c['inicio']}) é antes do fim das inscrições ({c['prazo']})")
    if c.get("insc_ini") and c.get("prazo") and c["prazo"] < c["insc_ini"]:
        p.append("o fim das inscrições é antes do início")
    return p


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
    hoje_txt = hoje_ceara()
    hoje = datetime.date.fromisoformat(hoje_txt)
    lista = editais_recentes(hoje)
    print(f"IFRO: {len(lista)} editais recentes de cursos para a comunidade nas páginas dos campi.")
    existentes = {} if seco else {r["ID"]: r for r in base.tabela("Cursos") if (r.get("Link") or "").startswith(SITE)}
    novos, alteracoes = [], []
    for e in lista:
        try:
            pdf, texto = pdf_do_edital(e["link"])
        except Exception as ex:  # noqa: BLE001
            print(f"  ! {e['titulo'][:60]}: {type(ex).__name__}")
            continue
        if not texto:
            print(f"  - {e['titulo'][:70]}: sem PDF legível")
            continue
        c, faltas = ler_edital(texto)
        nome = c.get("curso") or e["titulo"]
        if faltas:
            print(f"  - {e['titulo'][:70]}: não segue o modelo ({'; '.join(faltas)})")
            continue
        provas = [citacao_valida(c[k], texto) for k in ("frase_quadro", "frase_periodo", "frase_selecao") if c.get(k)]
        if not all(provas):
            print(f"  - {nome[:60]}: frases não conferem no PDF")
            continue
        problemas = auditar(c)
        aberto = c["insc_ini"] <= hoje_txt <= c["prazo"] or hoje_txt < c["insc_ini"]
        ident = id_curso(e["link"], nome)
        print(f"  {'·' if ident in existentes else '+'} {nome[:50]} | {c['cidade']} | inscrições {c['insc_ini']} a {c['prazo']}"
              f" | {'aberto' if aberto else 'encerrado'}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))
        if seco:
            continue
        if ident in existentes:
            r = existentes[ident]
            nova = "Aberto" if aberto else "Encerrado"
            if nova != (r.get("Situação das inscrições") or ""):
                alteracoes.append((r["_linha"], {"Situação das inscrições": nova, "Última verificação": hoje_txt}))
            continue
        if not aberto:
            continue
        reqs = "; ".join(x for x in [c.get("formacao", ""), c.get("frase_idade", "").rstrip(".")] if x)
        quando = (f"As aulas são {c['horario_aula']}, em {c['local_aula']}" if c.get("horario_aula") else
                  "O local, os dias e os horários das aulas são divulgados depois da seleção")
        ev = [GRATUITO, f"curso: «{c['frase_quadro']}» ({pdf})", f"data: «{c['frase_periodo']}» ({pdf})",
              f"vagas: «{c['frase_selecao']}» ({pdf})"]
        comp = ["gratuito", "data"]
        if c.get("frase_idade"):
            ev.append(f"idade: «{c['frase_idade']}» ({pdf})")
            comp.append("idade")
        if c.get("prioridade"):
            ev.append(f"público: «{c['prioridade']}» ({pdf})")
        if c.get("frase_cert"):
            ev.append(f"certificado: «{c['frase_cert']}» ({pdf})")
        novos.append({
            "ID": ident, "Estado": "Rever" if problemas else "Publicado", "Título": nome[:200],
            "Entidade": f"IFRO – Instituto Federal de Rondônia ({'Campus ' if e['campus'] != 'reitoria' else ''}{NOMES[e['campus']]})",
            "Link": e["link"], "Página do curso": e["link"], "Local": "BR-RO", "Modalidade": "presencial", "País": "BR",
            "Região": "Rondônia", "Cidade": c["cidade"],
            "Descrição": (f"Curso gratuito de {c['ch']} horas em {c['cidade']}, do IFRO. São {c['vagas']} vagas. A inscrição é "
                          f"presencial, de {br(c['insc_ini'])} a {br(c['prazo'])}, por ordem de chegada ou sorteio, como diz o "
                          f"edital. {quando}."),
            "Origem da descrição": DESCRICAO_RESUMO, "Necessidades": necessidades("", nome), "Perfis": "todos",
            "Condição de acesso": "", "Requisitos": reqs[:500], "Certificado": "desconhecido", "Inscrições até": c["prazo"],
            "Início": c.get("inicio", ""), "Duração": f"{c['ch']} horas", "Link verificado": "SIM",
            "Primeiro visto": hoje_txt, "Última verificação": hoje_txt, "Origem": "turmas", "Notas": "",
            "Como me inscrever": (f"Vá ao local de inscrição: {c['local_insc']}" + (f", {c['horario_insc']}" if c.get('horario_insc') else "")
                                  + f", de {br(c['insc_ini'])} a {br(c['prazo'])}. Leve um documento de identificação. O edital está no botão do curso.")
            if c.get("local_insc") else "As regras de inscrição estão no edital (botão do curso).",
            "Nota da verificação": f"{hoje_txt}: criado por ifro_fic.py a partir do edital oficial (frases conferidas por código).",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": ", ".join(comp),
            "Idade mínima": c.get("idade", ""),
            "O que falta confirmar": "; ".join(problemas),
        })
    if seco:
        return 0
    base.atualizar("Cursos", alteracoes)
    base.acrescentar("Cursos", novos)
    base.guardar()
    print(f"\nIFRO: {len(novos)} cursos novos ({sum(1 for n in novos if n['Estado'] == 'Publicado')} publicados), "
          f"{len(alteracoes)} atualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
