"""Turmas do Programa Senac de Gratuidade em Mato Grosso do Sul, lidas da página oficial, sem Claude (27/11/2026).

A página https://www.ms.senac.br/Cursos/Gratuitos-PSG/Consulta-de-Vagas lista, cidade a cidade (Campo Grande,
Corumbá, Dourados, Ponta Porã, Três Lagoas, Inocência…), cada curso com o seu edital em PDF de uma página e a forma de
inscrição («Inscrições presenciais: … (enquanto durarem as vagas)», às vezes com pré-inscrição num formulário). O edital
tem a carga horária, as vagas, o período do curso («Início: dd/mm/aaaa Término: dd/mm/aaaa»), o local das aulas e os
requisitos (idade, escolaridade, renda per capita de até 2 salários mínimos). Abre a partir do GitHub.

Regras:
- turma aberta: inscrição «enquanto houver/durarem as vagas» e aulas que ainda não começaram; o prazo é a véspera do
  início das aulas (como nas outras fontes «até o limite de vagas»); depois fica Encerrada; turma que sai da página
  fica Encerrada;
- turmas fechadas a um público (escrito «Turma exclusiva», «Turma fechada» ou «via forms pelo parceiro», na página ou
  no edital) não entram: não são abertas ao público;
- gratuidade e renda: frases da própria página de consulta de vagas, conferidas por código a cada leitura (o nome do
  programa não chega, regra de 20/11/2026);
- AUDITORIA antes de publicar: nome, início, local e datas coerentes, e o período copiado do edital.
"""
import datetime
import html as _html
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim, texto_de_html
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://www.ms.senac.br"
PAGINA = SITE + "/Cursos/Gratuitos-PSG/Consulta-de-Vagas"
ENTIDADE = "Senac Mato Grosso do Sul (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = "o Senac abre inscrições para cursos gratuitos, com aulas presenciais e remotas"
FRASE_RENDA = "Para participar, o interessado deve ter a renda do seu grupo familiar (que residem na mesma casa) de até dois salários mínimos."
REQUISITO_RENDA = "Renda familiar de até 2 salários mínimos por pessoa"
FECHADA = re.compile(r"turma\s+(?:exclusiva|fechada)|forms\s+pelo\s+parceiro", re.I)
ATE_VAGAS = re.compile(r"enquanto\s+(?:houver|durarem)\s+(?:as\s+)?vagas", re.I)
DATA = r"(\d{2})/(\d{2})/(\d{4})"


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def iso(m):
    return f"{m[2]}-{m[1]}-{m[0]}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def sem_acentos(s):
    n = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in n if not unicodedata.combining(c))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", sem_acentos(s)).strip("-")[:60]


def url_pdf(href):
    return SITE + urllib.parse.quote(_html.unescape(urllib.parse.unquote(href)), safe="/?=&%()")


def cursos_da_pagina(b):
    """[(cidade, título, url do edital, texto do bloco)] na ordem da página."""
    out = []
    partes = re.split(r'<button class="accordion-button[^"]*"[^>]*>', b)[1:]
    for parte in partes:
        cidade = limpo(parte[:parte.find("</button>")]).title()
        corpo = parte[parte.find("</button>"):]
        for bloco in re.split(r"<strong>\s*Curso:\s*", corpo)[1:]:
            bloco = bloco.split("<strong>Curso:")[0]
            fim_p = bloco.find("</p>")
            bloco = bloco[:fim_p if fim_p > 0 else None]
            titulo = limpo(re.sub(r"^\s*</strong>", "", bloco.split("<br")[0]))
            m = re.search(r'href="(/Portals/0/PSG/[^"]+?\.pdf[^"]*)"', bloco, re.I)
            if titulo:
                out.append((cidade, titulo.strip(" :"), url_pdf(m.group(1)) if m else "", limpo(bloco)))
    return out


def texto_pdf(dados):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(dados)
        f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, check=True).stdout.decode(
            "utf-8", "replace")


def bloco_do_titulo(texto, titulo):
    """Um edital pode trazer mais de uma turma («PSG 2026.46.185 … PSG 2026.46.186»): fica o bloco cujo texto tem mais
    palavras do título; o resto do edital (inscrições, requisitos) vale para todos."""
    cabecalhos = list(re.finditer(r"PSG\s+\d{4}\.\d+\.\d+", texto))
    if len(cabecalhos) <= 1:
        return texto, (cabecalhos[0].group(0) if cabecalhos else "")
    palavras = {w for w in re.findall(r"[a-z]{4,}", sem_acentos(titulo))}
    melhor, codigo, pontos = texto, "", -1
    for i, c in enumerate(cabecalhos):
        trecho = texto[c.start():cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(texto)]
        p = len(palavras & set(re.findall(r"[a-z]{4,}", sem_acentos(trecho))))
        if p > pontos:
            melhor, codigo, pontos = trecho, c.group(0), p
    return melhor, codigo


