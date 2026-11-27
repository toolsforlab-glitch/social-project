"""Notícias oficiais de cursos gratuitos das prefeituras e governos (23/11/2026), sem Claude.

Muitos cursos para quem mais precisa (ciclos da Semtas do Natal, Semtes de Maceió, Fortaleza Inclusiva…) não estão em
nenhuma lista de cursos: saem só como notícia no site oficial da prefeitura, com inscrição presencial e poucos dias de
prazo. Este script lê, todos os dias, as páginas de notícias oficiais da tabela FONTES e, quando aparece uma notícia
NOVA cujo título fala de cursos gratuitos ou de qualificação profissional, cria um curso «Novo» com o link da notícia
oficial (Origem «notícia oficial»).

A seguir, na mesma rotina, a verificação (verificar.py com VERIFICAR_ORIGEM="notícia oficial") lê cada notícia com
o Claude e aplica todas as regras do site (gratuidade com frase, prazo, prova para entrar, emprego, auditoria
independente) antes de publicar. Este script não publica nada.

Na primeira leitura de cada fonte, as notícias que já lá estão são só marcadas como vistas (essas já foram tratadas à
mão a 23/11/2026).
"""
import datetime
import html as _html
import json
import re
import sys
import urllib.parse

from base import VERIFICACAO_INICIAL, Base, carregar_config, registar_pendencia
from comum import baixar, gravar_json, ler_json
from cursos import id_curso

ESTADO = "estado/noticias_oficiais.json"
ORIGEM = "notícia oficial"
DIAS_API = 20  # na API do WordPress (Piauí), só as notícias dos últimos dias

