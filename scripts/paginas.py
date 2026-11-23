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


# ------------------------------------------------------------------ destino do link
# Regra do projeto: quem clica num botão do site tem de saber que página vai abrir. Cada link é classificado
# e o site escreve o botão e uma nota a partir desta classificação (ver construir_site.py e app.js):
#   curso      a página do próprio curso ou turma (o título do curso está no título ou cabeçalho da página)
#   acesso     uma página de entrada (login): é preciso entrar com uma conta antes de ver a inscrição
#   lista      uma lista geral onde o curso aparece: o site diz o nome exato a procurar
#   pdf        um documento PDF (edital): o site diz onde estão os cursos
#   formulario um formulário de inscrição (Google Forms, Microsoft Forms, etc.)
#   inicio     a página inicial do site: o site diz o nome a procurar
#   geral      uma página que não fala deste curso: não serve, o curso não é publicado sozinho
FORMULARIOS = ("docs.google.com/forms", "forms.gle", "forms.office.com", "forms.microsoft.com", "typeform.com",
               "jotform.com", "survio.com", "pesquisa.", "formulario")
ACESSO_URL = r"/(login|signin|sign-in|sign_in|entrar|acessar|acesso|auth|sso|oauth|cas/login)(/|\.php|\?|$)"


def destino_do_link(url_final, bruto, titulo):
    """Devolve (tipo, nome a procurar na página ou "")."""
    if isinstance(bruto, bytes):
        if bruto[:4] == b"%PDF":
            return "pdf", ""
        bruto = bruto.decode("utf-8", "replace")
    url = (url_final or "").lower()
    if re.search(r"\.pdf($|[?#])", url):
        return "pdf", ""
    if any(f in url for f in FORMULARIOS):
        return "formulario", ""
    caminho = urllib.parse.urlparse(url).path
    so_texto = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", bruto)
    pede_senha = re.search(r'(?i)<input[^>]+type=["\']?password', bruto) and len(chave(so_texto)) < 4000
    if re.search(ACESSO_URL, caminho) or pede_senha:
        return "acesso", ""
    if e_pagina_do_curso(bruto, titulo):
        return "curso", ""
    alvo = chave(titulo_curto(titulo))
    if len(alvo) >= 6:
        # o nome tal como está escrito na página (texto de uma ligação ou de um título que contém o curso)
        for bloco in re.findall(r"(?is)<(?:a|h[1-6]|strong|b)\b[^>]*>(.*?)</(?:a|h[1-6]|strong|b)>", so_texto):
            texto = re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", bloco))).strip()
            if alvo in chave(texto) and len(texto) <= 200:
                return ("inicio" if caminho in ("", "/") else "lista"), texto
        if alvo in chave(so_texto):
            return ("inicio" if caminho in ("", "/") else "lista"), titulo_curto(titulo)
    return "geral", ""


def destino_texto(tipo, procurar="", conta="", frase=""):
    """Forma escrita na coluna «Destino do link» (legível na folha e lida de volta por ler_destino)."""
    partes = [tipo]
    if procurar:
        partes.append(f"procurar: «{procurar}»")
    if conta:
        partes.append(f"conta: {conta}")
    if frase:
        partes.append(f"frase: «{frase}»")
    return " | ".join(partes)


def ler_destino(texto):
    d = {"tipo": "", "procurar": "", "conta": "", "frase": ""}
    for i, parte in enumerate((texto or "").split(" | ")):
        parte = parte.strip()
        if i == 0:
            d["tipo"] = parte
        elif ": " in parte:
            k, v = parte.split(": ", 1)
            if k in d:
                d[k] = v.strip().strip("«»")
    return d


