"""Vigia páginas oficiais que ainda não têm leitor próprio porque, quando foram vistas, não havia nada aberto.

Para cada página, guarda-se a frase que ela mostra quando está FECHADA. Se a página abrir e a frase sumir, a rotina
abre uma pendência para o responsável (e para o Claude montar o leitor próprio a partir da página aberta).
Não muda cursos nem turmas.
"""
import urllib.parse
import json
import sys

from base import Base, carregar_config, registar_pendencia
from comum import baixar

VIGIAS = [
    {"nome": "Senac Pernambuco (Programa Senac de Gratuidade)",
     "url": "https://intranet.pe.senac.br/dr/nova/psgnet/",
     "fechado": "não existe processo de inscrição aberto",
     "verificar": "O Senac PE abriu inscrições: peça ao Claude para montar o leitor próprio a partir da página "
                  "(enquanto está aberta). A pendência de 23/11 sobre o Senac PE pode ser fechada depois disso."},
    # SENAI Bahia (cursos técnicos com bolsa): saiu em 23/11/2026, porque a entrada exige nota do ENEM (regra: cursos
    # com prova ficam fora); o vigia foi retirado.
    # Senac Paraíba: o catálogo de matrículas tem o tipo de formação «Seleção PSG» (código 5); em 23/11/2026 estava
    # vazio. A resposta deste endereço traz também campos internos de pagamento do Senac PB: só se conta o número
    # de turmas, nada mais é lido nem guardado.
    {"nome": "Senac Paraíba (Seleção PSG no catálogo de matrículas)",
     "url": "https://pb.senac.br/matriculas/matricula/cursos-tecnicos/get-turmas.php?json="
            "%7B%22search%22%3A%22%22%2C%22nivel%22%3A%5B%5D%2C%22area%22%3A%22%22%2C%22cidade%22%3A%22%22%2C"
            "%22unidade%22%3A%22%22%2C%22tpFormacao%22%3A%5B%225%22%5D%2C%22turnos%22%3A%5B%5D%2C"
            "%22dataInicial%22%3A%22%22%2C%22dataFinal%22%3A%22%22%7D",
     "contar_json": True, "link": "https://pb.senac.br/matriculas/matricula/cursos-tecnicos/index.php",
     "verificar": "Apareceram turmas «Seleção PSG» (gratuitas) no catálogo do Senac PB: peça ao Claude para montar o "
                  "leitor próprio enquanto estão abertas (filtro «Tipo de formação: Seleção PSG»)."},
    # Senac Sergipe: o portal do PSG (psg.se.senac.br/cursos) lê a lista pública /api/course/filter; em 23/11/2026 tinha
    # 0 cursos. Conta-se meta.totalItems.
    {"nome": "Senac Sergipe (Programa Senac de Gratuidade)",
     "url": "https://psg.se.senac.br/api/course/filter?page=1&limit=6",
     "contar_json": True, "caminho": ["meta", "totalItems"], "link": "https://psg.se.senac.br/cursos",
     "verificar": "Apareceram cursos no portal do PSG do Senac Sergipe: peça ao Claude para montar o leitor próprio a "
                  "partir da lista pública (psg.se.senac.br/api/course/filter)."},
    # SENAI Rio Grande do Norte: a página «Oportunidades» (vagas gratuitas regimentais) lê esta lista; em 23/11/2026
    # respondia «Nenhuma oportunidade encontrada».
    {"nome": "SENAI Rio Grande do Norte (vagas gratuitas regimentais)",
     "url": "https://www.rn.senai.br/transparencia/includes/api/api-oportunidades.php?acao=resultado&modalidade=&produto=&cidade=&area=&curso=",
     "fechado": "Nenhuma oportunidade encontrada",
     "verificar": "O SENAI RN publicou vagas gratuitas na página «Oportunidades» (www.rn.senai.br/oportunidades/): peça "
                  "ao Claude para montar o leitor próprio enquanto estão abertas."},
    # Senac Rio Grande do Norte: a página do Programa de Bolsas mostra o último edital; em 23/11/2026 só tinha o
    # resultado do edital 006/2026 (fechado). Quando o texto mudar, saiu edital novo.
    {"nome": "Senac Rio Grande do Norte (Programa de Bolsas / PSG)",
     "url": "https://lp.rn.senac.br/programa-de-bolsa",
     "fechado": "RESULTADO EDITAL Nº 006_2026",
     "verificar": "O Senac RN mudou a página do Programa de Bolsas (provavelmente edital novo): peça ao Claude para ler o "
                  "edital e montar o leitor próprio."},
    # SENAI Amazonas: as páginas da FIEAM não abrem a partir do GitHub (Cloudflare); o leitor (senac_ma.py, fonte «Senai
    # AM») procura os PDFs da chamada seguinte pelos nomes habituais. Reserva: se o Google Notícias tiver notícias
    # recentes da abertura e o leitor ainda não tiver achado a chamada, abre-se uma pendência.
    {"nome": "SENAI Amazonas (Chamada Pública de gratuidade)",
     "rss": "https://news.google.com/rss/search?q=%22Senai%22+Amazonas+vagas+gratuitas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"senai[\s-]*(?:amazonas|am)\b.*(?:vagas|inscri)|(?:vagas|inscri).*senai[\s-]*(?:amazonas|am)\b",
     "dias": 10, "estado_leitor": "estado/senai_am_chamadas.json",
     "link": "https://fieam.org.br/senai/chamada-publica/",
     "verificar": "Há notícias de uma Chamada Pública nova do SENAI AM e o leitor não achou o PDF (nome novo): peça ao "
                  "Claude para abrir fieam.org.br/senai/chamada-publica/ no navegador e juntar os links da chamada e da "
                  "programação ao estado (estado/senai_am_chamadas.json)."},
    # SENAI Bahia: cada processo seletivo de curso gratuito (parcerias com empresas, programas como o CIMATEC Plural)
    # ganha uma página própria no WordPress do site, com formato diferente de processo para processo, e as inscrições
    # duram uma ou duas semanas. A lista pública de páginas (/wp-json/wp/v2/pages) é lida com as palavras abaixo; uma
    # página nova (que não estava na leitura anterior) abre uma pendência para se criar o curso a partir da página e do
    # edital. Os cursos técnicos com bolsa ficam fora (a bolsa exige nota do ENEM; regra: cursos com prova ficam fora).
    {"nome": "SENAI Bahia (processos seletivos de cursos gratuitos)",
     "wp": ["https://www.senaibahia.com.br/wp-json/wp/v2/pages?search=processo%20seletivo&orderby=modified"
            "&per_page=30&_fields=link,title,modified",
            "https://www.senaibahia.com.br/wp-json/wp/v2/pages?search=gratuit&orderby=modified"
            "&per_page=30&_fields=link,title,modified"],
     "estado": "estado/senai_ba_paginas.json", "dias": 30,
     "link": "https://www.senaibahia.com.br/cursos-gratuitos-parceria-com-empresas/",
     "verificar": "O SENAI Bahia publicou a página de um processo seletivo novo. Abra a página e o edital: entra se o "
                  "curso for gratuito (escrito), a seleção não tiver prova (ordem de inscrição, sorteio ou análise de "
                  "documentos) e as inscrições estiverem abertas. Peça ao Claude para criar o curso."},
    # Secretaria da Educação da Bahia (SEC): cursos técnicos subsequentes ao ensino médio (Prosub), gratuitos, com vagas
    # por sorteio eletrônico (sorteio pode entrar; o site avisa). As inscrições abrem duas vezes por ano (em 2026: 09/01 e
    # junho/julho) e duram poucas semanas. Quando sair notícia de inscrições abertas, abre-se uma pendência para se criar
    # o curso a partir do edital oficial (www.ba.gov.br/educacao).
    {"nome": "SEC Bahia (cursos técnicos subsequentes por sorteio)",
     "rss": "https://news.google.com/rss/search?q=%22sorteio+eletr%C3%B4nico%22+%22cursos+t%C3%A9cnicos%22+Bahia&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"^(?=.*(inscri|abre|abertas))(?=.*(cursos? t[ée]cnicos?|sorteio))", "dias": 10,
     "link": "https://www.ba.gov.br/educacao/noticias",
     "resumo": "notícias recentes de inscrições para o sorteio dos cursos técnicos",
     "verificar": "A SEC Bahia abriu inscrições para o sorteio de vagas nos cursos técnicos subsequentes (gratuitos, para "
                  "quem terminou o ensino médio). Abra o edital oficial em www.ba.gov.br/educacao e peça ao Claude para "
                  "criar o curso com o período de inscrição, os requisitos e o aviso de que as vagas são por sorteio."},
    # Piauí: desde 19/11/2026 o certificado de psg.pi.senac.br está expirado (confirmado em 25/11: Let's Encrypt, válido
    # até 19/11/2026) e o leitor do Senac PI não abre a lista; a verificação de segurança não é desligada. O site
    # principal (www.pi.senac.br) só liga para o portal do PSG. Enquanto isso, as notícias avisam quando abrem vagas.
    # A Seduc PI (Mais Formação, Mais Renda) recusa ligações do GitHub: também por notícias.
    {"nome": "Senac Piauí (PSG; portal com certificado expirado)",
     "rss": "https://news.google.com/rss/search?q=%22Senac%22+Piau%C3%AD+vagas+gratuitas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"^(?=.*senac)(?=.*(piau[íi]|teresina|parna[íi]ba|picos|floriano))(?=.*(vagas|inscri|gratuit))", "dias": 10,
     "link": "https://news.google.com/search?q=Senac+Piau%C3%AD+vagas+gratuitas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de vagas gratuitas",
     "verificar": "O portal do PSG do Senac Piauí (psg.pi.senac.br) está com o certificado de segurança expirado e o "
                  "leitor automático não o abre. Abra a notícia e o portal no seu navegador; se o edital estiver "
                  "aberto, peça ao Claude para criar o curso a partir do PDF do edital (pode anexá-lo)."},
    {"nome": "Seduc Piauí (Mais Formação, Mais Renda)",
     "rss": "https://news.google.com/rss/search?q=%22Mais+Forma%C3%A7%C3%A3o%22+Piau%C3%AD+inscri%C3%A7%C3%B5es&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"inscri|vagas|cursos?", "dias": 10,
     "link": "https://news.google.com/search?q=%22Mais+Forma%C3%A7%C3%A3o%22+Piau%C3%AD+inscri%C3%A7%C3%B5es&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de inscrições",
     "verificar": "O site da Seduc PI não abre a partir do GitHub. Abra a notícia e procure a página oficial (pi.gov.br) "
                  "com as datas de inscrição e a gratuidade; peça ao Claude para criar o curso."},
    # Senac Tocantins: o site (www.to.senac.br) só mostra turmas pagas (formas de pagamento na própria lista); em
    # 25/11/2026 não havia página nem lista pública do PSG. As notícias avisam quando abrem vagas gratuitas.
    {"nome": "Senac Tocantins (PSG; sem lista pública)",
     "rss": "https://news.google.com/rss/search?q=%22Senac%22+Tocantins+vagas+gratuitas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"^(?=.*senac)(?=.*(tocantins|palmas|aragua[íi]na|gurupi|\bTO\b))(?=.*(vagas|inscri|gratuit))", "dias": 10,
     "link": "https://news.google.com/search?q=%22Senac%22+Tocantins+vagas+gratuitas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de vagas gratuitas",
     "verificar": "O Senac Tocantins não tem lista pública das turmas do PSG. Abra a notícia e procure o edital ou a "
                  "página oficial com as datas de inscrição; peça ao Claude para criar o curso (pode anexar o PDF)."},
    # Institutos federais (cursos FIC, técnicos subsequentes e EJA, gratuitos; entram os que não têm prova): as páginas
    # que listam os editais são lidas e cada edital NOVO de seleção de alunos abre uma pendência, para se criar o curso
    # a partir do edital (prova, sorteio ou ordem de inscrição conferidos no PDF). Tipo «itens»: na primeira leitura só
    # se guardam os editais que já lá estão.
    {"nome": "IFRN (portal de processos seletivos)",
     "itens": ["https://processoseletivo.ifrn.edu.br/"], "estado": "estado/ifrn_editais.json",
     "item": r"<h3><a href='([^']+)'>([^<]+)</a></h3>",
     "incluir": r"FIC|Forma[çc][ãa]o Inicial|Subsequente|EJA|Proeja|Qualifica",
     "excluir": r"P[óo]s-Gradua|Mestrado|Doutorado|Especializa|Licenciatura|Superior|Gradua[çc][ãa]o|BOLSISTA|ESTAGI|servidores|funcion[áa]rios|privação de liberdade|PROFESSOR|COORDENA|TUTOR|ASSISTENTE|CADASTRO RESERVA|DOCENTE|HETEROIDENTIFICA|RELATOS",
     "link": "https://processoseletivo.ifrn.edu.br/",
     "verificar": "Edital novo de cursos para a comunidade no IFRN. Abra o edital: entra se for gratuito, sem prova "
                  "(sorteio, ordem de inscrição ou análise de documentos) e com inscrições abertas. Peça ao Claude para "
                  "criar o curso."},
    {"nome": "IFRO (cursos FIC dos campi)",
     "itens": ["https://selecao.ifro.edu.br/extensao-ariquemes", "https://selecao.ifro.edu.br/extensao-buritis", "https://selecao.ifro.edu.br/extensao-cacoal", "https://selecao.ifro.edu.br/extensao-colorado", "https://selecao.ifro.edu.br/extensao-guajara-mirim", "https://selecao.ifro.edu.br/extensao-jaru", "https://selecao.ifro.edu.br/extensao-jiparana", "https://selecao.ifro.edu.br/extensao-calama", "https://selecao.ifro.edu.br/extensao-zona-norte", "https://selecao.ifro.edu.br/extensao-saomiguel", "https://selecao.ifro.edu.br/extensao-vilhena", "https://selecao.ifro.edu.br/reitoria"],
     "estado": "estado/ifro_fic.json",
     "item": r'<h2 class="tileHeadline">\s*<a href="([^"]+)">([^<]+)</a>',
     "incluir": r"sele[çc][ãa]o de (alunos|cursistas|estudantes|interessados|candidatas)|\bcursos?\b|\bFIC\b|forma[çc][ãa]o inicial",
     "excluir": r"professor|bolsista|profissiona|mediador|docente|servidor|ONU|coral|audi[çc]",
     "link": "https://selecao.ifro.edu.br/cursos-fic",
     "verificar": "Edital novo de curso FIC (curta duração, gratuito) num campus do IFRO. Abra o edital: entra se não "
                  "tiver prova (sorteio, ordem de inscrição ou análise de documentos) e as inscrições estiverem abertas. "
                  "Peça ao Claude para criar o curso."},
    # OSCs aprovadas pelos critérios de histórico (regra do responsável, 25/11/2026; ver LEIAME). Não publicam as turmas
    # num site: a inscrição é feita no município, pela própria OSC. Se o Google Notícias tiver notícias recentes de cursos
    # ou inscrições com o nome delas, abre-se uma pendência (uma por mês e por OSC). Os cursos só entram com página
    # oficial da turma (datas e gratuidade).
    {"nome": "Fundação Esperança – FÉ (Barreiras, BA)",
     "rss": "https://news.google.com/rss/search?q=%22Funda%C3%A7%C3%A3o+Esperan%C3%A7a%22+Barreiras&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"curso|inscri|qualifica|capacita|vagas|forma[çc][ãa]o", "dias": 14,
     "link": "https://news.google.com/search?q=%22Funda%C3%A7%C3%A3o+Esperan%C3%A7a%22+Barreiras&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de cursos ou inscrições",
     "verificar": "OSC aprovada pelos critérios de histórico (LEIAME). Abra as notícias, procure a página oficial da "
                  "turma (datas de inscrição e gratuidade explícita) e peça ao Claude para criar o curso. Sem página "
                  "oficial, o curso não entra."},
    {"nome": "Associação Central de Cidadania (Serrinha, BA)",
     "rss": "https://news.google.com/rss/search?q=%22Associa%C3%A7%C3%A3o+Central+de+Cidadania%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"curso|inscri|qualifica|capacita|vagas|forma[çc][ãa]o", "dias": 14,
     "link": "https://news.google.com/search?q=%22Associa%C3%A7%C3%A3o+Central+de+Cidadania%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de cursos ou inscrições",
     "verificar": "OSC aprovada pelos critérios de histórico (LEIAME). Abra as notícias, procure a página oficial da "
                  "turma (datas de inscrição e gratuidade explícita) e peça ao Claude para criar o curso. Sem página "
                  "oficial, o curso não entra."},
    {"nome": "Instituto Casa da Cidadania (Vitória da Conquista, BA)",
     "rss": "https://news.google.com/rss/search?q=%22Casa+da+Cidadania%22+%22Vit%C3%B3ria+da+Conquista%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"curso|inscri|qualifica|capacita|vagas|forma[çc][ãa]o", "dias": 14,
     "link": "https://news.google.com/search?q=%22Casa+da+Cidadania%22+%22Vit%C3%B3ria+da+Conquista%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de cursos ou inscrições",
     "verificar": "OSC aprovada pelos critérios de histórico (LEIAME). Abra as notícias, procure a página oficial da "
                  "turma (datas de inscrição e gratuidade explícita) e peça ao Claude para criar o curso. Sem página "
                  "oficial, o curso não entra."},
    {"nome": "MOC – Movimento de Organização Comunitária (Feira de Santana, BA)",
     "rss": "https://news.google.com/rss/search?q=%22Movimento+de+Organiza%C3%A7%C3%A3o+Comunit%C3%A1ria%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"curso|inscri|qualifica|capacita|vagas|forma[çc][ãa]o", "dias": 14,
     "link": "https://news.google.com/search?q=%22Movimento+de+Organiza%C3%A7%C3%A3o+Comunit%C3%A1ria%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de cursos ou inscrições",
     "verificar": "OSC aprovada pelos critérios de histórico (LEIAME). Abra as notícias, procure a página oficial da "
                  "turma (datas de inscrição e gratuidade explícita) e peça ao Claude para criar o curso. Sem página "
                  "oficial, o curso não entra."},
    {"nome": "OELA – Oficina Escola de Lutheria da Amazônia (AM/AP)",
     "rss": "https://news.google.com/rss/search?q=%22Lutheria+da+Amaz%C3%B4nia%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "titulo": r"curso|inscri|qualifica|capacita|vagas|forma[çc][ãa]o", "dias": 14,
     "link": "https://news.google.com/search?q=%22Lutheria+da+Amaz%C3%B4nia%22&hl=pt-BR&gl=BR&ceid=BR:pt-419",
     "resumo": "notícias recentes de cursos ou inscrições",
     "verificar": "OSC aprovada pelos critérios de histórico (LEIAME). Abra as notícias, procure a página oficial da "
                  "turma (datas de inscrição e gratuidade explícita) e peça ao Claude para criar o curso. Sem página "
                  "oficial, o curso não entra."},
]