FONTES = [
    {"nome": "Prefeitura do Natal – Semtas", "pagina": "https://natal.rn.gov.br/semtas", "local": "BR-RN",
     "regiao": "Rio Grande do Norte", "cidade": "Natal", "entidade": "Prefeitura do Natal (Semtas)"},
    {"nome": "Prefeitura de Maceió", "pagina": "https://maceio.al.gov.br/noticias", "local": "BR-AL",
     "regiao": "Alagoas", "cidade": "Maceió", "entidade": "Prefeitura de Maceió"},
    {"nome": "Prefeitura de Fortaleza", "pagina": "https://www.fortaleza.ce.gov.br/noticias", "local": "BR-CE",
     "regiao": "Ceará", "cidade": "Fortaleza", "entidade": "Prefeitura de Fortaleza"},
    {"nome": "Prefeitura de Fortaleza – Fortaleza Inclusiva", "pagina": "https://www.fortaleza.ce.gov.br/fortaleza-inclusiva",
     "local": "BR-CE", "regiao": "Ceará", "cidade": "Fortaleza", "entidade": "Prefeitura de Fortaleza (Fortaleza Inclusiva)"},
    # Piauí: o portal do governo (WordPress) tem pesquisa pública; usam-se só as notícias recentes
    {"nome": "Governo do Piauí", "api": "https://www.pi.gov.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["cursos gratuitos", "qualificação profissional inscrições"], "local": "BR-PI", "regiao": "Piauí",
     "cidade": "", "entidade": "Governo do Piauí"},
    # Cagece Capacita (24/11/2026): cursos profissionalizantes gratuitos todos os meses em Fortaleza, com carta de
    # encaminhamento do Sine/IDT. O site da Cagece não abre fora do Brasil; as notícias saem no portal do Governo do
    # Ceará, cuja pesquisa (WordPress) abre a partir do GitHub. Os títulos falam de «cartas de encaminhamento», não de
    # «cursos gratuitos», daí o filtro próprio. Na primeira leitura já cria as notícias dos últimos 20 dias (nenhuma foi
    # tratada à mão).
    {"nome": "Governo do Ceará – Cagece Capacita",
     "api": "https://www.ce.gov.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["cagece capacita"], "local": "BR-CE", "regiao": "Ceará", "cidade": "Fortaleza",
     "entidade": "Cagece (Cagece Capacita)", "incluir": r"cagece capacita.*(?:carta|curso|inscri|matr[íi]cula|vaga)",
     "primeira_leitura_cria": True},
    # Norte (26/11/2026). Roraima: a Escola do Legislativo (Escolegis) da Assembleia Legislativa abre turmas
    # presenciais gratuitas em Boa Vista várias vezes por ano, com inscrições de 2 ou 3 dias no site da ALE-RR
    # (ex.: 720 vagas, inscrições de 9 a 11/11/2026). Rondônia: o IDEP (Instituto Estadual de Desenvolvimento da
    # Educação Profissional, escolas técnicas estaduais) abre cursos de qualificação presenciais e remotos, com seleção
    # por ordem de inscrição, e a Escola Móvel nos municípios; as notícias saem no portal do Governo de Rondônia.
    {"nome": "Assembleia Legislativa de Roraima – Escolegis",
     "api": "https://al.rr.leg.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["escolegis"], "local": "BR-RR", "regiao": "Roraima", "cidade": "Boa Vista",
     "entidade": "Assembleia Legislativa de Roraima (Escola do Legislativo – Escolegis)",
     "incluir": r"(?:vagas|inscri[çc][õo]es|abre|oferta).{0,60}cursos|cursos.{0,60}(?:vagas|inscri)"},
    {"nome": "Governo de Rondônia – IDEP",
     "api": "https://rondonia.ro.gov.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["inscrições cursos", "Escola Móvel inscrições"], "local": "BR-RO", "regiao": "Rondônia", "cidade": "",
     "entidade": "Governo de Rondônia (IDEP – Educação Profissional)",
     "incluir": r"inscri[çc][õo]es.{0,80}cursos|cursos.{0,80}inscri[çc][õo]es|vagas.{0,40}cursos"},
    {"nome": "Governo de Roraima",
     "api": "https://portal.rr.gov.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["cursos gratuitos", "qualificação profissional inscrições"], "local": "BR-RR", "regiao": "Roraima",
     "cidade": "", "entidade": "Governo de Roraima"},
    {"nome": "Prefeitura de Porto Velho", "pagina": "https://www.portovelho.ro.gov.br/noticias", "local": "BR-RO",
     "regiao": "Rondônia", "cidade": "Porto Velho", "entidade": "Prefeitura de Porto Velho"},
    {"nome": "Prefeitura de Palmas", "pagina": "https://www.palmas.to.gov.br/core/noticias/", "local": "BR-TO",
     "regiao": "Tocantins", "cidade": "Palmas", "entidade": "Prefeitura de Palmas"},
    # Maranhão e Pernambuco (26/11/2026). IEMA (Instituto Estadual de Educação, Ciência e Tecnologia do Maranhão):
    # publica no seu site (WordPress; a API só abre com ?rest_route=) editais de cursos FIC e de qualificação nas
    # Unidades Vocacionais, várias vezes por ano (ex.: Editais 08, 09, 13 e 18/2026). O Edital 13/2026 é um edital GERAL
    # (vigente até 31/12/2026, prorrogável 6 meses): as vagas saem em «Editais Complementares de Oferta», preenchidas por
    # ordem de manifestação de interesse (item 4.5); daí a pesquisa «vocacional» e «edital complementar» no filtro (27/11).
    # Nenhum foi tratado à mão, daí
    # «primeira_leitura_cria». SEDEPE (Secretaria de Desenvolvimento Econômico de Pernambuco): notícias do Qualifica PE
    # (o portal do programa não abre a partir do GitHub; o site da SEDEPE abre).
    {"nome": "IEMA – editais de cursos FIC",
     "api": "https://iema.ma.gov.br/?rest_route=/wp/v2/posts&search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["formação inicial e continuada", "qualificação profissional", "vagas ociosas", "curso de libras", "vocacional"],
     "local": "BR-MA", "regiao": "Maranhão", "cidade": "",
     "entidade": "IEMA – Instituto Estadual de Educação, Ciência e Tecnologia do Maranhão",
     "incluir": r"forma[çc][ãa]o inicial e continuada|\bFICs?\b|qualifica[çc][ãa]o profissional|vagas ociosas|curso (?:b[áa]sico|intermedi[áa]rio)|edital complementar|unidade vocacional|iema idiomas",
     "primeira_leitura_cria": True},
    {"nome": "Governo de Pernambuco – SEDEPE (Qualifica PE)",
     "api": "https://www.sedepe.pe.gov.br/wp-json/wp/v2/posts?search={q}&per_page=20&_fields=date,link,title",
     "pesquisas": ["qualifica pe", "cursos gratuitos"], "local": "BR-PE", "regiao": "Pernambuco", "cidade": "",
     "entidade": "Governo de Pernambuco – SEDEPE (Qualifica PE)",
     "incluir": r"qualifica pe|inscri[çc][õo]es.{0,60}cursos|cursos.{0,40}(?:gratuit|qualifica)"},
]

INCLUIR = re.compile(r"cursos?\s+(?:\w+\s+){0,2}(?:gratuit|de\s+qualifica|profissionaliz|de\s+capacita)|"
                     r"vagas\s+(?:gratuitas\s+)?(?:em|para|de)\s+(?:\w+\s+)?cursos|qualifica[çc][ãa]o\s+profissional|"
                     r"inscri[çc][õo]es\s+(?:abertas\s+)?para\s+(?:os\s+)?cursos|oficinas?\s+gratuit", re.I)
EXCLUIR = re.compile(r"servidor|gestor|conselheir|professor|concurso|seletivo\s+para\s+contrat|"
                     r"capacita\s+(?:profissionais|equipes|t[ée]cnicos)|entrega\s+(?:de\s+)?certificad|formatura|"
                     r"certifica\s+(?:mais\s+de\s+)?\d|entregam|entregaram|\d+\s+certificados|encerra", re.I)


