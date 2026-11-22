"""Turmas dos cursos, lidas diretamente das páginas oficiais, sem Claude.

O Senac Ceará (Programa Senac de Gratuidade) tem uma página por turma, com unidade, datas, horário,
prazo de inscrição, idade mínima, escolaridade e o botão "matricule-se". Os cursos da folha juntam
várias turmas, por isso o link do curso só podia apontar para a lista geral. Este script:

1. percorre a lista de oportunidades do Senac PSG e encontra as turmas dos cursos que já estão na folha
   (mesmo título, curso com link do psg.ce.senac.br);
2. abre a página de cada turma e copia os dados por código, tal como estão escritos;
3. calcula a situação só a partir das datas da própria página:
   - com prazo de inscrição: Aberta até ao fim desse dia, depois Encerrada;
   - sem prazo: Por confirmar enquanto a turma não começou, depois Encerrada;
4. grava tudo no separador "Turmas". Uma pessoa pode pôr Estado = Oculto para esconder uma turma;
5. quando aparece uma turma aberta de um curso que ainda não está na folha, cria o curso em Cursos com
   Estado = Novo (uma pessoa aprova), com o título e a descrição copiados da página da turma e as regras
   gerais do programa (renda, documentos) copiadas da página "Bolsas de estudos", confirmadas por código;
6. atualiza a "Situação das inscrições" de cada curso do Senac PSG a partir das suas turmas;
7. AUDITORIA INDEPENDENTE de cada turma, antes de publicar: a página é lida uma segunda vez por outro método
   (texto visível e ordem dos separadores, em vez dos identificadores do HTML) e as duas leituras têm de
   coincidir; depois verifica-se se as datas e o horário fazem sentido. Só as turmas que passam ficam
   Publicado; as outras ficam em Rever, com o motivo na coluna Auditoria, e não aparecem no site;
8. um curso criado pelas turmas passa sozinho de Novo a Publicado quando tem pelo menos uma turma aberta
   aprovada na auditoria, descrição e as regras do programa comprovadas.

Regras:
- Nada é deduzido nem resumido: cada valor vem do texto da página da turma (a coluna Evidência guarda-o).
- Uma turma só é ligada a uma unidade da folha quando o nome na página é igual ao Nome ou a um dos
  "Nomes na fonte" da organização. Se não houver correspondência exata, fica só o nome da página.
- Turmas novas só entram se ainda não estiverem encerradas.
- Um curso com Estado = Oculto nunca é recriado nem recebe turmas.
- As "Necessidades" de um curso novo vêm de uma tabela simples por área do Senac (é só para os filtros do site).
- Se a página de uma turma deixar de abrir N vezes seguidas, a turma passa a Encerrada.
"""
import datetime
import hashlib
import html
import os
import re
import sys
import time
import unicodedata

from base import registar_pendencia, DESCRICAO_PAGINA, DESCRICAO_RESUMO, frase_de_gratuidade, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, numero, sim, texto_de_html
from comum import baixar

ABA = "Turmas"
COLUNAS = ["ID", "Curso", "Estado", "Título na fonte", "Unidade na fonte", "Cidade", "Unidade", "Link da turma",
           "Link de matrícula", "Início", "Fim", "Horário", "Dias", "Carga horária", "Vagas", "Prazo de inscrição",
           "Idade mínima", "Escolaridade", "Documentos", "Mais informações", "Situação", "Primeiro visto",
           "Última verificação", "Falhas seguidas", "Evidência", "Notas", "Auditoria", "Local na fonte",
           "Modo de inscrição", "Vagas reservadas"]
