"""Turmas do Programa Senac de Gratuidade no Rio Grande do Sul, lidas da «Consulta Vagas» oficial, sem Claude (28/11/2026).

A página https://www.senacrs.com.br/hotsite/psg/partials/vagas-filter.php (a «Consulta Vagas» do portal do PSG do
Senac-RS, para onde senacrs.com.br/psg leva) abre a partir do GitHub. Cada turma é um bloco com: categoria (Livres,
Técnicos…), unidade («Senac Santo Ângelo»), curso, «Inscrições: dd/mm/aaaa a dd/mm/aaaa», modalidade, vagas e turno, e
duas janelas: «Requisitos básicos» (renda, idade, escolaridade e, em alguns cursos, um documento) e «Cronograma»
(inscrição, lista de selecionados, chamadas, «Início das aulas», «Dias e horário»). A página guarda também turmas
antigas (2023, 2024); só contam as que têm datas. O botão «Inscreva-se» abre uma janela geral que leva ao sistema de
inscrição por CPF (apsweb.senacrs.com.br/modulos/vestibular): não há página própria por turma, por isso o link do
curso é a «Consulta Vagas», onde está o bloco da turma com os requisitos e o cronograma.

Provas (conferidas a cada leitura na página «Perguntas frequentes» do portal, index.html#/perguntas-frequentes, cujo
texto vem de hotsite/psg/partials/faq.html):
- gratuidade: «…para garantir a oferta de vagas gratuitas em cursos de educação profissional, da Formação Inicial ao
  Nível Técnico, com custo zero à população brasileira de baixa renda.»;
- vagas: «Os interessados fazem suas inscrições e são selecionados segundo a ordem cronológica de suas inscrições.»
  (o site avisa «inscreva-se cedo»);
- renda: o item a) dos «Requisitos básicos» de cada turma.

Cursos que pedem «um dos documentos a seguir: Certificado de curso de qualificação profissional, ou … ou
Autodeclaração de trabalho/experiência profissional» entram (como os cursos «avançados» do Cetam: basta um
certificado de qualquer curso de qualificação ou uma autodeclaração), com o requisito escrito como na página.
"""
import hashlib
import html as _html
import re
import sys
import unicodedata

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim, texto_de_html
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

LISTA = "https://www.senacrs.com.br/hotsite/psg/partials/vagas-filter.php"
FAQ = "https://www.senacrs.com.br/hotsite/psg/partials/faq.html"  # conteúdo da página «Perguntas frequentes» do portal
FAQ_LINK = "https://www.senacrs.com.br/hotsite/psg/index.html#/perguntas-frequentes"
ENTIDADE = "Senac Rio Grande do Sul (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = ("para garantir a oferta de vagas gratuitas em cursos de educação profissional, da Formação Inicial "
                    "ao Nível Técnico, com custo zero à população brasileira de baixa renda")
FRASE_ORDEM = "Os interessados fazem suas inscrições e são selecionados segundo a ordem cronológica de suas inscrições."
REQUISITO_RENDA = "Renda familiar de até 2 salários mínimos por pessoa"


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def iso(dmy):
    m = re.match(r"(\d{2})/(\d{2})/+(\d{4})", dmy or "")  # a página tem «07/02//2027»
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def slug(s):
    n = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in n if not unicodedata.combining(c))).strip("-")[:80]


def cidade_da_unidade(u):
    """«Senac Santo Ângelo» → Santo Ângelo; «Centro Universitário Senac - Porto Alegre» e «Senac Distrito Criativo –
    Porto Alegre» → Porto Alegre; «Centro Universitário Senac» → Porto Alegre (a sede fica em Porto Alegre)."""
    u = re.sub(r"\s+", " ", u or "").strip()
    partes = re.split(r"\s+[-–]\s+", u)
    if len(partes) > 1:
        return partes[-1].strip()
    if re.search(r"Centro Universit[áa]rio", u, re.I):
        return "Porto Alegre"
    return re.sub(r"^(Nova\s+)?Senac\s+", "", u).strip()


