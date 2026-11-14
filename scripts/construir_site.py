"""Gera o site estático em docs/ a partir da folha (só conteúdos visíveis e locais ativos)."""
import collections
import html
import os
import shutil
import sys
import time

from base import Base, carregar_config, visivel
from comum import caminho, gravar_json

PAGINAS = {
    "index.html": ("inicio", "{nome}: cursos gratuitos e informação útil"),
    "cursos.html": ("cursos", "Cursos gratuitos online e presenciais | {nome}"),
    "noticias.html": ("noticias", "Notícias do setor social | {nome}"),
    "sobre.html": ("sobre", "Sobre | {nome}"),
}


def lista(valor):
    return [x.strip() for x in str(valor or "").split(",") if x.strip()]


def passos(valor):
    linhas = [l.strip() for l in str(valor or "").splitlines() if l.strip()]
    return [l.split(". ", 1)[1] if l[:2].rstrip(".").isdigit() and ". " in l else l for l in linhas]


def exportar_dados(base, cfg):
    locais = {l["id"] for l in cfg["cursos"]["locais"]}
    piloto = cfg.get("territorio_piloto", "")
    pais_piloto = "BR" if piloto.startswith("BR") else "PT" if piloto == "PT" else ""
    cursos = []
    for r in base.tabela("Cursos"):
        if not visivel(r.get("Estado"), cfg) or r.get("Local") not in locais or not r.get("Link"):
            continue
        if r.get("Local") == "online" and pais_piloto and r.get("País") not in (pais_piloto, "Internacional"):
            continue
        cursos.append({
            "id": r.get("ID", ""), "titulo": r.get("Título", ""), "entidade": r.get("Entidade", ""),
            "url": r["Link"], "local": r.get("Local", ""), "modalidade": r.get("Modalidade", ""),
            "pais": r.get("País", ""), "regiao": r.get("Região", ""), "cidade": r.get("Cidade", ""),
            "descricao": r.get("Descrição", ""), "necessidades": lista(r.get("Necessidades")),
            "exclusivo_para": r.get("Condição de acesso", ""), "requisitos": r.get("Requisitos", ""),
            "certificado": r.get("Certificado", ""), "inscricoes_ate": r.get("Inscrições até", ""),
            "inicio": r.get("Início", ""), "duracao": r.get("Duração", ""),
            "primeiro_visto": r.get("Primeiro visto", ""), "como_me_inscrever": passos(r.get("Como me inscrever")),
        })
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
        for p in ("cursos", "noticias", "sobre"):
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
        "temas": cfg["noticias"]["temas"],
    })
    n_cursos, n_noticias = exportar_dados(base, cfg)
    print(f"Site gerado em docs/: {n_cursos} cursos e {n_noticias} notícias visíveis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
