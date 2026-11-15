"""Gera o site estático em docs/ a partir da folha (só conteúdos visíveis e locais ativos)."""
import collections
import datetime
import html
import os
import shutil
import sys
import time

from base import Base, carregar_config, comprovado, curso_no_site, sim, visivel
from comum import caminho, gravar_json

PAGINAS = {
    "index.html": ("inicio", "{nome}: cursos gratuitos e informação útil"),
    "cursos.html": ("cursos", "Cursos gratuitos online e presenciais | {nome}"),
    "noticias.html": ("noticias", "Notícias do setor social | {nome}"),
    "antes.html": ("antes", "Antes de começar: CPF, conta gov.br e CadÚnico | {nome}"),
    "encaminhar.html": ("encaminhar", "Para quem encaminha pessoas: lista e fichas para imprimir | {nome}"),
    "sobre.html": ("sobre", "Sobre | {nome}"),
}

# Dados sobre quem pode entrar e as barreiras; só saem para o site se estiverem comprovados
BARREIRAS = [("idade_minima", "Idade mínima", "idade"), ("escolaridade", "Escolaridade mínima", "escolaridade"),
             ("renda", "Renda máxima", "renda"), ("cadunico", "Prioridade CadÚnico", "cadunico"),
             ("turnos", "Turno", "turno"), ("internet", "Precisa de internet", "internet"),
             ("ajuda", "Ajuda de custo ou transporte", "ajuda"), ("documentos", "Documentos pedidos", "documentos")]


def valor_comprovado(r, coluna, prova):
    v = str(r.get(coluna) or "").strip()
    if not v or v == "Não indicado" or not comprovado(r, prova):
        return ""
    return v


def lista(valor):
    return [x.strip() for x in str(valor or "").split(",") if x.strip()]


def passos(valor):
    linhas = [l.strip() for l in str(valor or "").splitlines() if l.strip()]
    return [l.split(". ", 1)[1] if l[:2].rstrip(".").isdigit() and ". " in l else l for l in linhas]


def exportar_turmas(base, unidades):
    """Turmas por curso, lidas das páginas oficiais por turmas.py. Só saem as que não encerraram.

    Devolve ({ID do curso: [turmas]}, leitura_recente). O dicionário inclui os cursos com turmas na folha,
    mesmo encerradas, para se saber que o curso é acompanhado por turma. leitura_recente indica que a rotina
    das turmas correu nos últimos 3 dias; só então um curso do Senac PSG sem turmas abertas sai do site.
    """
    por_curso = {}
    if "Turmas" not in base.abas():
        return por_curso, False
    linhas = base.tabela("Turmas")
    # a leitura das turmas só conta como completa se correu há pouco tempo
    recente = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    leitura_recente = any((t.get("Última verificação") or "") >= recente for t in linhas)
    for t in linhas:
        curso = (t.get("Curso") or "").strip()
        if not curso or not t.get("Link da turma"):
            continue
        situacao = (t.get("Situação") or "").strip()
        unidade = unidades.get((t.get("Unidade") or "").strip())
        por_curso.setdefault(curso, []).append({
            "visivel": situacao in ("Aberta", "Por confirmar") and (t.get("Estado") or "").strip() == "Publicado",
            "situacao": situacao, "link": t["Link da turma"].strip(),
            "unidade": t.get("Unidade na fonte", ""), "cidade": (unidade or {}).get("municipio") or t.get("Cidade", ""),
            "local": unidade, "inicio": t.get("Início", ""), "fim": t.get("Fim", ""),
            "horario": t.get("Horário", ""), "dias": t.get("Dias", ""), "prazo": t.get("Prazo de inscrição", ""),
            "idade_minima": t.get("Idade mínima", ""), "escolaridade": t.get("Escolaridade", ""),
            "documentos": t.get("Documentos", ""), "verificado_em": (t.get("Última verificação") or "")[:10],
        })
    for lst in por_curso.values():
        lst.sort(key=lambda t: (t["prazo"] or t["inicio"] or "9999", t["unidade"]))
    return por_curso, leitura_recente