def janela(pagina, alvo):
    i = pagina.find(f'id="{alvo}"')
    if i < 0:
        return ""
    fim = pagina.find('<div class="modal fade"', i + 10)
    return limpo(pagina[i:fim if fim > 0 else i + 6000])


def ler_turmas(pagina):
    turmas = []
    for inicio_bloco in re.finditer(r'<div class="card\s+box\b', pagina):
        pos = inicio_bloco.start()
        if pagina.rfind("<!--", 0, pos) > pagina.rfind("-->", 0, pos):
            continue  # bloco dentro de um comentário HTML (turma retirada da página)
        bloco = pagina[inicio_bloco.end():inicio_bloco.end() + 8000].split("<!----------")[0]
        unidade = re.search(r'<h4 class="name">(.*?)</h4>', bloco, re.S)
        # o nome do curso é o primeiro <h5> que não é «Inscrições/Modalidade/Vagas/Turno» (às vezes sem class="name")
        nome = next((h for h in re.finditer(r"<h5[^>]*>(.*?)</h5>", bloco, re.S)
                     if not re.match(r"\s*(Inscri|Modalidade|Vagas|Turno)", limpo(h.group(1)))), None)
        insc = re.search(r"Inscri[çc][õo]es:\s*(\d{2}/\d{2}/+\d{4})\s*a\s*(\d{2}/\d{2}/+\d{4})", bloco)
        if not (unidade and nome and insc):
            continue
        cat = re.search(r'categoria-size-badge">(.*?)</span>', bloco, re.S)
        mod = re.search(r"Modalidade:\s*([^<]+)", bloco)
        vagas = re.search(r"Vagas:\s*(\d+)", bloco)
        turno = re.search(r"Turno:\s*([^<]+)", bloco)
        alvos = re.findall(r'data-bs-target="#([^"]+)"', bloco)
        req = next((janela(pagina, a) for a in alvos if "requisitos" in a), "")
        cron = next((janela(pagina, a) for a in alvos if "cronograma" in a), "")
        n = limpo(nome.group(1))
        # cada janela começa pelo nome do curso; corta-se no primeiro título de outra janela que venha a seguir
        req = re.split(r"\s(?:" + re.escape(n) + r"\s+)?Cronograma\s+Etapas", req)[0]
        cron = re.split(r"\s" + re.escape(n) + r"\s+Requisitos B[áa]sicos|\s\S[^.]{0,80}\sRequisitos B[áa]sicos", cron)[0]
        inicio = re.search(r"In[íi]cio das aulas\s*(\d{2}/\d{2}/+\d{4})", cron)
        dias = re.search(r"Dias e hor[áa]rio\s*(.+?)(?=\s+[A-ZÀ-Ý][\wÀ-ÿ]+\s+(?:Requisitos|Cronograma)|$)", cron)
        itens = re.findall(r"([a-e]\))\s*(.+?)(?=\s+[a-e]\)\s|$)", req.split("seguintes requisitos:")[-1])
        turmas.append({
            "categoria": limpo(cat.group(1)) if cat else "", "unidade": limpo(unidade.group(1)), "nome": n,
            "insc_ini": iso(insc.group(1)), "prazo": iso(insc.group(2)),
            "modalidade": limpo(mod.group(1)) if mod else "", "vagas": vagas.group(1) if vagas else "",
            "turno": limpo(turno.group(1)) if turno else "", "ini": iso(inicio.group(1)) if inicio else "",
            "dias": limpo(dias.group(1))[:120] if dias else "",
            "requisitos": [f"{a} {t.strip(' ;.')}" for a, t in itens], "req_texto": req[:900], "cron_texto": cron[:900],
            "botao": "Inscreva-se" in bloco})
    return turmas


def idade_escolaridade(reqs):
    idade = esc = doc = renda = ""
    for r in reqs:
        if re.search(r"renda", r, re.I):
            renda = r
        elif re.search(r"escolaridade", r, re.I):  # antes da idade: «escolaridade» contém «idade»
            esc = re.sub(r"^[a-e]\)\s*", "", r)
        elif re.search(r"\bidade\b", r, re.I):
            m = re.search(r"(\d{2})\s*anos", r)
            idade = m.group(1) if m else ""
        elif re.search(r"documento|certificado de curso|carteira de trabalho", r, re.I):
            doc = re.sub(r"^[a-e]\)\s*", "", r)
    return idade, esc, doc, renda