# EJA (Educação de Jovens e Adultos) na varredura dos estados (pedido do responsável, 25/11/2026). A matrícula na
# rede pública abre em períodos (em geral de novembro a fevereiro, e alguns estados no meio do ano); estas vigias
# avisam quando sai notícia de matrícula aberta, para se criar o curso em «Terminar a escola» a partir da página
# oficial da secretaria de educação.
ESTADOS_EJA = ["Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Maranhão", "Pará", "Paraíba",
               "Pernambuco", "Piauí", "Rio Grande do Norte", "Rondônia", "Roraima", "Sergipe", "Tocantins"]
for _uf in ESTADOS_EJA:
    _q = urllib.parse.quote_plus(f'EJA matrícula "{_uf}"')
    VIGIAS.append({
        "nome": f"EJA – {_uf}",
        "rss": f"https://news.google.com/rss/search?q={_q}&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "titulo": r"^(?!.*(fraude|suspeit|investig|\blei\b|den[úu]ncia))(?=.*(\bEJA\b|jovens e adultos))"
                   r"(?=.*(matr[íi]cul|vagas|inscri))", "dias": 14,
        "link": f"https://news.google.com/search?q={_q}&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "resumo": "notícias recentes de matrícula na EJA",
        "verificar": "Matrícula na EJA da rede pública (estado ou prefeitura). Abra a notícia e procure a página "
                     "oficial da secretaria de educação com o período de matrícula, onde e como se matricular e os "
                     "documentos. Peça ao Claude para criar o curso em «Terminar a escola». Sem página oficial com o "
                     "período, não entra. Para quem não acha escola: CadEJA do MEC (cadeja.mec.gov.br)."})


