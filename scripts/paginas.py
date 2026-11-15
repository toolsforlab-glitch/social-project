"""Encontrar a página própria de um curso, sem Claude.

Muitas fontes dão primeiro uma página geral (lista de cursos, página do campus, pesquisa de ofertas).
Quem clica no site tem de chegar à página DO CURSO, onde está a inscrição. Regras, iguais para todas as fontes:

- Uma página só conta como "página do curso" se o título do curso aparecer no título da página (<title>)
  ou no cabeçalho principal (<h1>; ou <h3> do título, no caso do Senac). Verificado por código.
- Se o link que temos já é a página do curso, fica esse.
- Se é uma página geral, procuram-se nela as ligações cujo texto contém o título do curso (ou cujo endereço
  contém o título escrito como nos endereços). Só se aceitam ligações para sites de confiança.
- Abre-se cada candidata e confirma-se que é mesmo a página do curso. Se ficar exatamente uma, é essa.
  Se houver várias (por exemplo, várias turmas), não se escolhe nenhuma: isso é tratado por turmas.
- Se nada se confirmar, a página do curso fica vazia e o site diz "Procurar este curso na página oficial".
"""
import html as _html
import re
import unicodedata
import urllib.parse

from comum import baixar, dominio_permitido

MAX_CANDIDATAS = 4


def chave(t):
    t = re.sub(r"(?s)<[^>]+>", " ", t or "")
    t = _html.unescape(t)
    t = re.sub(r"^\s*\d{4}\.\d+\.\d+\s*[–—-]\s*", "", t)  # código de turma do Senac
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def slug(t):
    return chave(t).replace(" ", "-")


def titulo_curto(titulo):
    """Tira o que acrescentamos ao título (ex.: "em Aracati", parênteses) para comparar com a fonte."""
    t = re.sub(r"\s*\([^)]*\)", "", titulo or "")
    t = re.sub(r"\s+(em|no|na)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ ]*$", "", t)
    return t.strip() or titulo


def cabecalhos(bruto):
    partes = re.findall(r"(?is)<title[^>]*>(.*?)</title>", bruto)[:1]
    partes += re.findall(r"(?is)<h1[^>]*>(.*?)</h1>", bruto)[:2]
    partes += re.findall(r'(?is)<div class="content__title">\s*<h3>(.*?)</h3>', bruto)[:1]
    return [chave(p) for p in partes if chave(p)]


def e_pagina_do_curso(bruto, titulo):
    alvo = chave(titulo_curto(titulo))
    if len(alvo) < 6:
        return False
    return any(alvo in c for c in cabecalhos(bruto))


def ligacoes(bruto, base_url):
    for href, texto in re.findall(r'(?is)<a\s[^>]*href="([^"#][^"]*)"[^>]*>(.*?)</a>', bruto):
        href = _html.unescape(href).strip()
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "whatsapp:")):
            continue
        yield urllib.parse.urljoin(base_url, href), chave(texto)


def candidatas(bruto, base_url, titulo):
    alvo, alvo_slug = chave(titulo_curto(titulo)), slug(titulo_curto(titulo))
    vistas, escolhidas = [], []
    for url, texto in ligacoes(bruto, base_url):
        sem_frag = url.split("#")[0].rstrip("/")
        if sem_frag == base_url.split("#")[0].rstrip("/") or sem_frag in vistas:
            continue
        caminho = urllib.parse.urlparse(url).path.lower()
        if (alvo and alvo in texto and len(texto) <= len(alvo) * 2 + 20) or (alvo_slug and alvo_slug in caminho):
            vistas.append(sem_frag)
            escolhidas.append(url.split("#")[0])
    return escolhidas


def encontrar_pagina(link, bruto, titulo, dominios, abrir=None):
    """Devolve (página do curso ou "", nota curta)."""
    abrir = abrir or (lambda u: baixar(u, timeout=30).decode("utf-8", "replace"))
    if isinstance(bruto, bytes):
        bruto = bruto.decode("utf-8", "replace")
    if e_pagina_do_curso(bruto, titulo):
        return link, "o link já é a página do curso"
    cands = [u for u in candidatas(bruto, link, titulo) if not dominios or dominio_permitido(u, dominios)]
    if not cands:
        return "", "o link leva a uma página geral e não tem ligação para a página deste curso"
    confirmadas = []
    for u in cands[:MAX_CANDIDATAS]:
        try:
            if e_pagina_do_curso(abrir(u), titulo):
                confirmadas.append(u)
        except Exception:  # noqa: BLE001
            continue
    if len(confirmadas) == 1:
        return confirmadas[0], "página do curso encontrada a partir da página geral"
    if len(confirmadas) > 1:
        return "", f"a página geral tem {len(confirmadas)} páginas para este curso (várias turmas)"
    return "", "o link leva a uma página geral e a página deste curso não foi confirmada"
