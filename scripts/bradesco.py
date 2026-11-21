"""Cursos on-line da Escola Virtual da Fundação Bradesco (ev.org.br), lidos do catálogo oficial, com prova por código.

O catálogo tem cerca de 70 cursos e trilhas, sob demanda e sem datas. Regras marcadas pelo responsável em Sites de
confiança: todos os cursos são gratuitos («Tudo gratuito», 15/11/2026) e um curso cuja página mostra o botão
«Quero me matricular» tem inscrições abertas (21/11/2026). O código confere, em cada leitura:

- que a página é do próprio curso (título da página) e mostra o botão de matrícula;
- a duração («Duração 16h») e a idade mínima («Idade mínima 16»), tal como estão escritas na página.

O Claude só escolhe quais cursos servem ao público do site (não os pensados para professores, empresas ou ONGs) e as
necessidades de cada um. Os que passam são publicados sozinhos; cursos já na planilha com «Mudança a rever» marcada
ou «Revisto por pessoa» não mudam de Estado. A verificação semanal não toca nestes cursos.
"""
import hashlib
import re
import sys
import urllib.parse
import urllib.request

from base import (DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida,
                  hoje_iso, registo_historico, sim, texto_de_html)
from comum import claude, custo_estimado, extrair_json

SITE = "https://www.ev.org.br"
LISTAS = ["/cursos?pagina={n}", "/trilhas-de-conhecimento?pagina={n}"]
ENTIDADE = "Fundação Bradesco (Escola Virtual)"
MARCA = "lida na página oficial, conferida por código"
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe cursos da \
Escola Virtual da Fundação Bradesco. Escolha os que servem a qualquer pessoa que quer aprender ou trabalhar (deixe de \
fora os pensados só para professores, gestores de empresas, ONGs ou profissionais de áreas muito específicas). Para \
cada escolhido, indique as necessidades (ids da lista dada). Responda só com JSON entre <json></json>: \
[{"url": "…", "necessidades": ["id", ...]}]."""


def obter(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto social; leitura do catálogo público)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def catalogo():
    urls = []
    for modelo in LISTAS:
        for n in range(1, 20):
            html = obter(SITE + modelo.format(n=n))
            novos = [SITE + h for h in re.findall(r'href="(/(?:cursos|trilhas-de-conhecimento)/[^"?#]+)"', html)]
            novos = [u for u in dict.fromkeys(novos) if u not in urls]
            if not novos:
                break
            urls += novos
    return urls


def chave(url):
    return urllib.parse.unquote(urllib.parse.urlparse(url).path).rstrip("/").lower()


def ler_curso(url, botao):
    html = obter(url)
    texto = texto_de_html(html.encode())
    m = re.search(r"<title>\s*(.*?)\s*-\s*Fundação Bradesco", html, flags=re.S | re.I)
    titulo = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    duracao = re.search(r"Duração\s*(\d+\s*h)", texto)
    idade = re.search(r"Idade m[íi]nima\s*(\d{1,2})", texto)
    descricao = ""
    m = re.search(r"Favoritar\s+(.{40,900}?)(?:Matricule-se|Quero me matricular|Conteúdo|Objetivo|$)", texto, flags=re.S)
    if m:
        frases = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", m.group(1)).strip())
        descricao = " ".join(f for f in frases[:2] if not re.search(r"matricule|inscreva", f, re.I))[:500]
    return {"url": url, "titulo": titulo, "aberto": bool(botao) and citacao_valida(botao, texto),
            "duracao": duracao.group(1).replace(" ", "") if duracao else "", "idade": idade.group(1) if idade else "",
            "descricao": descricao, "texto": texto}


def provas(d, botao):
    ev, comp = [], []
    if d["aberto"]:
        ev.append(f"situação: «{botao}» ({d['url']}; {MARCA}; regra de Sites de confiança marcada por uma pessoa)")
        comp.append("situação")
    ev.append("gratuito: «entidade marcada como “Tudo gratuito” em Sites de confiança, por uma pessoa»")
    comp.append("gratuito")
    if d["idade"]:
        ev.append(f"idade: «Idade mínima {d['idade']}» ({d['url']}; {MARCA})")
        comp.append("idade")
    return " | ".join(ev)[:1500], comp


def main():
    base = Base()
    cfg = carregar_config(base)
    botao = cfg["cursos"].get("botao_inscricao", {}).get("ev.org.br", "")
    gratuito = "ev.org.br" in cfg["cursos"].get("dominios_gratuitos", set())
    if not (botao and gratuito):
        print("Sites de confiança: falta a regra «Tudo gratuito» ou o botão de inscrição do ev.org.br; nada a fazer.")
        return
    hoje = hoje_iso()
    urls = catalogo()
    print(f"Catálogo da Fundação Bradesco: {len(urls)} cursos e trilhas.")
    linhas = base.tabela("Cursos")
    por_chave = {}
    for r in linhas:
        for l in (r.get("Link", ""), r.get("Página do curso", "")):
            if "ev.org.br" in (l or ""):
                por_chave.setdefault(chave(l), r)
    lidos, alteracoes, historico = {}, [], []
    for u in urls:
        try:
            lidos[u] = ler_curso(u, botao)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {u}: {e}")
    # 1. cursos já na planilha
    for u, d in lidos.items():
        r = por_chave.get(chave(u))
        if not r or r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        evid, comp = provas(d, botao)
        outros = [c.strip() for c in (r.get("Campos comprovados") or "").split(",")
                  if c.strip() and c.strip() not in ("situação", "gratuito", "idade")]
        campos = {"Situação das inscrições": "Aberto" if d["aberto"] else "Por confirmar", "Evidência": evid,
                  "Campos comprovados": ", ".join(outros + comp), "Página do curso": u, "Última verificação": hoje,
                  "Verificar automaticamente": "FALSE", "Destino do link": ""}
        if d["duracao"] and not r.get("Duração"):
            campos["Duração"] = d["duracao"].replace("h", " horas")
        if not (r.get("Descrição") or "").strip() and d["descricao"]:
            campos["Descrição"], campos["Origem da descrição"] = d["descricao"], DESCRICAO_PAGINA
        if r.get("Estado") == "Novo" and d["aberto"] and not sim(r.get("Mudança a rever")):
            campos["Estado"] = "Publicado"
            campos["Nota da verificação"] = (f"{hoje}: publicado automaticamente: página própria do curso com o botão "
                                             f"“{botao}” e gratuidade pela regra da entidade (marcadas por uma pessoa).")
            historico.append(registo_historico(r, "Catálogo Fundação Bradesco", "Publicado", campos, u))
        alteracoes.append((r["_linha"], campos))
        print(f"  = {r['Título'][:55]} | {'Aberto' if d['aberto'] else 'sem botão'}"
              + (" | publicado" if campos.get("Estado") == "Publicado" else "")
              + (" | Mudança a rever marcada" if sim(r.get("Mudança a rever")) else ""))
    # 2. cursos novos: o Claude escolhe os úteis para o público do site
    novos_lidos = [d for u, d in lidos.items() if chave(u) not in por_chave and d["aberto"] and d["titulo"]]
    novos, custo = [], 0.0
    if novos_lidos:
        lista = "\n".join(f"{d['url']} | {d['titulo']} | {d['descricao'][:200]}" for d in novos_lidos)
        texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                            f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nCursos (url | título | descrição):\n{lista}",
                            max_tokens=5000)
        custo += custo_estimado(uso, cfg["modelo_cursos"])
        escolha = {x.get("url"): x for x in (extrair_json(texto) or []) if isinstance(x, dict)}
        print(f"Cursos novos com botão de matrícula: {len(novos_lidos)}; o Claude escolheu {len(escolha)}.")
        for d in novos_lidos:
            x = escolha.get(d["url"])
            if not x:
                continue
            evid, comp = provas(d, botao)
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            novos.append({
                "ID": "C-" + hashlib.sha1(f"bradesco|{chave(d['url'])}".encode()).hexdigest()[:8],
                "Estado": "Publicado", "Título": d["titulo"][:200], "Entidade": ENTIDADE, "Link": d["url"],
                "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": d["descricao"], "Origem da descrição": DESCRICAO_PAGINA if d["descricao"] else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "",
                "Requisitos": f"Ter {d['idade']} anos ou mais" if d["idade"] else "", "Certificado": "desconhecido",
                "Inscrições até": "", "Início": "", "Duração": d["duracao"].replace("h", " horas") if d["duracao"] else "",
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "bradesco",
                "Notas": "", "Como me inscrever": "", **VERIFICACAO_INICIAL,
                "Nota da verificação": (f"{hoje}: publicado automaticamente: página própria do curso com o botão "
                                        f"“{botao}” e gratuidade pela regra da entidade (marcadas por uma pessoa)."),
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": ", ".join(comp), "Página do curso": d["url"], "Idade mínima": d["idade"]})
            print(f"  + {d['titulo'][:60]} | {d['duracao']}")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Fundação Bradesco: {len(alteracoes)} cursos atualizados, {len(novos)} novos publicados. "
          f"Custo estimado: {custo:.3f} USD")


if __name__ == "__main__":
    sys.exit(main())
