"""Turmas do Programa Senac de Gratuidade em Roraima, lidas do portal de seleções oficial, sem Claude (25/11/2026).

O portal https://send.rr.senac.br/site/psg lista os editais do PSG (Capital: Boa Vista; Interior: Caracaraí,
Rorainópolis, São Luiz) com o estado «Aberto» ou «Encerrado». A página de cada edital (/site/psg/curso_selecao/<n>) tem
uma linha por turma: cidade, curso, período, turno, pré-requisito (idade, escolaridade, documentos), vagas, vagas
disponíveis e o período de inscrição («06/11/2026 08:30:00 até 08/11/2026 23:59:00»), com o aviso «Inscrições
encerradas» quando já passou. As inscrições duram dois ou três dias, por isso o leitor corre todos os dias. Abre a
partir do GitHub.

Regras (as mesmas das outras fontes de turmas):
- situação pelas datas: «Por abrir» antes do início das inscrições; Aberta dentro do período e sem o aviso de
  encerradas; senão Encerrada; turma que sai das seleções abertas fica Encerrada;
- gratuidade e renda: frases da página «Programa de Gratuidade» do Senac Roraima, conferidas por código a cada leitura
  (o nome do programa não chega, regra de 20/11/2026);
- pré-requisitos copiados do texto da turma, tal como estão escritos (nada reescrito);
- AUDITORIA antes de publicar: nome, prazo, início, cidade e datas coerentes.
"""
import html as _html
import os
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim, texto_de_html
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://send.rr.senac.br"
LISTA = SITE + "/site/psg"
PAGINA_PSG = "https://www.rr.senac.br/portalsenac/programa-de-gratuidade/"
ENTIDADE = "Senac Roraima (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = "com o objetivo de oferecer ações educacionais com custo zero à população brasileira de baixa renda"
FRASE_RENDA = "Possuir renda familiar “per capita” de até dois salários mínimos federal"


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def iso(dmy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dmy or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def selecoes_abertas(pagina):
    """[(link, nome)] das seleções com a etiqueta «Aberto»."""
    out = []
    for linha in pagina.split("<tr>")[1:]:
        m = re.search(r'href="(https://send\.rr\.senac\.br/site/psg/curso_selecao/\d+)">(.*?)</a>', linha, re.S)
        if m and re.search(r'class="label label-success"[^>]*>\s*Aberto', linha):
            out.append((m.group(1), limpo(m.group(2))))
    return out


def turmas_da_selecao(url):
    b = baixar(url, timeout=60).decode("utf-8", "replace")
    corpo = b.split("<tbody>", 1)[1] if "<tbody>" in b else ""
    pdf = re.search(r'href="([^"]+\.pdf)"', b)
    lidas = []
    for linha in corpo.split("<tr>")[1:]:
        linha = re.sub(r"<!--.*?-->", "", linha, flags=re.S)  # a página tem células comentadas
        tds = re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)
        if len(tds) < 3:
            continue
        info = tds[1]
        nome = limpo(info.split("<br", 1)[0])
        campo = lambda rot: (lambda m: limpo(m.group(1)) if m else "")(
            re.search(rf"<b>{rot}:\s*</b>(.*?)<br", info, re.S))
        per = re.search(r"(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})", campo("Período"))
        insc = re.search(r"(\d{2}/\d{2}/\d{4})[^<]*<br\s*/?>\s*até\s*<br\s*/?>\s*(\d{2}/\d{2}/\d{4})", tds[-1])
        pre = campo("Pré-requisito")
        livres = re.search(r"(\d+)", limpo(tds[2])) if len(tds) >= 4 else None
        lidas.append({
            "cidade": limpo(tds[0]), "nome": nome, "ini": iso(per.group(1)) if per else "",
            "fim": iso(per.group(2)) if per else "", "turno": campo("Turno"), "pre": pre, "vagas": campo("Vagas"),
            "livres": livres.group(1) if livres else "", "insc_ini": iso(insc.group(1)) if insc else "",
            "prazo": iso(insc.group(2)) if insc else "", "encerrada": "Inscrições encerradas" in tds[-1],
            "texto": limpo(info)[:600], "pdf": pdf.group(1) if pdf else ""})
    return lidas