def vigiar_rss(base, v):
    """Notícias recentes (Google Notícias) que o leitor próprio ainda não apanhou."""
    import datetime
    import email.utils
    import re
    from comum import ler_json
    try:
        xml = baixar(v["rss"], timeout=40).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"{v['nome']}: o Google Notícias não abriu ({type(e).__name__}); fica para amanhã.")
        return
    import os
    dias = int(os.environ.get("DIAS_ENSAIO") or v["dias"])  # só para ensaios
    hoje = datetime.date.today()
    vista = (ler_json(v["estado_leitor"], {}) or {}).get("vista_em", "") if v.get("estado_leitor") else ""
    recentes = []
    for titulo, data in re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", xml, flags=re.S):
        try:
            d = email.utils.parsedate_to_datetime(data).date()
        except (TypeError, ValueError):
            continue
        if (hoje - d).days <= dias and re.search(v["titulo"], titulo, flags=re.I) and (not vista or vista < d.isoformat()):
            recentes.append(f"{d.isoformat()}: {titulo}")
    if not recentes:
        print(f"{v['nome']}: sem notícias novas de abertura.")
        return
    resumo = v.get("resumo", "notícias de abertura e nenhum PDF achado pelo leitor")
    print(f"{v['nome']}: {len(recentes)} {resumo}.")
    for r in recentes[:5]:
        print("   ", r[:200])
    if base is None:  # ensaio (SECO=1)
        return
    registar_pendencia(base, f"{v['nome']}: {resumo} ({recentes[0][:200]}).",
                       v["verificar"], v["link"] + "#" + hoje.strftime("%Y-%m"), origem="vigiar.py")


