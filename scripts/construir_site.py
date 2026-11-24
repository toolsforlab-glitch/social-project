"""Gera o site estático em docs/ a partir da folha (só conteúdos visíveis e locais ativos).

Unidades e guias só saem com Estado = Publicado, dado pelas rotinas de auditoria ou por uma pessoa.
"""
import collections
import datetime
import html
import os
import re
import shutil
import sys
import time

from base import DESCRICAO_PAGINA, Base, gratuidade_comprovada, carregar_config, comprovado, curso_no_site, etiqueta_idade, etiqueta_publico, etiquetas_acessibilidade, sim, visivel
from comum import caminho, gravar_json
from paginas import destino_fixo, ler_destino

PAGINAS = {
    "index.html": ("inicio", "{nome}: cursos gratuitos e informação útil"),
    "cursos.html": ("cursos", "Cursos gratuitos online e presenciais | {nome}"),
    "noticias.html": ("noticias", "Notícias do setor social | {nome}"),
    "antes.html": ("antes", "Antes de começar: CPF, conta gov.br, CadÚnico e Jovem Aprendiz | {nome}"),
    "encaminhar.html": ("encaminhar", "Para quem encaminha pessoas: lista e fichas para imprimir | {nome}"),
    "numeros.html": ("numeros", "Os números do site: cursos gratuitos abertos hoje | {nome}"),
    "sobre.html": ("sobre", "Sobre | {nome}"),
}

# Dados sobre quem pode entrar e as barreiras; só saem para o site se estiverem comprovados
BARREIRAS = [("idade_minima", "Idade mínima", "idade"), ("idade_maxima", "Idade máxima", "idade máxima"), ("escolaridade", "Escolaridade mínima", "escolaridade"),
             ("renda", "Renda máxima", "renda"), ("cadunico", "Prioridade CadÚnico", "cadunico"),
             ("turnos", "Turno", "turno"), ("internet", "Precisa de internet", "internet"),
             ("ajuda", "Ajuda de custo ou transporte", "ajuda"), ("documentos", "Documentos pedidos", "documentos")]


# Fontes acompanhadas turma a turma por código (turmas.py e centec.py)
FONTES_COM_TURMAS = ("psg.ce.senac.br", "centec.org.br/cursos-formacao-inicial-continuada", "ma.senac.br/editais-psg",
                     "portal.ac.senac.br/psg", "fiema.org.br/editais/11", "psg.pi.senac.br",
                                                 "cursos-nivel-medio-senai-gratuidade")



def origem_descricao(r):
    """«pagina» quando a descrição foi copiada da página oficial; «resumo» quando foi reescrita (o site mostra
    «Em resumo:»). Linhas antigas sem a coluna: só os cursos do Senac Ceará (turmas.py) copiam o texto da página."""
    if not (r.get("Descrição") or "").strip():
        return ""
    origem = (r.get("Origem da descrição") or "").strip()
    if origem:
        return "pagina" if origem == DESCRICAO_PAGINA else "resumo"
    return "pagina" if r.get("Origem") == "turmas" and "psg.ce.senac.br" in (r.get("Link") or "") else "resumo"

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


def destino_do_curso(r):
    """Para onde leva o botão do curso: coluna «Destino do link» (verificar.py) ou a tabela das fontes."""
    url = (r.get("Página do curso") or "").strip() or r["Link"]
    d = ler_destino(r.get("Destino do link"))
    if d["tipo"]:
        d["nota"] = ""
        fixo = destino_fixo(url)
        if fixo and not d["conta"]:
            d["nota"] = fixo["nota"]
        return d
    fixo = destino_fixo(url, r.get("Título", ""))
    if fixo:
        return fixo
    if (r.get("Página do curso") or "").strip():
        return {"tipo": "curso", "conta": "", "nota": "", "procurar": "", "frase": ""}
    return None


