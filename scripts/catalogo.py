"""Varre o catálogo inteiro das instituições com cursos sob demanda (aba "Catálogos"), não só os cursos que a pesquisa
semanal encontra (regra do responsável, 21/11/2026).

Cada linha ativa da aba "Catálogos" diz o domínio, a página da lista (com {n} no número da página, se houver várias)
e o padrão dos links dos cursos. Linhas criadas sozinhas (verificar.py, quando encontra um curso claramente sob
demanda de uma instituição que ainda não está na aba) chegam só com um link de exemplo: este script descobre a página
da lista e o padrão a partir desse link e grava-os na linha.

Para cada catálogo:
1. lê as páginas da lista (até MAX_PAGINAS; tenta ?pagina=N, ?page=N e /page/N) e junta os links dos cursos;
2. os links que ainda não estão na planilha (em nenhum Estado) passam pelo Claude, que escolhe só os úteis para o
   público do site (por número; título e começo do texto da página);
3. os escolhidos entram como Novo, no máximo MAX_NOVOS por catálogo e por rodada. A verificação semanal (verificar.py,
   que corre a seguir na mesma rotina) lê cada página, aplica todas as regras (gratuidade com frase; sob demanda só
   com frase da página; auditoria independente) e publica os que passam.

Os catálogos com leitor próprio (Fundação Bradesco: bradesco.py; Escola Virtual de Governo: evg.py; Sebrae: sebrae.py;
Senac, SENAI e Centec, com turmas: turmas.py, senac_ma.py, centec.py) não são lidos aqui: na aba, a Origem dessas linhas
começa por "leitor próprio".
"""
import hashlib
import re
import sys
import urllib.parse
import urllib.request
from html import unescape

from base import NECESSIDADES, necessidades_para_claude, VERIFICACAO_INICIAL, Base, carregar_config, hoje_iso, sim, texto_de_html
from comum import claude, custo_estimado, extrair_json

ABA = "Catálogos"
COM_LEITOR_PROPRIO = ("ev.org.br", "escolavirtual.gov.br", "loja.sebrae.com.br")
MAX_PAGINAS, MAX_LINKS, MAX_NOVOS = 20, 300, 40
SISTEMA = """Você escolhe cursos gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no Brasil a \
encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe páginas do catálogo de \
uma instituição (número, título, começo do texto). Escolha só as que são de UM curso (não listas, notícias, \
categorias ou páginas institucionais) e que servem a qualquer pessoa que quer aprender ou trabalhar (deixe de fora os \
só para professores, empresas, servidores públicos ou profissionais muito específicos). Para cada escolhido, indique \
as necessidades (ids da lista dada). Responda só com JSON entre <json></json>: [{"n": número, "necessidades": ["id"]}]."""


def obter(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto social; leitura de catálogo público)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def descobrir(exemplo):
    """A partir de um link de curso (ex.: https://site/cursos/excel), a lista (https://site/cursos?pagina={n})
    e o padrão dos links (^https://site/cursos/[^/?#]+$)."""
    u = urllib.parse.urlparse(exemplo)
    partes = [p for p in u.path.split("/") if p]
    if len(partes) < 2:
        return "", ""
    prefixo = "/" + "/".join(partes[:-1])
    base_url = f"{u.scheme}://{u.netloc}{prefixo}"
    return base_url + "?pagina={n}", "^" + re.escape(f"{u.scheme}://{u.netloc}{prefixo}/") + r"[^/?#]+/?$"


def paginas_da_lista(modelo):
    """Endereços a tentar para as páginas 1, 2, … de uma lista."""
    if "{n}" in modelo:
        yield from (modelo.format(n=n) for n in range(1, MAX_PAGINAS + 1))
        return
    yield modelo
    for n in range(2, MAX_PAGINAS + 1):
        yield f"{modelo}{'&' if '?' in modelo else '?'}page={n}"


def links_do_catalogo(lista, padrao):
    rx = re.compile(padrao, re.I)
    achados = []
    estilos = [lista] if "{n}" in lista else [lista.split("?")[0] + "?pagina={n}", lista.split("?")[0] + "?page={n}",
                                               lista.split("?")[0].rstrip("/") + "/page/{n}/"]
    for modelo in estilos:
        antes = len(achados)
        for url in paginas_da_lista(modelo):
            try:
                html, final = obter(url)
            except Exception:  # noqa: BLE001
                break
            novos = []
            for h in re.findall(r'href="([^"#]+)"', html):
                a = urllib.parse.urljoin(final, unescape(h)).split("#")[0]
                if rx.search(a) and a not in achados and a not in novos:
                    novos.append(a)
            if not novos:
                break
            achados += novos
            if len(achados) >= MAX_LINKS:
                return achados[:MAX_LINKS]
        if len(achados) > antes and "{n}" not in lista:
            break  # este estilo de paginação funcionou
    return achados