def requisitos(pre):
    """Partes do pré-requisito como estão escritas: «idade mínima: 16 anos, escolaridade: …. Documentos exigidos…»."""
    antes_docs = re.split(r"\s*Documentos exigidos", pre, 1)[0]
    docs = re.search(r"Documentos exigidos para matrícula:\s*(.+?)(?:\s*\(O menor|$)", pre)
    idade = re.search(r"idade mínima:\s*(\d{2})\s*anos", pre, re.I)
    esc = re.search(r"escolaridade:\s*(.+?)(?:\.\s|\.$|$)", antes_docs, re.I)
    return (antes_docs.strip(" ."), idade.group(1) if idade else "", esc.group(1).strip(" .") if esc else "",
            docs.group(1).strip(" .") if docs else "")


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
    if c["insc_ini"] and c["prazo"] and c["prazo"] < c["insc_ini"]:
        p.append("o fim das inscrições é antes do início")
    if not c["cidade"]:
        p.append("a turma não indica a cidade")
    return p


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
        garantir_aba(base)
    hoje = hoje_ceara()
    try:
        lista = baixar(LISTA, timeout=60).decode("utf-8", "replace")
        texto_psg = texto_de_html(baixar(PAGINA_PSG, timeout=60))
    except Exception as e:  # noqa: BLE001
        print(f"Senac Roraima: o portal do PSG não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"Senac Roraima (PSG): o portal não abriu ({type(e).__name__}).",
                               "Se a página abre no seu navegador.", LISTA, origem="senac_rr.py")
            base.guardar()
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_psg)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_psg) else ""
    abertas = selecoes_abertas(lista)
    print(f"Senac Roraima: {len(abertas)} seleções com «Aberto»; gratuidade {'conferida' if gratuito else 'NÃO conferida'}; "
          f"renda {'conferida' if renda else 'não'}.")
    lidas = []
    for url, nome_sel in abertas:
        try:
            for c in turmas_da_selecao(url):
                c["selecao"], c["url"] = nome_sel, url
                lidas.append(c)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url}: {e}")
    for c in lidas:
        if c["prazo"] and hoje > c["prazo"] or c["encerrada"]:
            c["situacao"] = "Encerrada"
        elif c["insc_ini"] and hoje < c["insc_ini"]:
            c["situacao"] = "Por abrir"
        else:
            c["situacao"] = "Aberta" if c["prazo"] else "Encerrada"
    if seco:
        for c in lidas:
            req, idade, esc, docs = requisitos(c["pre"])
            print(f"  {c['nome'][:45]} | {c['cidade']} | inscrições {c['insc_ini']} a {c['prazo']} | {c['situacao']} | "
                  f"idade {idade or '-'} | esc. {esc[:40] or '-'} | {'; '.join(auditar(c)) or 'ok'}")
        return 0
    if not gratuito:
        registar_pendencia(base, "Senac Roraima (PSG): a frase de gratuidade saiu da página «Programa de Gratuidade»; "
                                 "as turmas novas não são publicadas.", "Se o PSG continua gratuito.",
                           PAGINA_PSG, origem="senac_rr.py")

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
        if not c["nome"] or k in ocultos:
            continue
        link = f"{c['url']}#{re.sub(r'[^a-z0-9]+', '-', chave(c['nome']))[:50]}-{chave(c['cidade']).replace(' ', '-')}-{c['ini']}"
        if link in vistos:
            continue
        vistos.add(link)
        req, idade, esc, docs = requisitos(c["pre"])
        problemas = auditar(c)
        situacao = c["situacao"]
        campos = {
            "Título na fonte": c["nome"], "Unidade na fonte": "", "Unidade": "", "Cidade": c["cidade"],
            "Link de matrícula": c["url"], "Início": c["ini"], "Fim": c["fim"], "Horário": c["turno"][:200], "Dias": "",
            "Carga horária": "", "Vagas": c["vagas"], "Prazo de inscrição": c["prazo"], "Idade mínima": idade,
            "Escolaridade": esc[:400], "Documentos": docs[:400],
            "Mais informações": (f"Inscrições pela internet, de {br(c['insc_ini'])} a {br(c['prazo'])}, na página do "
                                 f"{c['selecao']}" + (f"; vagas disponíveis: {c['livres']}" if c["livres"] else "") + "."),
            "Local na fonte": c["cidade"], "Modo de inscrição": "online", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": f"{c['selecao']} ({c['url']}): «{c['texto'][:500]}»"[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, prazo, datas e cidade do portal oficial do PSG do Senac Roraima).",
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
        elif situacao in ("Aberta", "Por abrir"):
            curso = cursos.get(k)
            if not curso:
                reqs = "; ".join(x for x in [req, renda] if x)
                novo = {
                    "ID": id_curso(LISTA, c["nome"]), "Estado": "Novo", "Título": c["nome"][:200], "Entidade": ENTIDADE,
                    "Link": LISTA, "Local": "BR-RR", "Modalidade": "presencial", "País": "BR", "Região": "Roraima",
                    "Cidade": "", "Descrição": "", "Origem da descrição": "", "Necessidades": necessidades("", c["nome"]),
                    "Perfis": "todos", "Condição de acesso": "", "Requisitos": reqs[:500], "Certificado": "desconhecido",
                    "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje,
                    "Última verificação": hoje, "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma do portal do PSG do Senac Roraima.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto" if situacao == "Aberta" else "Encerrado",
                    "Verificar automaticamente": "FALSE",
                    "Evidência": " | ".join(x for x in [
                        f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA_PSG})" if gratuito else "",
                        f"renda: «{renda}» ({PAGINA_PSG})" if renda else ""] if x),
                    "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else ""] if x),
                    "Renda máxima": renda,
                    "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {c['nome'][:45]} | {c['cidade']} | inscrições {c['insc_ini']} a {c['prazo'] or '?'} "
              f"| {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu das seleções abertas do portal do PSG do Senac Roraima."}))
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
            f"oficial do PSG do Senac Roraima.")
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
    print(f"\nSenac Roraima: {len(lidas)} turmas lidas; {len(novas)} turmas novas, {len(alteracoes)} atualizadas; "
          f"{len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
