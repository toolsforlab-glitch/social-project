"""Turmas do Programa Senac de Gratuidade no Pará, lidas do portal oficial do PSG, sem Claude (24/11/2026).

O portal https://www.pa.senac.br/psg/selecao lista as seleções de todas as unidades (Belém, Ananindeua, Santarém,
Marabá, Capanema, Redenção…), cada uma com a etiqueta «Inscrições Abertas» ou «Indisponível». A página de cada seleção
(/psg/selecao/detalhar/<cidade>/<n>/<id>) tem, curso a curso: nome, modo de inscrição (online ou presencial),
pré-requisitos (idade, escolaridade), local do curso, período de inscrição, período do curso e o botão «Inscrever
neste curso» ou «Inscrições encerradas». Abre a partir do GitHub.

Regras (as mesmas das outras fontes de turmas):
- situação pelas datas e pelo botão: «Por abrir» antes do início das inscrições; Aberta com o botão de inscrição e o
  prazo por vencer; senão Encerrada; turma que sai da página fica Encerrada;
- gratuidade: frase da página oficial «Como se inscrever» do PSG do Senac Pará (o nome do programa não chega, regra
  de 20/11/2026), conferida por código a cada leitura; renda: frase da página do PSG («até 2 salários mínimos
  federais»); vagas por ordem de inscrição (frase da mesma página): o site avisa «inscreva-se cedo»;
- AUDITORIA antes de publicar: nome, prazo, início, local e datas coerentes.
"""
import html as _html
import re
import sys
import unicodedata

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim, texto_de_html
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://www.pa.senac.br"
LISTA = SITE + "/psg/selecao"
PAGINA_INSCRICAO = SITE + "/psg/como-se-inscrever"
PAGINA_PSG = SITE + "/psg"
ENTIDADE = "Senac Pará (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = "conheça a oferta de vagas gratuitas em unidades mais próximas"
FRASE_RENDA = "Se o resultado for até 2 salários mínimos federais, o candidato poderá concorrer a uma vaga no PSG."
FRASE_ORDEM = "O ingresso nos cursos do PSG se dá por ordem de inscrição do candidato."
REQUISITO_RENDA = "Renda familiar de até 2 salários mínimos por pessoa"


# nomes com acento das cidades que aparecem nos links do portal (o resto fica com a primeira letra maiúscula)
CIDADES = {"belem": "Belém", "maraba": "Marabá", "santarem": "Santarém", "redencao": "Redenção", "castanhal": "Castanhal",
           "ananindeua": "Ananindeua", "barcarena": "Barcarena", "capanema": "Capanema", "parauapebas": "Parauapebas",
           "altamira": "Altamira", "tucurui": "Tucuruí", "braganca": "Bragança", "abaetetuba": "Abaetetuba",
           "paragominas": "Paragominas", "itaituba": "Itaituba", "cameta": "Cametá", "tailandia": "Tailândia",
           "xinguara": "Xinguara", "breves": "Breves", "soure": "Soure", "salinopolis": "Salinópolis"}


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def iso(dmy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dmy or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def slug(s):
    n = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in n if not unicodedata.combining(c))).strip("-")[:60]


def selecoes_abertas(pagina):
    """Links das seleções com a etiqueta «Inscrições Abertas» (cada seleção aparece duas vezes na lista)."""
    links = []
    for bloco in pagina.split('<li class="list-group-item">')[1:]:
        m = re.search(r'href="(https://www\.pa\.senac\.br/psg/selecao/detalhar/[^"]+)"', bloco)
        if m and "Inscrições Abertas" in bloco and m.group(1) not in links:
            links.append(m.group(1))
    return links