def vigiar_wp(base, v):
    """Páginas novas de um site WordPress (lista pública), comparadas com as da leitura anterior."""
    import datetime
    import html as _html
    from comum import gravar_json, ler_json
    paginas = {}
    for url in v["wp"]:
        try:
            for p in json.loads(baixar(url, timeout=40).decode("utf-8", "replace")):
                paginas[p["link"]] = (_html.unescape(p.get("title", {}).get("rendered", "")), p.get("modified", "")[:10])
        except Exception as e:  # noqa: BLE001
            print(f"{v['nome']}: a lista de páginas não abriu ({type(e).__name__}); fica para amanhã.")
            return
    estado = ler_json(v["estado"], None)
    if estado is None:  # primeira leitura: só guarda o que já existe
        gravar_json(v["estado"], {"links": sorted(paginas)})
        print(f"{v['nome']}: primeira leitura, {len(paginas)} páginas guardadas.")
        return
    limite = (datetime.date.today() - datetime.timedelta(days=v["dias"])).isoformat()
    novas = [(l, t, m) for l, (t, m) in paginas.items() if l not in set(estado.get("links", [])) and m >= limite]
    gravar_json(v["estado"], {"links": sorted(set(estado.get("links", [])) | set(paginas))})
    if not novas:
        print(f"{v['nome']}: sem páginas novas.")
        return
    for link, titulo, mod in novas:
        print(f"{v['nome']}: página nova: {titulo} ({mod}) {link}")
        if base is not None:
            registar_pendencia(base, f"{v['nome']}: página nova «{titulo or link}» (alterada em {mod}).",
                               v["verificar"], link, origem="vigiar.py")