def resumo_pagina(url):
    html, _ = obter(url)
    m = re.search(r"<title>([^<]{3,300})</title>", html, flags=re.I)
    titulo = re.split(r"\s+[-|–]\s+", re.sub(r"\s+", " ", unescape(m.group(1))).strip())[0] if m else ""
    m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]{20,400})"', html, flags=re.I)
    inicio = unescape(m.group(1)) if m else re.sub(r"\s+", " ", texto_de_html(html.encode()))[:300]
    return titulo[:200], inicio[:300]


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    catalogos = base.tabela(ABA)
    cursos = base.tabela("Cursos")
    conhecidos = {(r.get(c) or "").strip().rstrip("/").lower() for r in cursos for c in ("Link", "Página do curso")}
    alt_cat, novos, custo = [], [], 0.0
    for cat in catalogos:
        dominio = (cat.get("Domínio") or "").strip().lower()
        if (not sim(cat.get("Ativo")) or not dominio or any(dominio.endswith(d) for d in COM_LEITOR_PROPRIO)
                or (cat.get("Origem") or "").strip().lower().startswith("leitor próprio")):
            continue
        lista, padrao = (cat.get("Página da lista") or "").strip(), (cat.get("Padrão dos links") or "").strip()
        campos_cat = {"Última leitura": hoje}
        if not (lista and padrao):
            exemplo = re.search(r"https?://\S+", cat.get("Notas") or "")
            lista, padrao = descobrir(exemplo.group(0).rstrip(".,);") if exemplo else "")
            if not (lista and padrao):
                print(f"  ! {dominio}: falta a página da lista e não há link de exemplo nas Notas")
                continue
            campos_cat.update({"Página da lista": lista, "Padrão dos links": padrao})
        links = links_do_catalogo(lista, padrao)
        campos_cat["Cursos encontrados"] = str(len(links))
        print(f"{dominio}: {len(links)} links de cursos no catálogo")
        por_ver = [l for l in links if l.rstrip("/").lower() not in conhecidos][:MAX_NOVOS * 3]
        lidos = []
        for l in por_ver:
            try:
                lidos.append((l, *resumo_pagina(l)))
            except Exception as e:  # noqa: BLE001
                print(f"  ! {l}: {e}")
        if lidos:
            lista_txt = "\n".join(f"{i} | {t} | {d[:220]}" for i, (_, t, d) in enumerate(lidos, 1))
            texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                                f"Necessidades (id = o que é): {necessidades_para_claude()}.\n\nPáginas (número | título | começo):\n{lista_txt}",
                                max_tokens=4000)
            custo += custo_estimado(uso, cfg["modelo_cursos"])
            escolhidos = [x for x in (extrair_json(texto) or []) if isinstance(x, dict) and str(x.get("n", "")).isdigit()
                          and 1 <= int(x["n"]) <= len(lidos)][:MAX_NOVOS]
            for x in escolhidos:
                link, titulo, _ = lidos[int(x["n"]) - 1]
                if not titulo:
                    continue
                novos.append({
                    "ID": "C-" + hashlib.sha1(f"catalogo|{link.rstrip('/').lower()}".encode()).hexdigest()[:8],
                    "Estado": "Novo", "Título": titulo, "Entidade": cat.get("Entidade") or dominio, "Link": link,
                    "Local": cat.get("Local") or "online", "Modalidade": "online" if (cat.get("Local") or "online") == "online" else "presencial",
                    "País": "BR", "Região": "", "Cidade": "", "Descrição": "", "Origem da descrição": "",
                    "Necessidades": ", ".join(n for n in (x.get("necessidades") or []) if n in NECESSIDADES),
                    "Perfis": "todos", "Condição de acesso": "", "Requisitos": "", "Certificado": "desconhecido",
                    "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "", "Primeiro visto": hoje,
                    "Última verificação": "", "Origem": "catálogo", "Notas": f"Do catálogo de {dominio}.",
                    "Como me inscrever": "", **VERIFICACAO_INICIAL,
                    "Nota da verificação": f"{hoje}: encontrado no catálogo de {dominio}; falta a verificação da página.",
                    "Situação das inscrições": "Por confirmar"})
                conhecidos.add(link.rstrip("/").lower())
            print(f"  {len(lidos)} páginas novas lidas; {len(escolhidos)} cursos escolhidos para verificar")
        alt_cat.append((cat["_linha"], campos_cat))
    base.atualizar(ABA, alt_cat)
    if novos:
        base.acrescentar("Cursos", novos)
    base.guardar()
    print(f"Catálogos: {len(alt_cat)} lidos, {len(novos)} cursos novos para a verificação. Custo estimado: {custo:.3f} USD")


if __name__ == "__main__":
    sys.exit(main())