def cursos_da_selecao(url):
    b = baixar(url, timeout=60).decode("utf-8", "replace")
    texto = limpo(b)
    m = re.search(r"Seleção\s+(\d+/\d{4})\s+em\s+([A-ZÀ-Ý][\wÀ-ÿ' ]+?)\s+-\s+Programa", texto)
    numero = m.group(1) if m else ""
    # cidade: do título da página («Seleção 150/2026 em Belém - …»); senão, do link (/detalhar/<cidade>/…)
    cidade = m.group(2).strip() if m else ""
    if not cidade:
        s_cid = re.search(r"/detalhar/([a-z\-]+)/", url)
        cidade = CIDADES.get(s_cid.group(1), s_cid.group(1).replace("-", " ").title()) if s_cid else ""
    cursos = []
    for bloco in b.split('<div class="media-body">')[1:]:
        h = re.search(r'<h3 class="h4 media-heading">(.*?)<small>(.*?)</small>', bloco, re.S)
        if not h:
            continue
        pre = re.search(r"<strong>Pré-requisito:</strong>(.*?)<br", bloco, re.S)
        loc = re.search(r"<strong>Local do curso:</strong>(.*?)<br", bloco, re.S)
        insc = re.search(r"Inscrições de\s*<strong>([\d/]+)</strong>.*?até\s*<strong>([\d/]+)</strong>", bloco, re.S)
        per = re.search(r"Período do curso:\s*de\s*<strong>([\d/]+)</strong>\s*até\s*<strong>([\d/]+)</strong>", bloco, re.S)
        cursos.append({
            "nome": limpo(h.group(1)), "modo": "online" if "online" in limpo(h.group(2)).lower() else "presencial",
            "pre": limpo(pre.group(1)) if pre else "", "local": limpo(loc.group(1)).strip(" :;") if loc else "",
            "insc_ini": iso(insc.group(1)) if insc else "", "prazo": iso(insc.group(2)) if insc else "",
            "ini": iso(per.group(1)) if per else "", "fim": iso(per.group(2)) if per else "",
            "botao": "Inscrever neste curso" in bloco, "encerrada": "Inscrições encerradas" in bloco,
            "texto": limpo(bloco)[:600]})
    return numero, cidade, cursos