def vigiar_itens(base, v):
    """Editais novos numa ou mais páginas de listas (comparados com os da leitura anterior)."""
    import html as _html
    import re
    import urllib.parse
    from comum import gravar_json, ler_json
    achados = {}
    for url in v["itens"]:
        try:
            pagina = baixar(url, timeout=40).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"{v['nome']}: {url} não abriu ({type(e).__name__}).")
            continue
        for m in re.finditer(v["item"], pagina, flags=re.S | re.I):
            partes = m.groups()
            titulo = re.sub(r"\s+", " ", _html.unescape(partes[-1])).strip()
            link = urllib.parse.urljoin(url, partes[0]) if len(partes) > 1 else url
            if re.search(v["incluir"], titulo, flags=re.I) and not re.search(v["excluir"], titulo, flags=re.I):
                achados[titulo] = link
    if not achados:
        print(f"{v['nome']}: nenhum edital lido (a página mudou?).")
        return
    estado = ler_json(v["estado"], None)
    if estado is None:
        gravar_json(v["estado"], {"titulos": sorted(achados)})
        print(f"{v['nome']}: primeira leitura, {len(achados)} editais guardados.")
        return
    novos = [(t, l) for t, l in achados.items() if t not in set(estado.get("titulos", []))]
    gravar_json(v["estado"], {"titulos": sorted(set(estado.get("titulos", [])) | set(achados))})
    if not novos:
        print(f"{v['nome']}: sem editais novos ({len(achados)} na lista).")
        return
    for titulo, link in novos:
        print(f"{v['nome']}: edital novo: {titulo} {link}")
        if base is not None:
            registar_pendencia(base, f"{v['nome']}: edital novo «{titulo[:200]}».", v["verificar"], link,
                               origem="vigiar.py")