LISTA_PSG = "https://psg.ce.senac.br/oportunidades/"
BOLSAS_PSG = "https://psg.ce.senac.br/bolsa-de-estudos/"
# Gratuidade do programa, escrita na página oficial do Senac Ceará (as páginas das turmas e a de Bolsas de estudos
# não o dizem por escrito). Verificada letra a letra, por código, em cada leitura (regra de 20/11/2026).
PAGINA_GRATUIDADE_PSG = "https://www.ce.senac.br/programa-senac-de-gratuidade/"
FRASE_GRATUIDADE_PSG = "O Senac oferta vagas gratuitas para pessoas de baixa renda por meio do Programa Senac Gratuidade"
ENTIDADE_PSG = "Senac Ceará (Programa Senac de Gratuidade)"
DIAS_PARA_TRAS = 7  # turmas que começaram há mais tempo do que isto não são abertas para procurar cursos novos
# Regras gerais do programa: (frase exata da página Bolsas de estudos, coluna, valor, nome em Campos comprovados)
REGRAS_PSG = [
    ("Ter renda familiar per capita de até dois salários mínimos.", "Renda máxima",
     "Renda familiar por pessoa de até dois salários mínimos", "renda"),
    ("Documentos necessários RG, CPF e valor da renda bruta familiar mensal.", "Documentos pedidos",
     "RG, CPF e valor da renda bruta familiar mensal", "documentos"),
    ("presencialmente na unidade Senac ou de forma online", "Precisa de internet", "Não", "internet"),
]
REGRA_APERFEICOAMENTO = ("Para cursos de aperfeiçoamento, é preciso ter certificação profissional, registro na CTPS, "
                         "declaração de empresa ou autodeclaração.")
# Área do Senac → necessidades do site (só para os filtros; todos são cursos de profissão)
NECESSIDADES_POR_AREA = [("informatica", "tecnologia"), ("tecnologia", "tecnologia"), ("gestao", "negocio"),
                         ("comercio", "negocio")]
NECESSIDADES_POR_TITULO = [("mundo digital", "digital"), ("informatica basica", "digital"),
                           ("empreended", "negocio"), ("negocio", "negocio")]
MAX_PAGINAS = int(os.environ.get("TURMAS_MAX_PAGINAS", "40"))
PAUSA = float(os.environ.get("TURMAS_PAUSA", "0.5"))
FUSO_CEARA = datetime.timezone(datetime.timedelta(hours=-3))


# ------------------------------------------------------------------ texto

def limpo(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", t or ""))).strip()


def chave(t):
    """Para comparar títulos e nomes: sem código de turma, sem acentos, minúsculas."""
    t = limpo(t)
    t = re.sub(r"^\d{4}\.\d+\.\d+\s*[–—-]\s*", "", t)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[–—]", "-", t)
    t = re.sub(r"\s*-\s*", " - ", t)
    return re.sub(r"\s+", " ", t).strip()


def data_iso(t):
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t or "")
    if not m:
        return ""
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return ""


def hoje_ceara():
    return datetime.datetime.now(FUSO_CEARA).date().isoformat()


def id_curso(url, titulo):
    """Igual ao de cursos.py, para a pesquisa semanal reconhecer o curso."""
    return "C-" + hashlib.sha1((url + "|" + titulo.strip().lower()).encode()).hexdigest()[:8]


def titulo_sem_codigo(t):
    return re.sub(r"^\d{4}\.\d+\.\d+\s*[–—-]\s*", "", limpo(t)).strip()


def necessidades(area, titulo):
    ids = ["profissao", "emprego"]
    a, t = chave(area), chave(titulo)
    for palavra, nid in NECESSIDADES_POR_AREA:
        if palavra in a and nid not in ids:
            ids.append(nid)
    for palavra, nid in NECESSIDADES_POR_TITULO:
        if palavra in t and nid not in ids:
            ids.append(nid)
    return ", ".join(ids)


def id_turma(link):
    return "T-" + hashlib.sha1(link.strip().rstrip("/").encode()).hexdigest()[:8]


# ------------------------------------------------------------------ leitura das páginas

def ler_lista(pagina_html):
    """Caixas da lista de oportunidades: título, unidade, datas e link da página da turma."""
    caixas = []
    for bloco in re.findall(r'(?s)<div class="opportunities__box">(.*?)</a>\s*</div>', pagina_html):
        link = re.search(r'href="(https?://psg\.ce\.senac\.br/oportunidade/[^"]+)"', bloco)
        titulo = re.search(r"(?s)<h5>(.*?)</h5>", bloco)
        infos = [limpo(p) for p in re.findall(r'(?s)<div class="opportunities__info">.*?<p>(.*?)</p>', bloco)]
        if link and titulo:
            caixas.append({"link": html.unescape(link.group(1)), "titulo": limpo(titulo.group(1)), "infos": infos,
                           "inicio": next((data_iso(i) for i in infos if data_iso(i)), "")})
    return caixas