# Fontes lidas por leitores próprios (turmas): o destino de cada link é conhecido e foi confirmado abrindo o
# link sem sessão iniciada. REGRA: uma fonte nova de turmas só entra com a sua linha nesta tabela; sem ela,
# construir_site.py avisa e o site mostra só «Ver na página oficial».
DESTINOS_FONTES = [
    # Centec Academy: o link de inscrição da turma abre primeiro a página de acesso (CPF e senha) - 20/11/2026
    (r"^https://academy\.centec\.org\.br/", {
        "tipo": "acesso", "conta": "Centec Academy",
        "nota": "Se ainda não tem conta, clique em “Criar uma conta” (são pedidos CPF, RG, e-mail, endereço e "
                "telefone). Depois de entrar, a inscrição nesta turma vai abrir; se não abrir, clique de novo no botão."}),
    # OxeTech Lab (Alagoas): não há página por turma, só a lista; inscrição on-line no site com conta (CPF) - 23/11/2026
    (r"^https://oxetech\.al\.gov\.br/oxetechlab", {
        "tipo": "lista", "nome": "OxeTech", "conta": "conta OxeTech",
        "nota": "Na lista, escolha a cidade. É preciso criar a conta no site (botão «Cadastre-se», com o CPF)."}),
    # Centec presencial: não há página por turma, só a lista geral; inscrição na unidade com o CPF - 20/11/2026
    # O botão diz «Conferir na página do Centec»: serve só para conferir, a inscrição é presencial - 23/11/2026
    (r"^https://www\.centec\.org\.br/", {
        "tipo": "lista", "nome": "Centec", "nota": "A inscrição é feita na unidade, com o CPF."}),
    # Editais do Senac e do SENAI (MA, AC, PI): o link abre o PDF do edital
    (r"\.pdf($|[?#])", {
        "tipo": "pdf", "nota": "Os cursos, as datas e as vagas estão na tabela do anexo, perto do fim."}),
    # Senac Ceará: página da própria turma, com o botão «matricule-se»
    (r"^https://psg\.ce\.senac\.br/oportunidade/", {
        "tipo": "curso", "nota": "Na página da turma, use o botão “matricule-se” e entregue os documentos na "
                                 "unidade dentro do prazo."}),
    (r"^https://psg\.ce\.senac\.br/", {"tipo": "lista", "nota": ""}),
    # Senac Maranhão: página do edital do curso, com «Documentos» e o botão «Inscrição» em «Quer participar?» - 20/11/2026
    # Escola Virtual de Governo: página própria do curso (lida pela API em evg.py), com «Inscreva-se» - 21/11/2026
    (r"^https://www\.escolavirtual\.gov\.br/cursos/", {
        "tipo": "curso", "conta": "Escola Virtual de Governo",
        "nota": "Na página do curso, clique em “Inscreva-se”. Para se inscrever, entre ou crie conta na Escola "
                "Virtual de Governo (a página diz: “Entre ou crie sua conta para realizar a inscrição”)."}),
    # Escola Virtual da Fundação Bradesco: página própria do curso, com o botão "Quero me matricular" - 21/11/2026
    (r"^https://www\.ev\.org\.br/(cursos|trilhas-de-conhecimento)/", {
        "tipo": "curso", "conta": "Escola Virtual da Fundação Bradesco",
        "nota": "Na página do curso, clique em “Quero me matricular”. É preciso entrar ou criar uma conta na Escola "
                "Virtual da Fundação Bradesco (nome, telefone e e-mail). O curso não tem data para começar: você "
                "estuda no seu ritmo."}),
    # Sebrae: página própria do curso na loja, com "Gratuito" e o botão "Inscreva-se agora" (visto no navegador,
    # 22/11/2026; o botão é desenhado por JavaScript). A loja pode abrir na versão do estado (ex.: sp.loja.sebrae.com.br).
    (r"^https://loja\.sebrae\.com\.br/[a-z0-9-]+-(?:\d{9,}|a0[a-z0-9]{14,})/?$", {
        "tipo": "curso", "conta": "conta Sebrae",
        "nota": "Na página do curso (aparece “Gratuito”), clique em “Inscreva-se agora”. A página pode abrir na loja "
                "do Sebrae do seu estado: é o mesmo curso."}),
    (r"^https://ma\.senac\.br/editais_psg/", {
        "tipo": "curso", "nota": "É a página do edital deste curso: em “Quer participar?” está o botão “Inscrição” e "
                                 "em “Documentos” está o edital completo."}),
]


def destino_fixo(link, procurar=""):
    """Destino de um link de uma fonte conhecida (tabela acima), ou None se a fonte não estiver na tabela."""
    for padrao, d in DESTINOS_FONTES:
        if re.search(padrao, link or "", flags=re.I):
            r = {"tipo": d["tipo"], "conta": d.get("conta", ""), "nota": d.get("nota", ""), "procurar": "", "frase": ""}
            if d.get("nome"):
                r["nome"] = d["nome"]  # nome curto da fonte, para o botão «Conferir na página do …»
            if d["tipo"] in ("lista", "inicio"):
                r["procurar"] = procurar
            return r
    return None