def abertura_da_turma(t):
    """Primeiro dia das inscrições (AAAA-MM-DD), quando está em «Mais informações» («Inscrições de dd/mm/aaaa a …»)."""
    m = re.search(r"Inscrições de (\d{2})/(\d{2})/(\d{4})", t.get("Mais informações") or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def exportar_turmas(base, unidades, municipios):
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
            # inscrição que ainda não começou (23/11/2026): vai para o site só para o calendário da página de cursos
            "por_abrir": situacao == "Por abrir" and (t.get("Estado") or "").strip() == "Publicado",
            "abertura": abertura_da_turma(t),
            "situacao": situacao, "link": t["Link da turma"].strip(),
            "unidade": t.get("Unidade na fonte", ""), "cidade": municipios.get((t.get("Unidade") or "").strip()) or t.get("Cidade", ""),
            "local": unidade, "inicio": t.get("Início", ""), "fim": t.get("Fim", ""),
            "horario": t.get("Horário", ""), "dias": t.get("Dias", ""), "prazo": t.get("Prazo de inscrição", ""),
            "idade_minima": t.get("Idade mínima", ""), "escolaridade": t.get("Escolaridade", ""),
            "documentos": t.get("Documentos", ""), "local_texto": t.get("Local na fonte", ""),
            "titulo_fonte": t.get("Título na fonte", ""),
            # para onde leva o botão da turma (tabela DESTINOS_FONTES em paginas.py)
            "destino": destino_fixo(t["Link da turma"].strip(), t.get("Título na fonte", "")),
            "telefone": "" if (t.get("Modo de inscrição") or "").strip() else t.get("Mais informações", ""),
            # como se faz a inscrição: a coluna "Modo de inscrição" decide quando está preenchida; senão, pelo link
            "inscricao": (("online" if t["Modo de inscrição"].strip() == "online" else "presencial")
                          if (t.get("Modo de inscrição") or "").strip() else
                          "online" if "academy.centec.org.br" in t["Link da turma"] else
                          "presencial" if "centec.org.br" in t["Link da turma"] else "pagina"),
            "info": t.get("Mais informações", "") if (t.get("Modo de inscrição") or "").strip() else "",
            "verificado_em": (t.get("Última verificação") or "")[:10],
            "reserva": (t.get("Vagas reservadas") or "").strip(),
        })
    sem_destino = sorted({re.sub(r"^(https?://[^/]+).*", r"\1", x["link"]) for lst in por_curso.values()
                          for x in lst if x["visivel"] and not x["destino"]})
    if sem_destino:
        print("AVISO: turmas de fontes sem destino conhecido (acrescentar a DESTINOS_FONTES em paginas.py): "
              + ", ".join(sem_destino))
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
    # o município de uma unidade oficial pode aparecer mesmo antes de a unidade estar revista
    municipios = ({o["ID"].strip(): (o.get("Município") or "").strip() for o in base.tabela("Organizações") if o.get("ID")}
                  if "Organizações" in base.abas() else {})
    turmas_por_curso, turmas_recentes = exportar_turmas(base, unidades, municipios)

    cursos = []
    for r in base.tabela("Cursos"):
        if not curso_no_site(r, cfg) or r.get("Local") not in locais or not r.get("Link"):
            continue
        if r.get("Local") == "online" and pais_piloto and r.get("País") not in (pais_piloto, "Internacional"):
            continue
        # cursos com turmas acompanhadas: a situação vem das páginas das turmas, não da página geral
        acompanhadas = turmas_por_curso.get(r.get("ID", "").strip())
        if acompanhadas is None and turmas_recentes and any(f in r["Link"] for f in FONTES_COM_TURMAS):
            acompanhadas = []  # curso do Senac PSG sem nenhuma turma aberta na lista oficial
        turmas = [t for t in (acompanhadas or []) if t["visivel"]]
        futuras = [t for t in (acompanhadas or []) if t["por_abrir"]]
        if acompanhadas is not None and not turmas and not futuras:
            continue  # todas as turmas conhecidas já encerraram
        so_futuro = bool(futuras) and not turmas  # só aparece quando o calendário escolhe dias do período
        turmas = turmas + futuras
        cursos.append({
            "id": r.get("ID", ""), "titulo": r.get("Título", ""), "entidade": r.get("Entidade", ""),
            # o botão leva à página própria do curso quando ela foi encontrada e confirmada (paginas.py)
            "url": (r.get("Página do curso") or "").strip() or r["Link"],
            "pagina_propria": bool((r.get("Página do curso") or "").strip()), "local": r.get("Local", ""), "modalidade": r.get("Modalidade", ""),
            "destino": destino_do_curso(r),
            "pais": r.get("País", ""), "regiao": r.get("Região", ""), "cidade": r.get("Cidade", ""),
            "descricao": r.get("Descrição", ""), "descricao_origem": origem_descricao(r),
            # sem frase da página que diga que não há custo: o site mostra «Gratuidade por confirmar»
            "gratuidade_comprovada": gratuidade_comprovada(r), "necessidades": lista(r.get("Necessidades")),
            "exclusivo_para": r.get("Condição de acesso", ""), "requisitos": r.get("Requisitos", ""),
            # o certificado só aparece com prova (frase da página, ou GPT conferido por código) ou revisto por pessoa
            "certificado": r.get("Certificado", "") if comprovado(r, "certificado") else "",
            "certificado_comprovado": comprovado(r, "certificado"),
            # uma data só aparece se estiver comprovada na página ou confirmada por uma pessoa
            "inscricoes_ate": r.get("Inscrições até", "") if comprovado(r, "data") else "",
            "data_por_confirmar": bool(r.get("Inscrições até")) and not comprovado(r, "data"),
            "so_futuro": so_futuro,
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
        # etiquetas de vagas exclusivas ou reservadas: só com a frase da fonte (verificação ou edital)
        frases = re.findall(r"público: «(.+?)»", r.get("Evidência") or "") if comprovado(r, "público") else []
        frases += [t["reserva"] for t in turmas if t.get("reserva")]
        etiquetas = {}
        for f in frases:
            texto = etiqueta_publico(f)
            if texto and texto not in etiquetas:
                etiquetas[texto] = f
        cursos[-1]["etiquetas"] = [{"texto": k, "frase": v} for k, v in etiquetas.items()]
        # Como se distribuem as vagas (regra do responsável, 24/11/2026): sorteio e ordem de inscrição podem entrar, mas
        # quem procura tem de saber. Só com a frase da fonte (evidência ou informação da turma).
        fonte_vagas = " ".join([r.get("Evidência") or ""] + [str(t.get("info") or "") for t in turmas])
        cursos[-1]["vagas"] = ("sorteio" if re.search(r"\bsorte(?:io|ad[ao]s?|ar)\b", fonte_vagas, re.I)
                               else "ordem" if re.search(r"ordem (?:de|das) inscri[çc]|ordem de chegada|ordem cronol[óo]gica de inscri", fonte_vagas, re.I)
                               else "")
        # acessibilidade para pessoas com deficiência: só com a frase da fonte que nomeia o recurso
        acess = {}
        for f in (re.findall(r"acessibilidade: «(.+?)»", r.get("Evidência") or "")
                  if comprovado(r, "acessibilidade") else []):
            for texto in etiquetas_acessibilidade(f):
                acess.setdefault(texto, f)
        cursos[-1]["acessibilidade"] = [{"texto": k, "frase": v} for k, v in acess.items()]
        cursos[-1]["turnos"] = lista(cursos[-1]["turnos"])
        for campo in ("idade_minima", "idade_maxima"):
            try:
                cursos[-1][campo] = int(float(cursos[-1][campo])) if cursos[-1][campo] else None
            except ValueError:
                cursos[-1][campo] = None
        # curso só para uma faixa de idade (ex.: 15 a 29 anos, 60 anos ou mais): etiqueta com a frase da fonte
        idade = etiqueta_idade(cursos[-1]["idade_minima"], cursos[-1]["idade_maxima"])
        if idade and idade not in [e["texto"] for e in cursos[-1]["etiquetas"]]:
            frase = " ".join(re.findall(r"idade(?: máxima)?: «(.+?)»", r.get("Evidência") or ""))
            cursos[-1]["etiquetas"].append({"texto": idade, "frase": frase or idade})
    gravar_json("docs/dados/cursos.json", {"atualizado": time.strftime("%Y-%m-%dT%H:%M"), "cursos": cursos})

    temas = cfg["noticias"]["temas"]
    dias = collections.OrderedDict()
    noticias = sorted((r for r in base.tabela("Notícias") if visivel(r.get("Estado"), cfg) and r.get("Data")
                       and (r.get("Região") or "").strip() == "Brasil"),  # o site só mostra notícias do Brasil
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
    # Google Analytics: só o ID G-…; o site pede consentimento antes de carregar (ver app.js)
    ga = (cfg.get("google_analytics") or "").strip()
    if not re.fullmatch(r"G-[A-Z0-9]+", ga):
        ga = ""
    # «Como apoiar o site»: só aparece quando a chave Pix estiver em config.json («pix»)
    pix = html.escape((cfg.get("pix") or "").strip())
    bloco_apoiar = ('<h2 id="apoiar">Como apoiar o site</h2>\n'
                    "<p>O site é feito de forma voluntária, mas tem custos: a inteligência artificial que procura e confere os "
                    "cursos todos os dias é paga. Se puder, contribua com qualquer valor pelo Pix. Toda ajuda mantém o site no ar "
                    "e permite chegar a mais estados.</p>\n"
                    + ('<p class="pix">A chave Pix será publicada aqui em breve.</p>\n' if pix.upper() == "EM-BREVE" else
                       f'<p class="pix">Chave Pix: <strong>{pix}</strong> <button type="button" class="botao secundario pequeno" '
                       f'data-copiar="{pix}">Copiar a chave</button></p>\n')) if pix else ""
    form = (cfg.get("formulario_sugestoes") or {}).get("url", "")
    bloco_sugestoes = ('<h2 id="sugestoes">Sugestões e erros</h2>\n'
                       "<p>Achou um erro num curso, um link que não abre ou um curso que não é gratuito? Tem uma ideia para "
                       "melhorar o site ou conhece um curso gratuito que falta? Conte pelo formulário: não precisa se identificar.</p>\n"
                       f'<p><a class="botao secundario" href="{html.escape(form)}" target="_blank" rel="noopener">Mandar uma sugestão ou avisar um erro</a></p>\n') if form else ""
    for ficheiro, (pagina, titulo) in PAGINAS.items():
        with open(caminho("site", ficheiro), encoding="utf-8") as f:
            conteudo = f.read()
        conteudo = (conteudo.replace("{{NOME}}", nome)
                    .replace("{{PLAYLIST_ONGS}}", html.escape(links.get("playlist_ongs") or "#"))
                    .replace("{{CAMINHO_WHATSAPP}}", bloco_wa)
                    .replace("{{PARCEIROS}}", bloco_parceiros)
                    .replace("{{APOIAR}}", bloco_apoiar)
                    .replace("{{SUGESTOES}}", bloco_sugestoes))
        pagina_html = (modelo_base.replace("{{CONTEUDO}}", conteudo)
                       .replace("{{TITULO}}", titulo.format(nome=nome))
                       .replace("{{DESCRICAO}}", slogan)
                       .replace("{{NOME}}", nome).replace("{{SLOGAN}}", slogan)
                       .replace("{{PAGINA}}", pagina).replace("{{VERSAO}}", versao)
                       .replace("{{GA}}", ga)
                       .replace("{{LINK_APOIAR}}", ' · <a href="sobre.html#apoiar">Como apoiar o site</a>' if bloco_apoiar else "")
                       .replace("{{LINK_SUGESTOES}}", ' · <a href="sobre.html#sugestoes">Sugestões e erros</a>' if form else ""))
        for p in ("cursos", "antes", "encaminhar", "noticias", "numeros", "sobre"):
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
        "formulario": cfg.get("formulario_sugestoes") or {},
        "temas": cfg["noticias"]["temas"], "url_site": cfg.get("url_site", ""),
    })
    n_cursos, n_noticias = exportar_dados(base, cfg)
    print(f"Site gerado em docs/: {n_cursos} cursos e {n_noticias} notícias visíveis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
