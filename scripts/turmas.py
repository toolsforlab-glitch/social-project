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
4. grava tudo no separador "Turmas". Uma pessoa pode pôr Estado = Oculto para esconder uma turma.

Regras:
- Nada é deduzido nem resumido: cada valor vem do texto da página da turma (a coluna Evidência guarda-o).
- Uma turma só é ligada a uma unidade da folha quando o nome na página é igual ao Nome ou a um dos
  "Nomes na fonte" da organização. Se não houver correspondência exata, fica só o nome da página.
- Turmas novas só entram se ainda não estiverem encerradas.
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

from base import HISTORICO, Base, carregar_config, numero
from comum import baixar

ABA = "Turmas"
COLUNAS = ["ID", "Curso", "Estado", "Título na fonte", "Unidade na fonte", "Cidade", "Unidade", "Link da turma",
           "Link de matrícula", "Início", "Fim", "Horário", "Dias", "Carga horária", "Vagas", "Prazo de inscrição",
           "Idade mínima", "Escolaridade", "Documentos", "Mais informações", "Situação", "Primeiro visto",
           "Última verificação", "Falhas seguidas", "Evidência", "Notas"]
LISTA_PSG = "https://psg.ce.senac.br/oportunidades/"
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
            caixas.append({"link": html.unescape(link.group(1)), "titulo": limpo(titulo.group(1)), "infos": infos})
    return caixas


def ler_turma(pagina_html):
    """Dados da página de uma turma, copiados tal como aparecem."""
    d = {}
    m = re.search(r'(?s)<div class="content__title">\s*<h3>(.*?)</h3>', pagina_html)
    d["titulo"] = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<span class="unit_name">(.*?)</span>', pagina_html)
    unidade_cidade = limpo(m.group(1)) if m else ""
    m = re.search(r'(?s)<p class="item-content__info unit_name">(.*?)</p>', pagina_html)
    d["unidade"] = limpo(m.group(1)) if m else unidade_cidade.split("|")[0].strip()
    d["cidade"] = unidade_cidade.split("|", 1)[1].strip() if "|" in unidade_cidade else ""
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


def main(baixar_pagina=baixar_texto):
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    limite_falhas = 3

    cursos_psg = {}
    for r in base.tabela("Cursos"):
        if r.get("ID") and "psg.ce.senac.br" in (r.get("Link") or "") and r.get("Estado") != "Oculto":
            cursos_psg.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    if not cursos_psg:
        print("Nenhum curso do Senac PSG na folha.")
        return 0
    unidades = mapa_unidades(base)
    existentes = {(t.get("Link da turma") or "").rstrip("/"): t for t in base.tabela(ABA) if t.get("Link da turma")}

    # 1. descobrir turmas na lista geral
    encontradas, pagina = {}, 1
    while pagina <= MAX_PAGINAS:
        url = LISTA_PSG if pagina == 1 else f"{LISTA_PSG}page/{pagina}/"
        try:
            caixas = ler_lista(baixar_pagina(url))
        except Exception as e:  # noqa: BLE001
            print(f"  lista, página {pagina}: não abriu ({type(e).__name__})")
            break
        if not caixas:
            break
        for c in caixas:
            curso = cursos_psg.get(chave(c["titulo"]))
            if curso:
                encontradas[c["link"].rstrip("/")] = curso
        pagina += 1
        time.sleep(PAUSA)
    print(f"Lista do Senac PSG: {pagina - 1} páginas lidas, {len(encontradas)} turmas dos nossos cursos.")

    # 2. abrir cada turma (novas e as que ainda não encerraram há mais de 30 dias)
    limite_antigas = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=30)).isoformat()
    a_ver = dict(encontradas)
    for link, t in existentes.items():
        if t.get("Situação") != "Encerrada" or (t.get("Fim") or "9999") >= limite_antigas:
            a_ver.setdefault(link, t.get("Curso", ""))

    novas, alteracoes, historico = [], [], []
    for link, curso in a_ver.items():
        t = existentes.get(link)
        try:
            d = ler_turma(baixar_pagina(link + "/"))
            if not d["titulo"] and not d["inicio"]:
                raise ValueError("página sem dados de turma")
        except Exception as e:  # noqa: BLE001
            if t:
                n = int(numero(t.get("Falhas seguidas"), 0)) + 1
                campos = {"Falhas seguidas": n, "Última verificação": hoje}
                if n >= limite_falhas and t.get("Situação") != "Encerrada":
                    campos["Situação"] = "Encerrada"
                    campos["Notas"] = f"A página da turma deixou de abrir ({n} vezes seguidas)."
                    historico.append(registo(t, "Turma", "página removida", campos["Notas"]))
                alteracoes.append((t["_linha"], campos))
            print(f"  ✗ {link}: {type(e).__name__}")
            time.sleep(PAUSA)
            continue
        campos = campos_da_turma(d, unidades)
        campos["Situação"] = situacao(d, hoje)
        campos["Última verificação"] = hoje
        campos["Falhas seguidas"] = 0
        if t:
            mudou = {k: v for k, v in campos.items() if str(t.get(k, "")) != str(v)}
            mudou.pop("Última verificação", None)
            if "Situação" in mudou or "Prazo de inscrição" in mudou or "Início" in mudou:
                historico.append(registo(t, "Turma", campos["Situação"],
                                         f"{campos['Unidade na fonte']}: prazo {campos['Prazo de inscrição'] or '—'}, "
                                         f"início {campos['Início'] or '—'}."))
            alteracoes.append((t["_linha"], campos))
        elif campos["Situação"] != "Encerrada":
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Publicado", "Link da turma": link + "/",
                          "Primeiro visto": hoje, **campos})
        print(f"  {'+' if not t else '·'} {d['titulo'][:50]} | {d['unidade']} | prazo {d['prazo'] or '—'} | {campos['Situação']}")
        time.sleep(PAUSA)

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nTurmas: {len(novas)} novas, {len(alteracoes)} atualizadas.")
    return 0


def registo(t, tipo, resultado, notas):
    return {"Data e hora": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "ID do curso": t.get("Curso", ""), "Título": t.get("Título na fonte", ""), "Tipo de verificação": tipo,
            "Resultado": resultado, "Estado antes": t.get("Situação", ""), "Estado depois": resultado,
            "Notas": notas[:500]}


if __name__ == "__main__":
    sys.exit(main())