def ler_turma(pagina_html):
    """Dados da página de uma turma, copiados tal como aparecem."""
    d = {}
    m = re.search(r'(?s)<div class="content__title">\s*<h3>(.*?)</h3>', pagina_html)
    d["titulo"] = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<div class="content__categorie">\s*<small>(.*?)</small>', pagina_html)
    d["area"] = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<div class="content__description">(.*?)</div>', pagina_html)
    d["descricao"] = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<span class="unit_name">(.*?)</span>', pagina_html)
    unidade_cidade = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<p class="item-content__info unit_name">(.*?)</p>', pagina_html)
    d["unidade"] = limpo(m.group(1)) if m else unidade_cidade.split("|")[0].strip()
    d["cidade"] = unidade_cidade.rsplit("|", 1)[1].strip() if "|" in unidade_cidade else ""
    datas = [limpo(x) for x in re.findall(r'(?s)<p class="item-content__info date_hour">(.*?)</p>', pagina_html)]
    d["inicio_texto"] = datas[0] if datas else ""
    d["fim_texto"] = datas[1] if len(datas) > 1 else ""
    d["inicio"] = data_iso(d["inicio_texto"])
    d["fim"] = data_iso(d["fim_texto"])
    h = re.search(r"\(\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*\)", d["inicio_texto"])
    d["horario"] = f"{h.group(1)} - {h.group(2)}" if h else ""
    m = re.search(r'(?s)<p class="item-content__info total_hours">(.*?)</p>', pagina_html)
    d["carga"] = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<a\s+href="([^"]*)"\s+class="prices__button"', pagina_html)
    d["matricula"] = html.unescape(m.group(1)).strip() if m else ""
    abas = {i: limpo(t) for i, t in re.findall(
        r'(?s)data-tab-id="([^"]+)"[^>]*class="tab-content-item[^"]*"\s*>(.*?)</div>', pagina_html)}
    d["vagas"] = abas.get("quantidade-de-vagas-ofertadas", "")
    d["dias"] = abas.get("periodicidade", "")
    d["documentos"] = abas.get("pre-requisitos", "")
    d["escolaridade"] = abas.get("escolaridade", "")
    d["idade_texto"] = abas.get("idade-minima", "")
    m = re.search(r"(\d{1,2})\s*anos", d["idade_texto"], re.I)
    d["idade"] = m.group(1) if m else ""
    d["prazo_texto"] = abas.get("prazo-para-inscricao", "")
    d["prazo"] = data_iso(d["prazo_texto"])
    d["mais"] = abas.get("mais-informacoes", "")
    return d


def situacao(d, hoje):
    if d.get("prazo"):
        return "Aberta" if hoje <= d["prazo"] else "Encerrada"
    if d.get("inicio"):
        return "Por confirmar" if hoje < d["inicio"] else "Encerrada"
    return "Por confirmar"


def evidencia(d):
    partes = []
    if d.get("prazo_texto"):
        partes.append(f"«Prazo para inscrição: {d['prazo_texto']}»")
    if d.get("inicio_texto"):
        partes.append(f"«Data início: {d['inicio_texto']}»")
    if d.get("fim_texto"):
        partes.append(f"«Data final: {d['fim_texto']}»")
    if d.get("unidade"):
        partes.append(f"«Unidade: {d['unidade']}»")
    if d.get("idade_texto"):
        partes.append(f"«{d['idade_texto']}»")
    if d.get("escolaridade"):
        partes.append(f"«Escolaridade: {d['escolaridade']}»")
    return " | ".join(partes)[:900]