def exportar_dados(base, cfg):
    locais = {l["id"] for l in cfg["cursos"]["locais"]}
    piloto = cfg.get("territorio_piloto", "")
    pais_piloto = "BR" if piloto.startswith("BR") else "PT" if piloto == "PT" else ""
    # Unidades onde as pessoas se inscrevem (só as publicadas; o contacto interno nunca sai da folha)
    unidades = {}
    if "Organizações" in base.abas():
        for o in base.tabela("Organizações"):
            if (o.get("Estado") or "").strip() == "Publicado" and o.get("ID"):
                # cada dado só sai para o site se estiver comprovado na fonte ou revisto por uma pessoa
                unidades[o["ID"].strip()] = {k: (o.get(c, "") if prova is None or comprovado(o, prova) else "")
                                             for k, c, prova in (
                    ("nome", "Nome", None), ("municipio", "Município", None), ("site", "Site", None),
                    ("bairro", "Bairro", "bairro"), ("morada", "Morada", "morada"),
                    ("telefone", "Telefone", "telefone"), ("whatsapp", "WhatsApp", "whatsapp"),
                    ("horario", "Horário de atendimento", "horário"), ("o_que_levar", "O que levar", "o que levar"))}
    # Guias "Antes de começar" publicados
    guias = []
    if "Antes de começar" in base.abas():
        for g in base.tabela("Antes de começar"):
            if (g.get("Estado") or "").strip() == "Publicado" and g.get("ID"):
                guias.append({"id": g["ID"].strip(), "titulo": g.get("Título", ""), "para_que": g.get("Para que serve", ""),
                              "passos": passos(g.get("Passos")), "onde": g.get("Onde fazer", ""),
                              "custo": g.get("Quanto custa", ""), "tempo": g.get("Quanto tempo leva", ""),
                              "fonte": g.get("Fonte", ""),
                              "verificado_em": (g.get("Revisto por pessoa") or g.get("Última verificação") or "")[:10]})
    gravar_json("docs/dados/guias.json", {"atualizado": time.strftime("%Y-%m-%dT%H:%M"), "guias": guias})
    ids_guias = {g["id"] for g in guias}
    turmas_por_curso, turmas_recentes = exportar_turmas(base, unidades)

    cursos = []
    for r in base.tabela("Cursos"):
        if not curso_no_site(r, cfg) or r.get("Local") not in locais or not r.get("Link"):
            continue
        if r.get("Local") == "online" and pais_piloto and r.get("País") not in (pais_piloto, "Internacional"):
            continue
        # cursos com turmas acompanhadas: a situação vem das páginas das turmas, não da página geral
        acompanhadas = turmas_por_curso.get(r.get("ID", "").strip())
        if acompanhadas is None and turmas_recentes and "psg.ce.senac.br" in r["Link"]:
            acompanhadas = []  # curso do Senac PSG sem nenhuma turma aberta na lista oficial
        turmas = [t for t in (acompanhadas or []) if t["visivel"]]
        if acompanhadas is not None and not turmas:
            continue  # todas as turmas conhecidas já encerraram
        cursos.append({
            "id": r.get("ID", ""), "titulo": r.get("Título", ""), "entidade": r.get("Entidade", ""),
            # o botão leva à página própria do curso quando ela foi encontrada e confirmada (paginas.py)
            "url": (r.get("Página do curso") or "").strip() or r["Link"],
            "pagina_propria": bool((r.get("Página do curso") or "").strip()), "local": r.get("Local", ""), "modalidade": r.get("Modalidade", ""),
            "pais": r.get("País", ""), "regiao": r.get("Região", ""), "cidade": r.get("Cidade", ""),
            "descricao": r.get("Descrição", ""), "necessidades": lista(r.get("Necessidades")),
            "exclusivo_para": r.get("Condição de acesso", ""), "requisitos": r.get("Requisitos", ""),
            "certificado": r.get("Certificado", ""),
            # uma data só aparece se estiver comprovada na página ou confirmada por uma pessoa
            "inscricoes_ate": r.get("Inscrições até", "") if comprovado(r, "data") else "",
            "data_por_confirmar": bool(r.get("Inscrições até")) and not comprovado(r, "data"),
            "situacao": ("Aberto" if any(t["situacao"] == "Aberta" for t in turmas) else "Por confirmar") if turmas
                        else (r.get("Situação das inscrições", "") or "Por confirmar"),
            "turmas": [{k: v for k, v in t.items() if k != "visivel"} for t in turmas],
            "em_revisao": sim(r.get("Mudança a rever")),
            "onde_inscrever": [unidades[i] for i in lista(r.get("Onde se inscrever")) if i in unidades],
            "verificado_em": (r.get("Revisto por pessoa") or (r.get("Última verificação") if r.get("Nota da verificação") else "") or "")[:10],
            "inicio": r.get("Início", ""), "duracao": r.get("Duração", ""),
            "primeiro_visto": r.get("Primeiro visto", ""), "como_me_inscrever": passos(r.get("Como me inscrever")),
            "antes": [i for i in lista(r.get("Antes de começar")) if i in ids_guias],
            **{k: valor_comprovado(r, c, p) for k, c, p in BARREIRAS},
        })
        cursos[-1]["turnos"] = lista(cursos[-1]["turnos"])
        try:
            cursos[-1]["idade_minima"] = int(float(cursos[-1]["idade_minima"])) if cursos[-1]["idade_minima"] else None
        except ValueError:
            cursos[-1]["idade_minima"] = None
    gravar_json("docs/dados/cursos.json", {"atualizado": time.strftime("%Y-%m-%dT%H:%M"), "cursos": cursos})

    temas = cfg["noticias"]["temas"]
    dias = collections.OrderedDict()
    noticias = sorted((r for r in base.tabela("Notícias") if visivel(r.get("Estado"), cfg) and r.get("Data")),
                      key=lambda r: r["Data"], reverse=True)
    for r in noticias:
        dias.setdefault(r["Data"][:10], []).append({
            "titulo": r.get("Título", ""), "resumo": r.get("Resumo", ""),
            "tema": r.get("Tema") if r.get("Tema") in temas else None, "regiao": r.get("Região", ""),
            "fonte": r.get("Fonte", ""), "idioma_original": r.get("Idioma original", ""), "link": r.get("Link", ""),
        })
    lista_dias = [{"data": d, "itens": i} for d, i in list(dias.items())[: cfg["noticias"]["dias_guardados"]]]
    gravar_json("docs/dados/noticias.json", {"atualizado": time.strftime("%Y-%m-%dT%H:%M"), "dias": lista_dias})
    return len(cursos), sum(len(d["itens"]) for d in lista_dias)


