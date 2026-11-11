"""Gera o site estático em docs/ a partir dos modelos em site/ e da configuração."""
import html
import os
import shutil
import sys
import time

from comum import caminho, config, gravar_json

PAGINAS = {
    "index.html": ("inicio", "{nome}: cursos grátis e notícias do setor social"),
    "cursos.html": ("cursos", "Cursos gratuitos online e presenciais | {nome}"),
    "noticias.html": ("noticias", "Notícias do setor social | {nome}"),
    "sobre.html": ("sobre", "Sobre | {nome}"),
}


def main():
    cfg = config()
    nome = html.escape(cfg["nome"])
    slogan = html.escape(cfg["slogan"])
    links = cfg.get("links", {})
    docs = caminho("docs")
    os.makedirs(os.path.join(docs, "dados"), exist_ok=True)

    whatsapp = links.get("canal_whatsapp") or ""
    if whatsapp:
        caminho_wa = ('<div class="caminho"><h3><a href="{}" rel="noopener">Canal no WhatsApp</a></h3>'
                      '<p>Receba os cursos novos todas as semanas no seu telemóvel ou celular.</p></div>').format(
            html.escape(whatsapp))
    else:
        caminho_wa = ('<div class="caminho breve"><h3>Canal no WhatsApp</h3>'
                      '<p>Em breve: os cursos novos todas as semanas no seu telemóvel ou celular.</p></div>')

    with open(caminho("site", "base.html"), encoding="utf-8") as f:
        base = f.read()
    versao = str(int(time.time()))
    for ficheiro, (pagina, titulo) in PAGINAS.items():
        with open(caminho("site", ficheiro), encoding="utf-8") as f:
            conteudo = f.read()
        conteudo = (conteudo.replace("{{NOME}}", nome)
                    .replace("{{PLAYLIST_ONGS}}", html.escape(links.get("playlist_ongs", "#")))
                    .replace("{{CAMINHO_WHATSAPP}}", caminho_wa))
        pagina_html = (base.replace("{{CONTEUDO}}", conteudo)
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
        "nome": cfg["nome"],
        "necessidades": cfg["cursos"]["necessidades"],
        "locais": cfg["cursos"]["locais"],
        "temas": cfg["noticias"]["temas"],
    })
    for ficheiro, vazio in (("noticias.json", {"atualizado": None, "dias": []}),
                            ("cursos.json", {"atualizado": None, "cursos": []})):
        if not os.path.exists(os.path.join(docs, "dados", ficheiro)):
            gravar_json(f"docs/dados/{ficheiro}", vazio)
    print("Site gerado em docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