def local_do_curso(texto):
    """Valor do campo «Local de realização do curso» (tabela de duas colunas: rótulo à esquerda, valor à direita)."""
    linhas = texto.splitlines()
    partes = [[p for p in re.split(r"\s{3,}", l.strip())] for l in linhas]
    for k, ps in enumerate(partes):
        esq = ps[0] if ps else ""
        prox = partes[k + 1][0] if k + 1 < len(partes) and partes[k + 1] else ""
        if re.match(r"Local de real\w*", esq, re.I) and (re.search(r"curso", esq, re.I)
                                                               or re.match(r"do curso", prox, re.I)):
            vals = ps[1:]
            for ps2 in partes[k + 1:k + 4]:
                e2 = ps2[0] if ps2 else ""
                if re.match(r"(Modalidade|Per[íi]odo|Requisitos|Hor[áa]rio|PSG\s+\d)", e2, re.I):
                    break
                if re.match(r"do curso$", e2, re.I) or e2 == "":
                    vals += ps2[1:]
                elif len(ps2) == 1 and not re.match(r"do curso", e2, re.I):
                    vals.append(e2)  # valor sem rótulo à esquerda (linha de continuação)
                else:
                    vals += ps2[1:]
            return re.sub(r"\s+", " ", " ".join(v for v in vals if v)).strip(" •*")
    return ""


def dados_do_edital(texto, titulo):
    bloco, codigo = bloco_do_titulo(texto, titulo)
    plano = re.sub(r"\s+", " ", texto)
    per = re.search(rf"In[íi]cio:\s*{DATA}\s*T[ée]rmino:\s*{DATA}", re.sub(r"\s+", " ", bloco))
    if per:
        ini, fim = iso(per.groups()[:3]), iso(per.groups()[3:])
        frase_per = per.group(0)
    else:
        per = re.search(rf"{DATA}\s*(?:at[ée]|à|a)\s*{DATA}", re.sub(r"\s+", " ", bloco))
        ini, fim = (iso(per.groups()[:3]), iso(per.groups()[3:])) if per else ("", "")
        frase_per = per.group(0) if per else ""
    vag = re.search(r"(\d{1,4})\s*horas\s+(\d{1,3})\b", bloco)
    idade = re.search(r"Idade (?:maior ou igual a|m[íi]nima:?)\s*(\d{2})", plano, re.I)
    esc = re.search(r"((?:Escolaridade M[íi]nima:\s*)?(?:Ensino|Cursando)[^•\n]{3,80}|Escolaridade M[íi]nima:[^•\n]{3,80})", texto, re.I)
    local = local_do_curso(bloco) or local_do_curso(texto)
    insc = re.search(r"(Presencial[^\n]{0,40}|Inscri[çc][õo]es via[^\n]{0,40}|Turma fechada[^\n]{0,60})[^\n]*", texto, re.I)
    m_ate = ATE_VAGAS.search(plano)
    return {"codigo": codigo.replace("  ", " "), "ini": ini, "fim": fim, "frase_periodo": frase_per,
            "carga": f"{vag.group(1)} horas" if vag else "", "vagas": vag.group(2) if vag else "",
            "idade": idade.group(1) if idade else "", "escolaridade": re.sub(r"\s+", " ", esc.group(1)).strip(" .;") if esc else "",
            "local": local[:200], "modo": "a distância" if re.search(r"Modalidade de\s+educa[çc][ãa]o\s+(?:EaD|a dist)", plano, re.I) else "presencial",
            "inscricao": re.sub(r"\s+", " ", insc.group(0)).strip() if insc else "",
            "frase_vagas": m_ate.group(0) if m_ate else "", "fechada": bool(FECHADA.search(plano)),
            "renda": bool(re.search(r"Renda familiar per capita de at[ée] 0?2 sal[áa]rios", plano, re.I)), "texto": plano}


def cidade_do_local(local, cidade_pagina, conhecidas):
    """A cidade das aulas, quando o edital escreve uma das cidades da página («…, Inocência - MS», «Corumbá/MS»);
    senão, a cidade em que a página lista o curso."""
    m = re.findall(r"([A-Za-zÀ-ÿ ]{3,40}?)\s*[-/–]\s*MS\b", local or "")
    if m:
        fim = sem_acentos(m[-1]).strip()
        for c in conhecidas:
            if fim.endswith(sem_acentos(c)):
                return c
    return cidade_pagina