def auditar(d, pagina_html):
    """Segunda leitura da página, por outro método, e controlo de coerência. Devolve a lista de problemas."""
    problemas = []
    texto = texto_de_html(pagina_html)
    # 1. segunda leitura: texto visível e posição dos separadores
    m = re.search(r"Data início:\s*(\d{1,2}/\d{1,2}/\d{4})", texto)
    if (data_iso(m.group(1)) if m else "") != d.get("inicio", ""):
        problemas.append("a segunda leitura não confirma a data de início")
    m = re.search(r"Data final:\s*(\d{1,2}/\d{1,2}/\d{4})", texto)
    if (data_iso(m.group(1)) if m else "") != d.get("fim", ""):
        problemas.append("a segunda leitura não confirma a data final")
    if d.get("unidade") and chave("Unidade: " + d["unidade"]) not in chave(texto):
        problemas.append("a segunda leitura não confirma a unidade")
    titulos = [limpo(x) for x in re.findall(r'(?s)class="tab-header-item[^"]*"\s*>(.*?)</div>', pagina_html)]
    conteudos = [limpo(x) for x in re.findall(r'(?s)class="tab-content-item[^"]*"\s*>(.*?)</div>', pagina_html)]

    def separador(nome):
        return conteudos[titulos.index(nome)] if nome in titulos and titulos.index(nome) < len(conteudos) else ""
    if data_iso(separador("Prazo para inscrição")) != d.get("prazo", ""):
        problemas.append("a segunda leitura não confirma o prazo de inscrição")
    m = re.search(r"(\d{1,2})\s*anos", separador("Idade mínima"), re.I)
    if (m.group(1) if m else "") != d.get("idade", ""):
        problemas.append("a segunda leitura não confirma a idade mínima")
    # o link de matrícula traz o código do recurso financeiro: 1 nas turmas do Programa Senac de Gratuidade
    m = re.search(r"recursofinanceiroid=(\d+)", d.get("matricula", ""))
    if m and m.group(1) != "1":
        problemas.append("o link de matrícula indica outro recurso financeiro (código " + m.group(1)
                         + "): pode não ser uma turma do Programa Senac de Gratuidade, com outras regras")
    # 2. coerência
    ini, fim, prazo = d.get("inicio", ""), d.get("fim", ""), d.get("prazo", "")
    if not ini:
        problemas.append("a página não tem data de início")
    if not d.get("unidade"):
        problemas.append("a página não indica a unidade")
    if ini and fim and fim < ini:
        problemas.append(f"a data final ({fim}) é anterior ao início ({ini})")
    h = re.match(r"(\d{1,2}):(\d{2}) - (\d{1,2}):(\d{2})", d.get("horario", ""))
    if h and (int(h.group(1)) < 5 or (int(h.group(1)), int(h.group(2))) >= (int(h.group(3)), int(h.group(4)))):
        problemas.append(f"o horário ({d['horario']}) não faz sentido")
    if ini and prazo and prazo > (datetime.date.fromisoformat(ini) + datetime.timedelta(days=14)).isoformat():
        problemas.append(f"o prazo de inscrição ({prazo}) é mais de duas semanas depois do início ({ini})")
    return problemas


def campos_da_turma(d, unidades):
    unidade_id = unidades.get(chave(d.get("unidade", "")), "")
    return {
        "Título na fonte": d.get("titulo", ""), "Unidade na fonte": d.get("unidade", ""),
        "Cidade": d.get("cidade", ""), "Unidade": unidade_id, "Link de matrícula": d.get("matricula", ""),
        "Início": d.get("inicio", ""), "Fim": d.get("fim", ""), "Horário": d.get("horario", ""),
        "Dias": d.get("dias", ""), "Carga horária": d.get("carga", ""), "Vagas": d.get("vagas", ""),
        "Prazo de inscrição": d.get("prazo", ""), "Idade mínima": d.get("idade", ""),
        "Escolaridade": d.get("escolaridade", ""), "Documentos": d.get("documentos", ""),
        "Mais informações": d.get("mais", ""), "Evidência": evidencia(d),
    }


# ------------------------------------------------------------------ principal

def baixar_texto(url):
    return baixar(url, timeout=30).decode("utf-8", "replace")


def garantir_aba(base):
    if ABA in base.abas():
        return
    if base.local:
        base.dados[ABA] = [COLUNAS]
        return
    folha = base.folha.add_worksheet(title=ABA, rows=200, cols=len(COLUNAS))
    folha.update([COLUNAS], "A1")
    folha.freeze(rows=1)
    base._cache.pop(ABA, None)


def mapa_unidades(base):
    """Nome normalizado → ID da organização (Nome e "Nomes na fonte")."""
    m = {}
    if "Organizações" not in base.abas():
        return m
    for o in base.tabela("Organizações"):
        if not o.get("ID"):
            continue
        nomes = [o.get("Nome", "")] + re.split(r"[;\n]", o.get("Nomes na fonte", "") or "")
        for n in nomes:
            if n.strip():
                m.setdefault(chave(n), o["ID"].strip())
    return m