def idade_escolaridade(pre):
    idade = re.search(r"(?:Requisito de idade|Idade mínima)(?:\s+de)?:?\s*(\d{2})\s*anos|Idade maior ou igual a\s*(\d{2})", pre, re.I)
    esc = re.search(r"Escolaridade mínima:\s*(.+?)(?=\s+Requisito|\s+Idade|$)", pre, re.I)
    return ((idade.group(1) or idade.group(2)) if idade else ""), (esc.group(1).strip(" .;") if esc else "")


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
    if not c["local"]:
        p.append("a turma não indica onde são as aulas")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        lista = baixar(LISTA, timeout=60).decode("utf-8", "replace")
        texto_insc = texto_de_html(baixar(PAGINA_INSCRICAO, timeout=60))
        texto_psg = texto_de_html(baixar(PAGINA_PSG, timeout=60))
    except Exception as e:  # noqa: BLE001
        print(f"Senac Pará: o portal do PSG não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Senac Pará (PSG): o portal não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador.", LISTA, origem="senac_pa.py")
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_insc)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_psg) else ""
    frase_sel = FRASE_ORDEM if citacao_valida(FRASE_ORDEM, texto_insc) else ""
    abertas = selecoes_abertas(lista)
    print(f"Senac Pará: {lista.count('psg/selecao/detalhar/') // 2} seleções na lista, {len(abertas)} com inscrições "
          f"abertas; gratuidade {'conferida' if gratuito else 'NÃO conferida'}; renda {'conferida' if renda else 'não'}; "
          f"ordem de inscrição {'conferida' if frase_sel else 'não'}.")
    if not gratuito:
        registar_pendencia(base, "Senac Pará (PSG): a frase de gratuidade saiu da página «Como se inscrever»; "
                                 "as turmas novas não são publicadas.", "Se o PSG continua gratuito.",
                           PAGINA_INSCRICAO, origem="senac_pa.py")

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
    selecoes_lidas = set()
    for url in abertas:
        try:
            numero, cidade, lidos = cursos_da_selecao(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url}: {e}")
            continue
        selecoes_lidas.add(url)
        for c in lidos:
            k = chave(c["nome"])
            if not c["nome"] or k in ocultos:
                continue
            link = f"{url}#{slug(c['nome'])}-{c['ini'] or 'sem-data'}"
            if link in vistos:
                continue
            vistos.add(link)
            idade, esc = idade_escolaridade(c["pre"])
            problemas = auditar(c)
            if c["prazo"] and hoje > c["prazo"]:
                situacao = "Encerrada"
            elif c["insc_ini"] and hoje < c["insc_ini"]:
                situacao = "Por abrir"
            elif c["prazo"] and not c["encerrada"] and (c["botao"] or c["modo"] == "presencial"):
                # inscrição online: o botão «Inscrever neste curso» mostra que há vagas; inscrição presencial: a
                # página não tem botão, vale o período de inscrição (e o aviso «Inscrições encerradas», se aparecer)
                situacao = "Aberta"
            else:
                situacao = "Encerrada"
            a_distancia = bool(re.search(r"\bEaD\b|a distância|on-?line", c["local"], re.I))
            campos = {
                "Título na fonte": c["nome"], "Unidade na fonte": c["local"][:200], "Unidade": "", "Cidade": cidade,
                "Link de matrícula": url, "Início": c["ini"], "Fim": c["fim"], "Horário": "", "Dias": "",
                "Carga horária": "", "Vagas": "", "Prazo de inscrição": c["prazo"], "Idade mínima": idade,
                "Escolaridade": esc[:400], "Documentos": "",
                "Mais informações": (f"Inscrições de {br(c['insc_ini'])} a {br(c['prazo'])}, "
                                     + ("pela internet, na página da seleção" if c["modo"] == "online"
                                        else "presenciais (o local está no edital, na página da seleção)")
                                     + f" (seleção {numero} do Senac Pará)."),
                "Local na fonte": c["local"][:200], "Modo de inscrição": c["modo"], "Situação": situacao,
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": (f"página da seleção {numero} ({url}): «{c['texto'][:400]}»"
                              + (f" | vagas: «{frase_sel}»" if frase_sel else ""))[:900],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
                f"{hoje}: ok (nome, prazo, datas e local da página oficial do PSG do Senac Pará).",
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
                    reqs = "; ".join(x for x in [REQUISITO_RENDA if renda else "", c["pre"][:250]] if x)
                    novo = {
                        "ID": id_curso(LISTA, c["nome"]), "Estado": "Novo", "Título": c["nome"][:200], "Entidade": ENTIDADE,
                        "Link": LISTA, "Local": "BR-PA", "Modalidade": "online" if a_distancia else "presencial",
                        "País": "BR", "Região": "Pará", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                        "Necessidades": necessidades("", c["nome"]), "Perfis": "todos", "Condição de acesso": "",
                        "Requisitos": reqs, "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                        "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                        "Origem": "turmas", "Notas": "", "Como me inscrever": "",
                        "Nota da verificação": f"{hoje}: curso criado a partir de uma turma do portal do PSG do Senac Pará.",
                        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto" if situacao == "Aberta" else "Encerrado",
                        "Verificar automaticamente": "FALSE",
                        "Evidência": " | ".join(x for x in [
                            f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA_INSCRICAO})" if gratuito else "",
                            f"renda: «{renda}» ({PAGINA_PSG})" if renda else ""] if x),
                        "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else ""] if x),
                        "Renda máxima": REQUISITO_RENDA if renda else "",
                        "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                    }
                    cursos_novos.append(novo)
                    curso = cursos[k] = novo["ID"]
                novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                              "Link da turma": link, "Primeiro visto": hoje, **campos})
                estado_final[link] = (curso, situacao, not problemas)
            print(f"  {'·' if ex else '+'} {c['nome'][:45]} | {cidade} | inscrições {c['insc_ini']} a {c['prazo'] or '?'} "
                  f"| {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    # turmas que deixaram de aparecer (seleção sem «Inscrições Abertas» ou curso retirado)
    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu das seleções abertas do portal do PSG do Senac Pará."}))
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
            f"oficial do PSG do Senac Pará.")
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
    print(f"\nSenac Pará: {len(selecoes_lidas)} seleções lidas; {len(novas)} turmas novas, {len(alteracoes)} atualizadas; "
          f"{len(cursos_novos)} cursos novos ({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