def auditar(c, d):
    p = []
    if not c["titulo"]:
        p.append("a turma não tem nome")
    if not d["ini"]:
        p.append("o edital não tem a data de início")
    elif d["fim"] and d["fim"] < d["ini"]:
        p.append(f"a data final ({d['fim']}) é anterior ao início ({d['ini']})")
    if d["frase_periodo"] and not citacao_valida(d["frase_periodo"], d["texto"]):
        p.append("o período não foi encontrado letra a letra no edital")
    if not d["local"] and not c["cidade"]:
        p.append("a turma não indica onde são as aulas")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        bruto = baixar(PAGINA, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"Senac MS: a página de consulta de vagas não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Senac MS (PSG): a página de consulta de vagas não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador.", PAGINA, origem="senac_ms.py")
        return 0
    pagina = bruto.decode("utf-8", "replace")
    texto_pag = texto_de_html(bruto)
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_pag)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_pag) else ""
    lidos = cursos_da_pagina(pagina)
    print(f"Senac MS: {len(lidos)} cursos na página; gratuidade {'conferida' if gratuito else 'NÃO conferida'}; "
          f"renda {'conferida' if renda else 'não'}.")
    if not gratuito:
        registar_pendencia(base, "Senac MS (PSG): a frase de gratuidade saiu da página de consulta de vagas; as turmas "
                                 "novas não são publicadas.", "Se o PSG continua gratuito.", PAGINA, origem="senac_ms.py")

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(PAGINA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(SITE + "/Portals/0/PSG/")}
    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    textos = {}
    for cidade, titulo, url, txt_bloco in lidos:
        k = chave(titulo)
        if k in ocultos or not url:
            if not url:
                print(f"  ! {titulo} ({cidade}): sem edital na página")
            continue
        if FECHADA.search(txt_bloco):
            print(f"  - {titulo} ({cidade}): turma exclusiva de um parceiro (não é aberta ao público)")
            continue
        try:
            if url not in textos:
                textos[url] = texto_pdf(baixar(url, timeout=60))
        except Exception as e:  # noqa: BLE001
            print(f"  ! {titulo} ({cidade}): o edital não abriu ({type(e).__name__})")
            continue
        d = dados_do_edital(textos[url], titulo)
        if d["fechada"]:
            print(f"  - {titulo} ({cidade}): o edital diz que a turma é exclusiva ou fechada")
            continue
        link = f"{url}#{slug(titulo)}-{d['ini'] or 'sem-data'}"
        if link in vistos:
            continue
        vistos.add(link)
        cidade = cidade_do_local(d["local"], cidade, {x[0] for x in lidos})
        c = {"titulo": titulo, "cidade": cidade}
        problemas = auditar(c, d)
        ate_vagas = bool(d["frase_vagas"] or ATE_VAGAS.search(txt_bloco))
        prazo = ""
        if d["ini"]:
            prazo = (datetime.date.fromisoformat(d["ini"]) - datetime.timedelta(days=1)).isoformat()
        situacao = "Aberta" if ate_vagas and prazo and hoje <= prazo else "Encerrada"
        frase_vagas = d["frase_vagas"] or (ATE_VAGAS.search(txt_bloco).group(0) if ATE_VAGAS.search(txt_bloco) else "")
        campos = {
            "Título na fonte": titulo, "Unidade na fonte": d["local"][:200], "Unidade": "", "Cidade": cidade,
            "Link de matrícula": PAGINA, "Início": d["ini"], "Fim": d["fim"], "Horário": "", "Dias": "",
            "Carga horária": d["carga"], "Vagas": d["vagas"], "Prazo de inscrição": prazo, "Idade mínima": d["idade"],
            "Escolaridade": d["escolaridade"][:400], "Documentos": "",
            "Mais informações": (f"Inscrições enquanto houver vagas, até à véspera do início das aulas ({br(d['ini'])}); "
                                 f"forma de inscrição na página: «{txt_bloco[len(titulo):][:220].strip()}»"
                                 + (f" (edital {d['codigo']} do Senac MS)." if d["codigo"] else ".")),
            "Local na fonte": d["local"][:200], "Modo de inscrição": "presencial", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"edital ({url}): período: «{d['frase_periodo']}»"
                          + (f" | vagas: «{frase_vagas}»" if frase_vagas else "")
                          + f" | página ({PAGINA}): «{txt_bloco[:300]}»")[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, início, local e período do edital oficial do PSG do Senac MS).",
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
                reqs = "; ".join(x for x in [REQUISITO_RENDA if renda else "",
                                             f"Idade mínima: {d['idade']} anos" if d["idade"] else "", d["escolaridade"][:150]] if x)
                novo = {
                    "ID": id_curso(PAGINA, titulo), "Estado": "Novo", "Título": titulo[:200], "Entidade": ENTIDADE,
                    "Link": PAGINA, "Local": "BR-MS", "Modalidade": "online" if d["modo"] == "a distância" else "presencial",
                    "País": "BR", "Região": "Mato Grosso do Sul", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                    "Necessidades": necessidades("", titulo), "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": reqs, "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": d["carga"], "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                    "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma da página de vagas do PSG do Senac MS.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": " | ".join(x for x in [
                        f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA})" if gratuito else "",
                        f"renda: «{renda}» ({PAGINA})" if renda else ""] if x),
                    "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else ""] if x),
                    "Renda máxima": REQUISITO_RENDA if renda else "",
                    "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {titulo[:45]} | {cidade} | aulas {d['ini'] or '?'} a {d['fim'] or '?'} | {d['vagas'] or '?'} vagas "
              f"| {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da página de vagas do PSG do Senac MS."}))
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
            f"oficial do PSG do Senac MS.")
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
    print(f"\nSenac MS: {len(lidos)} cursos na página; {len(novas)} turmas novas, {len(alteracoes)} atualizadas; "
          f"{len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