# regra de 23/11/2026: fora os cursos que exigem ser estudante ou profissional de uma área (ex.: «ter cursado ou estar
# cursando técnico ou Ensino Superior em Enfermagem»); a alternativa «certificado de qualquer curso de qualificação ou
# autodeclaração» não conta como exigência de área
_AREA = re.compile(r"(?:cursad[oa]|cursando|formad[oa]|forma[çc][ãa]o)\s+(?:o\s+|um\s+)?(?:curso\s+)?(?:t[ée]cnico|ensino superior|gradua)"
                   r"|registro (?:profissional|no conselho)|conhecimentos espec[íi]ficos", re.I)


def exige_area(c):
    m = _AREA.search(" ".join(c["requisitos"]) + " " + c["req_texto"])
    return m.group(0) if m else ""


def auditar(c):
    p = []
    if not c["nome"]:
        p.append("a turma não tem nome")
    if not c["prazo"]:
        p.append("sem prazo de inscrição")
    if c["insc_ini"] and c["prazo"] and c["prazo"] < c["insc_ini"]:
        p.append("o fim das inscrições é antes do início")
    if not c["ini"]:
        p.append("o cronograma não diz o início das aulas")
    elif c["prazo"] and c["ini"] < c["prazo"]:
        p.append(f"as aulas começam ({c['ini']}) antes do fim das inscrições ({c['prazo']})")
    if not c["requisitos"]:
        p.append("não foi possível ler os requisitos básicos")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        pagina = baixar(LISTA, timeout=180).decode("utf-8", "replace")
        texto_faq = texto_de_html(baixar(FAQ, timeout=60))
    except Exception as e:  # noqa: BLE001
        print(f"Senac RS: a Consulta Vagas do PSG não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Senac RS (PSG): a Consulta Vagas não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador.", LISTA, origem="senac_rs.py")
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_faq)
    frase_sel = FRASE_ORDEM if citacao_valida(FRASE_ORDEM, texto_faq) else ""
    lidas = ler_turmas(pagina)
    print(f"Senac RS: {len(lidas)} turmas com datas na Consulta Vagas; gratuidade {'conferida' if gratuito else 'NÃO conferida'}; "
          f"ordem de inscrição {'conferida' if frase_sel else 'não'}.")
    if not gratuito:
        registar_pendencia(base, "Senac RS (PSG): a frase de gratuidade saiu das perguntas frequentes; as turmas novas não são publicadas.",
                           "Se o PSG continua gratuito.", FAQ_LINK, origem="senac_rs.py")
    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(LISTA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA) if (t.get("Link da turma") or "").startswith(LISTA)}
    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for c in lidas:
        if c["prazo"] and c["prazo"] < "2026-01-01":
            continue  # turmas antigas que a página ainda guarda (2023, 2024)
        k = chave(c["nome"])
        if not c["nome"] or k in ocultos:
            continue
        area = exige_area(c)
        if area:
            print(f"  - fora (exige ser da área: «{area}»): {c['nome'][:50]} | {c['unidade']}")
            continue
        link = f"{LISTA}#{slug(c['unidade'] + '-' + c['nome'] + '-' + c['turno'] + '-' + c['insc_ini'])}"
        if link in vistos:
            continue
        vistos.add(link)
        cidade = cidade_da_unidade(c["unidade"])
        idade, esc, doc, renda = idade_escolaridade(c["requisitos"])
        problemas = auditar(c)
        if c["prazo"] and hoje > c["prazo"]:
            situacao = "Encerrada"
        elif c["insc_ini"] and hoje < c["insc_ini"]:
            situacao = "Por abrir"
        elif c["botao"]:
            situacao = "Aberta"
        else:
            situacao = "Encerrada"
        a_distancia = bool(re.search(r"EaD|dist[âa]ncia|on-?line", c["modalidade"], re.I))
        campos = {
            "Título na fonte": c["nome"], "Unidade na fonte": c["unidade"][:200], "Unidade": "", "Cidade": cidade,
            "Link de matrícula": "https://apsweb.senacrs.com.br/modulos/vestibular/", "Início": c["ini"], "Fim": "",
            "Horário": c["turno"], "Dias": c["dias"], "Carga horária": "", "Vagas": c["vagas"], "Prazo de inscrição": c["prazo"],
            "Idade mínima": idade, "Escolaridade": esc[:400], "Documentos": doc[:400],
            "Mais informações": (f"Inscrições de {br(c['insc_ini'])} a {br(c['prazo'])}, pela internet (botão «Inscreva-se» "
                                 f"na Consulta Vagas do PSG, com o CPF). Turno: {c['turno'] or '—'}."
                                 + (f" Dias e horário: {c['dias']}." if c["dias"] else "")),
            "Local na fonte": c["unidade"][:200], "Modo de inscrição": "online", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"Consulta Vagas do PSG do Senac-RS ({LISTA}): «{c['unidade']} {c['nome']} Inscrições: "
                          f"{br(c['insc_ini'])} a {br(c['prazo'])} Modalidade: {c['modalidade']} Vagas: {c['vagas']} Turno: "
                          f"{c['turno']}» | requisitos: «{c['req_texto'][:300]}» | cronograma: «{c['cron_texto'][:300]}»"
                          + (f" | vagas: «{frase_sel}»" if frase_sel else ""))[:1500],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (nome, datas, requisitos e cronograma da Consulta Vagas oficial do PSG do Senac-RS).",
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
                reqs = "\n".join(x for x in [REQUISITO_RENDA if renda else ""] if x)
                novo = {
                    "ID": id_curso(LISTA, c["nome"]), "Estado": "Novo", "Título": c["nome"][:200], "Entidade": ENTIDADE,
                    "Link": LISTA, "Local": "BR-RS", "Modalidade": "online" if a_distancia else "presencial",
                    "País": "BR", "Região": "Rio Grande do Sul", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                    "Necessidades": necessidades("", c["nome"]), "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": reqs, "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                    "Origem": "turmas", "Notas": "",
                    "Como me inscrever": ("1. Abra a Consulta Vagas do PSG do Senac-RS e procure a turma (unidade e nome do curso).\n"
                                          "2. Veja os «Requisitos básicos» e o «Cronograma» da turma.\n"
                                          "3. Clique em \"Inscreva-se\", marque que leu o regulamento e clique em \"Realizar inscrição\".\n"
                                          "4. No sistema de inscrição, escreva o seu CPF e siga os passos.\n"
                                          "5. A seleção é pela ordem das inscrições: se for selecionado, leve os documentos na data da matrícula."),
                    "Nota da verificação": f"{hoje}: curso criado a partir de uma turma da Consulta Vagas do PSG do Senac-RS.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto" if situacao == "Aberta" else "Encerrado",
                    "Verificar automaticamente": "FALSE",
                    "Evidência": " | ".join(x for x in [
                        f"gratuito: «{FRASE_GRATUIDADE}» ({FAQ_LINK}; perguntas frequentes do PSG do Senac-RS)" if gratuito else "",
                        f"renda: «{renda}» ({LISTA}; requisitos básicos da turma)" if renda else "",
                        f"vagas: «{frase_sel}» ({FAQ_LINK})" if frase_sel else ""] if x),
                    "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else "",
                                                                "vagas" if frase_sel else ""] if x),
                    "Renda máxima": REQUISITO_RENDA if renda else "",
                    "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {c['nome'][:45]} | {cidade} | inscrições {c['insc_ini']} a {c['prazo']} | aulas {c['ini'] or '?'} "
              f"| {c['vagas']} vagas | {situacao}" + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))
    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da Consulta Vagas do PSG do Senac-RS."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)
    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = (f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade escrita nas perguntas "
            f"frequentes oficiais do PSG do Senac-RS.")
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
    print(f"\nSenac RS: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