def regras_do_programa(baixar_pagina):
    """Regras gerais do PSG, só as que a página Bolsas de estudos diz letra a letra neste momento."""
    try:
        texto = texto_de_html(baixar_pagina(BOLSAS_PSG))
    except Exception:  # noqa: BLE001
        return {}, [], [], ""
    campos, provados, frases = {}, [], []
    for frase, coluna, valor, nome in REGRAS_PSG:
        if citacao_valida(frase, texto):
            campos[coluna] = valor
            provados.append(nome)
            frases.append(f"«{frase}»")
    # gratuidade: só uma frase da página que diga que não há custo (o nome do programa não chega; regra de 20/11/2026)
    frase_g = frase_de_gratuidade(texto)
    if not frase_g:
        try:
            if citacao_valida(FRASE_GRATUIDADE_PSG, texto_de_html(baixar_pagina(PAGINA_GRATUIDADE_PSG))):
                frase_g = FRASE_GRATUIDADE_PSG
        except Exception:  # noqa: BLE001
            print(f"  ? não foi possível ler {PAGINA_GRATUIDADE_PSG}")
    if frase_g:
        provados.append("gratuito")
        frases.append(f"gratuito: «{frase_g}» ({PAGINA_GRATUIDADE_PSG if frase_g == FRASE_GRATUIDADE_PSG else BOLSAS_PSG})")
    return campos, provados, frases, (REGRA_APERFEICOAMENTO if citacao_valida(REGRA_APERFEICOAMENTO, texto) else "")


def curso_novo(d, hoje, regras):
    campos_regra, provados, frases, regra_aperf = regras
    titulo = titulo_sem_codigo(d["titulo"])
    requisitos = []
    if "Renda máxima" in campos_regra:
        requisitos.append("Renda familiar de até 2 salários mínimos por pessoa")
    if regra_aperf and chave(titulo).startswith("aperfeicoamento"):
        requisitos.append("Curso de aperfeiçoamento: é preciso ter certificação profissional, registro na carteira "
                          "de trabalho, declaração de empresa ou autodeclaração")
        frases = frases + [f"«{regra_aperf}»"]
    falta = [] if provados else ["Não foi possível ler as regras do programa na página Bolsas de estudos."]
    if not d.get("descricao"):
        falta.append("A página da turma não tem descrição do curso.")
    return {
        "ID": id_curso(LISTA_PSG, titulo), "Estado": "Novo", "Título": titulo[:200], "Entidade": ENTIDADE_PSG,
        "Link": LISTA_PSG, "Local": "BR-CE", "Modalidade": "presencial", "País": "BR", "Região": "Ceará",
        "Cidade": "", "Descrição": d.get("descricao", "")[:600],
        "Origem da descrição": DESCRICAO_PAGINA if d.get("descricao") else "", "Necessidades": necessidades(d.get("area", ""), titulo),
        "Perfis": "todos", "Condição de acesso": "", "Requisitos": "; ".join(requisitos), "Certificado": "desconhecido",
        "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje,
        "Última verificação": hoje, "Origem": "turmas", "Notas": f"Área no Senac: {d.get('area', '')}".strip(),
        "Como me inscrever": "", "Nota da verificação": f"{hoje}: curso criado a partir de uma turma aberta na lista do Senac.",
        **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(frases)[:1500], "Campos comprovados": ", ".join(provados),
        "O que falta confirmar": " ".join(falta), "Antes de começar": "cpf" if "documentos" in provados else "",
        **campos_regra,
    }