def limpar_titulo(t):
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^\d{2}/\d{2}/\d{4}\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{3,30}\s+", "", t)  # Maceió: «23/11/2026 OPORTUNIDADES …»
    t = re.sub(r"\s+[A-Z]{3,10}\s*,\s*\d{2}/\d{2}/\d{4}\.?$", "", t)       # Natal: «… SEMTAS , 17/11/2026.»
    t = re.sub(r"^(?:Economia|Educação|Cidadania|Trabalho)\s+(?=[A-ZÁÉÍÓÚ])", "", t)  # Fortaleza: «Economia Prefeitura …»
    return t.strip(" .")[:200]


def noticias_da_pagina(fonte):
    html = baixar(fonte["pagina"], timeout=40).decode("utf-8", "replace")
    achadas = {}
    for href, texto in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, flags=re.S):
        titulo = limpar_titulo(texto)
        if len(titulo) < 25:
            continue
        link = urllib.parse.urljoin(fonte["pagina"], _html.unescape(href))
        if urllib.parse.urlparse(link).netloc.split(":")[0].lower() != urllib.parse.urlparse(fonte["pagina"]).netloc.lower():
            continue
        if len(titulo) > len(achadas.get(link, "")):
            achadas[link] = titulo
    return achadas


def noticias_da_api(fonte, hoje):
    achadas = {}
    limite = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_API)).isoformat()
    for q in fonte["pesquisas"]:
        url = fonte["api"].format(q=urllib.parse.quote(q))
        for p in json.loads(baixar(url, timeout=40).decode("utf-8-sig", "replace")):  # o portal de RO manda BOM
            if str(p.get("date", ""))[:10] >= limite:
                achadas[p["link"]] = limpar_titulo((p.get("title") or {}).get("rendered", ""))
    return achadas


def main():
    base = Base()
    carregar_config(base)
    hoje = datetime.date.today().isoformat()
    estado = ler_json(ESTADO, {"vistas": {}})
    links_na_base = {(r.get("Link") or "").strip().rstrip("/") for r in base.tabela("Cursos")}
    novos = []
    for f in FONTES:
        try:
            achadas = noticias_da_api(f, hoje) if f.get("api") else noticias_da_pagina(f)
        except Exception as e:  # noqa: BLE001
            print(f"{f['nome']}: a página não abriu ({type(e).__name__}); fica para amanhã.")
            # regra T10 (26/11/2026): o que o GitHub não abre é tentado no Chrome do responsável pela tarefa diária
            registar_pendencia(base, f"{f['nome']}: a página não abriu a partir do GitHub ({type(e).__name__}).",
                               "A tarefa diária do navegador tenta ler esta página no Chrome (regra T10).",
                               f.get("pagina") or f["api"].split("?")[0], origem="noticias_oficiais.py")
            continue
        primeira = f["nome"] not in estado["vistas"]
        vistas = estado["vistas"].setdefault(f["nome"], {})
        incluir = re.compile(f["incluir"], re.I) if f.get("incluir") else INCLUIR
        relevantes = {l: t for l, t in achadas.items() if incluir.search(t) and not EXCLUIR.search(t)}
        n_novas = 0
        for link, titulo in relevantes.items():
            if link in vistas:
                continue
            vistas[link] = hoje
            if (primeira and not f.get("primeira_leitura_cria")) or link.rstrip("/") in links_na_base:
                continue
            n_novas += 1
            novos.append({
                "ID": id_curso(link, titulo), "Estado": "Novo", "Título": titulo, "Entidade": f["entidade"], "Link": link,
                "Local": f["local"], "Modalidade": "presencial", "País": "BR", "Região": f["regiao"], "Cidade": f["cidade"],
                "Descrição": "", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "", "Requisitos": "",
                "Certificado": "desconhecido", "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM",
                "Primeiro visto": hoje, "Última verificação": "", "Origem": ORIGEM,
                "Notas": f"{hoje}: notícia nova na página oficial «{f['nome']}» ({f.get('pagina') or 'pesquisa do portal'}).",
                "Como me inscrever": "", "Nota da verificação": "", **VERIFICACAO_INICIAL,
                "Situação das inscrições": "Por confirmar", "Verificar automaticamente": "TRUE",
            })
            print(f"  + {f['nome']}: {titulo[:90]}")
        print(f"{f['nome']}: {len(achadas)} links, {len(relevantes)} sobre cursos, "
              + ("primeira leitura (marcadas como vistas)." if primeira else f"{n_novas} notícias novas."))
    if novos:
        base.acrescentar("Cursos", novos)
    base.guardar()
    gravar_json(ESTADO, estado)
    print(f"Notícias oficiais: {len(novos)} cursos novos para a verificação.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