def main():
    import os
    if os.environ.get("SECO"):  # ensaio: só as vigias por notícias, sem planilha
        for v in VIGIAS:
            if v.get("rss"):
                vigiar_rss(None, v)
        return 0
    base = Base()
    carregar_config(base)
    for v in VIGIAS:
        if v.get("rss"):
            vigiar_rss(base, v)
            continue
        if v.get("wp"):
            vigiar_wp(base, v)
            continue
        if v.get("itens"):
            vigiar_itens(base, v)
            continue
        try:
            html = baixar(v["url"], timeout=40).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"{v['nome']}: a página não abriu ({type(e).__name__}); fica para amanhã.")
            continue
        if v.get("contar_json"):
            try:
                dado = json.loads(html)
                for k in v.get("caminho", []):
                    dado = dado[k]
                n = dado if isinstance(dado, int) else len(dado)
            except (ValueError, KeyError, TypeError):
                print(f"{v['nome']}: a resposta não é a lista esperada; fica para amanhã.")
                continue
            if not n:
                print(f"{v['nome']}: continua sem turmas.")
                continue
            print(f"{v['nome']}: {n} turmas.")
            registar_pendencia(base, f"{v['nome']}: apareceram {n} turmas.", v["verificar"], v["link"] + "#psg",
                               origem="vigiar.py")
            continue
        if v["fechado"].lower() in html.lower():
            print(f"{v['nome']}: continua sem inscrições abertas.")
            continue
        print(f"{v['nome']}: a frase de «fechado» sumiu da página.")
        registar_pendencia(base, f"{v['nome']}: a página oficial mudou e já não diz «{v['fechado']}» "
                                 "(provavelmente abriu inscrições).",
                           v["verificar"], v["url"] + "#mudou", origem="vigiar.py")
    base.guardar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