def main():
    base = Base()
    cfg = carregar_config(base)
    nome = html.escape(cfg["nome"])
    slogan = html.escape(cfg["slogan"])
    links = cfg.get("links", {})
    docs = caminho("docs")
    os.makedirs(os.path.join(docs, "dados"), exist_ok=True)

    if links.get("canal_whatsapp"):
        bloco_wa = ('<div class="caminho"><h3><a href="{}" rel="noopener">Canal no WhatsApp</a></h3>'
                    '<p>Receba os cursos novos toda semana no seu celular.</p></div>').format(html.escape(links["canal_whatsapp"]))
    else:
        bloco_wa = ('<div class="caminho breve"><h3>Canal no WhatsApp</h3>'
                    '<p>Em breve: os cursos novos toda semana no seu celular.</p></div>')
    if links.get("formulario_parceiros"):
        bloco_parceiros = ('<div class="aviso"><p><strong>Sua organização oferece cursos gratuitos?</strong> '
                           '<a href="{}" rel="noopener">Envie o curso aqui</a> e ele pode aparecer nesta lista.</p></div>'
                           ).format(html.escape(links["formulario_parceiros"]))
    else:
        bloco_parceiros = ""

    with open(caminho("site", "base.html"), encoding="utf-8") as f:
        modelo_base = f.read()
    versao = str(int(time.time()))
    for ficheiro, (pagina, titulo) in PAGINAS.items():
        with open(caminho("site", ficheiro), encoding="utf-8") as f:
            conteudo = f.read()
        conteudo = (conteudo.replace("{{NOME}}", nome)
                    .replace("{{PLAYLIST_ONGS}}", html.escape(links.get("playlist_ongs") or "#"))
                    .replace("{{CAMINHO_WHATSAPP}}", bloco_wa)
                    .replace("{{PARCEIROS}}", bloco_parceiros))
        pagina_html = (modelo_base.replace("{{CONTEUDO}}", conteudo)
                       .replace("{{TITULO}}", titulo.format(nome=nome))
                       .replace("{{DESCRICAO}}", slogan)
                       .replace("{{NOME}}", nome).replace("{{SLOGAN}}", slogan)
                       .replace("{{PAGINA}}", pagina).replace("{{VERSAO}}", versao))
        for p in ("cursos", "antes", "encaminhar", "noticias", "sobre"):
            pagina_html = pagina_html.replace("{{ATUAL_%s}}" % p.upper(),
                                              ' aria-current="page"' if p == pagina else "")
        with open(os.path.join(docs, ficheiro), "w", encoding="utf-8") as f:
            f.write(pagina_html)

    for estatico in ("estilo.css", "app.js"):
        shutil.copyfile(caminho("site", estatico), os.path.join(docs, estatico))
    open(os.path.join(docs, ".nojekyll"), "w").close()

    gravar_json("docs/dados/site.json", {
        "nome": cfg["nome"], "territorio_piloto": cfg.get("territorio_piloto", ""),
        "necessidades": cfg["cursos"]["necessidades"], "locais": cfg["cursos"]["locais"],
        "temas": cfg["noticias"]["temas"], "url_site": cfg.get("url_site", ""),
    })
    n_cursos, n_noticias = exportar_dados(base, cfg)
    print(f"Site gerado em docs/: {n_cursos} cursos e {n_noticias} notícias visíveis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