def main(baixar_pagina=baixar_texto):
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    limite_falhas = 3
    corte_lista = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_PARA_TRAS)).isoformat()

    cursos_psg, ocultos = {}, set()
    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and "psg.ce.senac.br" in (r.get("Link") or "")]
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos_psg.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    unidades = mapa_unidades(base)
    # só as turmas do Senac Ceará: o separador Turmas também guarda as do Centec e do Senac Maranhão,
    # que têm o seu próprio leitor e não podem ser abertas como páginas do Senac PSG
    existentes = {(t.get("Link da turma") or "").rstrip("/"): t for t in base.tabela(ABA)
                  if "psg.ce.senac.br" in (t.get("Link da turma") or "")}

    # 1. percorrer a lista geral: turmas dos cursos da folha e turmas recentes de cursos que ainda não temos
    a_ver, pagina, lista_completa = {}, 1, False
    while pagina <= MAX_PAGINAS:
        url = LISTA_PSG if pagina == 1 else f"{LISTA_PSG}page/{pagina}/"
        try:
            caixas = ler_lista(baixar_pagina(url))
        except Exception as e:  # noqa: BLE001
            print(f"  lista, página {pagina}: não abriu ({type(e).__name__})")
            if pagina == 1:
                registar_pendencia(base, f"Senac Ceará (PSG): a lista de oportunidades não abriu ({type(e).__name__}).",
                                   "Se a página abre no seu navegador e se a lista mudou de endereço.", LISTA_PSG,
                                   origem="turmas.py")
            break
        if not caixas:
            lista_completa = pagina > 1
            break
        for c in caixas:
            k, link = chave(c["titulo"]), c["link"].rstrip("/")
            if k in ocultos or link in existentes:
                continue
            if not c["inicio"] or c["inicio"] >= corte_lista:
                a_ver[link] = cursos_psg.get(k, "")
        pagina += 1
        time.sleep(PAUSA)
    print(f"Lista do Senac PSG: {pagina - 1} páginas lidas, {len(a_ver)} turmas recentes por abrir.")

    # 2. turmas já conhecidas que ainda não encerraram há mais de 30 dias
    limite_antigas = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=30)).isoformat()
    for link, t in existentes.items():
        if t.get("Situação") != "Encerrada" or (t.get("Fim") or "9999") >= limite_antigas:
            a_ver[link] = t.get("Curso", "")

    regras = None
    novas, alteracoes, historico, cursos_novos = [], [], [], []
    por_abrir = set()
    estado_final = {}  # link → (curso, situação, visível)
    for link, t in existentes.items():
        estado_final[link] = (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado")
    for link, curso in a_ver.items():
        t = existentes.get(link)
        try:
            bruto = baixar_pagina(link + "/")
            d = ler_turma(bruto)
            if not d["titulo"] and not d["inicio"]:
                raise ValueError("página sem dados de turma")
            problemas = auditar(d, bruto)
        except Exception as e:  # noqa: BLE001
            if t:
                n = int(numero(t.get("Falhas seguidas"), 0)) + 1
                campos = {"Falhas seguidas": n, "Última verificação": hoje}
                if n >= limite_falhas and t.get("Situação") != "Encerrada":
                    campos["Situação"] = "Encerrada"
                    campos["Notas"] = f"A página da turma deixou de abrir ({n} vezes seguidas)."
                    historico.append(registo(t, "Turma", "página removida", campos["Notas"]))
                    estado_final[link] = (t.get("Curso", ""), "Encerrada", False)
                alteracoes.append((t["_linha"], campos))
            elif curso:
                por_abrir.add(curso)  # turma nova que não abriu: hoje não se conclui nada sobre este curso
            print(f"  ✗ {link}: {type(e).__name__}")
            time.sleep(PAUSA)
            continue
        campos = campos_da_turma(d, unidades)
        campos["Situação"] = situacao(d, hoje)
        campos["Última verificação"] = hoje
        campos["Falhas seguidas"] = 0
        campos["Auditoria"] = (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else \
            f"{hoje}: ok (duas leituras iguais; datas e horário coerentes)."
        if t:
            # a rotina só mexe no Estado que ela própria pôs: Publicado ↔ Rever. Oculto é de uma pessoa.
            if problemas and t.get("Estado") == "Publicado":
                campos["Estado"] = "Rever"
                historico.append(registo(t, "Auditoria", "Rever", campos["Auditoria"]))
            elif not problemas and t.get("Estado") == "Rever" and "não passou" in (t.get("Auditoria") or ""):
                campos["Estado"] = "Publicado"
            mudou = {k: v for k, v in campos.items() if str(t.get(k, "")) != str(v)}
            mudou.pop("Última verificação", None)
            if "Situação" in mudou or "Prazo de inscrição" in mudou or "Início" in mudou:
                historico.append(registo(t, "Turma", campos["Situação"],
                                         f"{campos['Unidade na fonte']}: prazo {campos['Prazo de inscrição'] or '—'}, "
                                         f"início {campos['Início'] or '—'}."))
            alteracoes.append((t["_linha"], campos))
            estado_final[link] = (t.get("Curso", ""), campos["Situação"],
                                  campos.get("Estado", t.get("Estado")) == "Publicado")
        elif campos["Situação"] != "Encerrada":
            k = chave(d["titulo"])
            if k in ocultos:
                continue
            curso = curso or cursos_psg.get(k, "")
            if not curso:
                # curso que ainda não está na folha: criar, para uma pessoa aprovar
                if regras is None:
                    regras = regras_do_programa(baixar_pagina)
                c = curso_novo(d, hoje, regras)
                cursos_novos.append(c)
                curso = cursos_psg[k] = c["ID"]
                print(f"  + curso novo [Novo]: {c['Título']}")
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link + "/", "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, campos["Situação"], not problemas)
        print(f"  {'+' if not t else '·'} {d['titulo'][:50]} | {d['unidade']} | prazo {d['prazo'] or '—'} | {campos['Situação']}")
        time.sleep(PAUSA)

    # 3. situação de cada curso do Senac PSG, a partir das suas turmas (só com a lista lida até ao fim)
    alteracoes_cursos = []
    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    # 3a. publicar sozinho o curso criado pelas turmas que tem turma aberta aprovada na auditoria
    def pode_publicar(c):
        return (c.get("Estado") == "Novo" and c.get("Origem") == "turmas" and not sim(c.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(c.get("ID", "")).strip(), [])
                and len((c.get("Descrição") or "").strip()) >= 30 and "renda" in (c.get("Campos comprovados") or ""))
    nota_pub = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria independente."
    publicados = set()
    for c in cursos_novos:
        if pode_publicar(c):
            c["Estado"], c["Nota da verificação"] = "Publicado", nota_pub
    for r in linhas_cursos:
        if pode_publicar(r):
            publicados.add(r["ID"])
            alteracoes_cursos.append((r["_linha"], {"Estado": "Publicado", "Nota da verificação": nota_pub}))
            historico.append(registo({"Curso": r["ID"], "Título na fonte": r.get("Título", ""), "Situação": "Novo"},
                                     "Auditoria", "Publicado", nota_pub))

    if lista_completa:
        for r in linhas_cursos:
            if (r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip()
                    or r["ID"].strip() in por_abrir):
                continue
            sits = por_curso.get(r["ID"].strip(), [])
            abertas = sits.count("Aberta")
            nova = "Aberto" if abertas else "Por confirmar" if "Por confirmar" in sits else "Encerrado"
            campos = {}
            # gratuidade escrita na página Bolsas de estudos do Senac Ceará (se não houver: «Gratuidade por confirmar»)
            if "gratuito" not in (r.get("Campos comprovados") or ""):
                if regras is None:
                    regras = regras_do_programa(baixar_pagina)
                frase_g = next((f for f in regras[2] if f.startswith("gratuito: «")), "")
                if frase_g:
                    campos["Campos comprovados"] = ", ".join(
                        [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()] + ["gratuito"])
                    campos["Evidência"] = (frase_g + " | " + (r.get("Evidência") or "")).strip(" |")[:1500]
            if nova != (r.get("Situação das inscrições") or ""):
                campos["Situação das inscrições"] = nova
                if r["ID"] not in publicados:
                    campos["Nota da verificação"] = (f"{hoje}: situação calculada pelas turmas do Senac "
                                                     f"({abertas} com inscrições abertas).")
                historico.append(registo({"Curso": r["ID"], "Título na fonte": r.get("Título", ""),
                                          "Situação": r.get("Situação das inscrições", "")}, "Turmas", nova,
                                         f"{abertas} turmas com inscrições abertas."))
            if abertas:
                campos["Última verificação"] = hoje
                aviso = "Há turma nova com inscrições abertas: decidir se o curso volta a Publicado."
                if r.get("Estado") == "Expirado" and aviso not in (r.get("O que falta confirmar") or ""):
                    campos["Mudança a rever"] = "TRUE"
                    campos["O que falta confirmar"] = (aviso + " " + (r.get("O que falta confirmar") or "")).strip()[:900]
            if campos:
                alteracoes_cursos.append((r["_linha"], campos))

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nTurmas: {len(novas)} novas, {len(alteracoes)} atualizadas. Cursos: {len(cursos_novos)} novos, "
          f"{len(alteracoes_cursos)} com situação atualizada.")
    return 0


def registo(t, tipo, resultado, notas):
    return {"Data e hora": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "ID do curso": t.get("Curso", ""), "Título": t.get("Título na fonte", ""), "Tipo de verificação": tipo,
            "Resultado": resultado, "Estado antes": t.get("Situação", ""), "Estado depois": resultado,
            "Notas": notas[:500]}


if __name__ == "__main__":
    sys.exit(main())
