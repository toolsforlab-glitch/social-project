"""Temporário (27/11/2026): aplica a auditoria 5 do ChatGPT (Centro-Oeste). Frases conferidas por código aqui quando a
página abre a partir do GitHub; a do IFMS (recusa o GitHub e a VPN) foi conferida pelo Claude no Chrome sem VPN."""
import io, sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from pypdf import PdfReader
from turmas import hoje_ceara

def txt(u):
    b = baixar(u, timeout=40)
    if b[:4] == b"%PDF":
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
    return texto_de_html(b)

hoje = hoje_ceara()
falhas = []
def conf(frases, url):
    try:
        t = txt(url)
    except Exception as e:  # noqa: BLE001
        falhas.append(f"{url} não abriu ({type(e).__name__})"); return {}
    ok = {}
    for k, f in frases.items():
        if citacao_valida(f, t): ok[k] = f
        else: falhas.append(f"{k}: frase não confere em {url}")
    return ok

LDB = "https://legis.senado.gov.br/norma/551270/publicacao/34619663"
fldb = conf({"gratuito": "assegurarão gratuitamente aos jovens e aos adultos"}, LDB)
IFMT = "https://ifmt.edu.br/blog/abertas-inscricoes-para-96-vagas-em-cursos-tecnicos-subsequentes-em-6-campi/"
SOBRE = "https://ifmt.edu.br/estude-no-ifmt/sobre/"
fifmt = conf({"data": "No período de 23 de novembro até 13 de dezembro de 2026, estarão abertas as inscrições para o processo seletivo de vagas remanescentes dos cursos Técnicos Subsequentes ao Ensino Médio do IFMT",
              "vagas": "se inscrever para assistir presencialmente o sorteio público que ocorrerá no dia 17 de dezembro de 2026",
              "requisito": "ter concluído o ensino médio ou equivalente até a data da matrícula",
              "matrícula": "A matrícula dos aprovados será realizada entre 12 e 14 de janeiro de 2027."}, IFMT)
fsobre = conf({"gratuito": "Sim, todos os nossos cursos de nível médio, graduação e pós-graduação lato e stricto sensu são gratuitos."}, SOBRE)
GYN = "https://sme.goiania.go.gov.br/site/index.php/institucional/ultimas-noticias/3320-prefeitura-de-goiania-divulga-cronograma-de-matriculas-para-o-ano-letivo-de-2027"
fgyn = conf({"abertura": "Solicitação de vagas – Ensino Fundamental e EJA: 04/01/2027, às 12h"}, GYN)
SAM = "https://www.ifb.edu.br/samambaia/49122-curso-tecnico-em-edificacoes-eja-ept-2027"
fsam = conf({"local": "também de forma on-line ou presencial"}, SAM)
SINJ = "https://www.sinj.df.gov.br/sinj/Diario/405f76ef-1040-3efc-9852-036b7736aa52/visualizar-pdf%2015.pdf"
fsinj = conf({"vagas": "havendo empate entre os ranqueados, haverá sorteio eletrônico"}, SINJ)
print("FALHAS:", falhas)

base = Base(); carregar_config(base)
L = base.tabela("Cursos"); por_id = {r.get("ID"): r for r in L}
novos, alter = [], []

# --- IFMT: cursos técnicos subsequentes (vagas remanescentes, Edital 234/2026)
if len(fifmt) == 4 and fsobre:
    ev = [f"gratuito: «{fsobre['gratuito']}» ({SOBRE})"] + [f"{k}: «{v}» ({IFMT})" for k, v in fifmt.items()]
    for curso, cid, campus in [("Agropecuária", "Cáceres", "Cáceres – Professor Olegário Baldo"), ("Agropecuária", "Campo Novo do Parecis", "Campo Novo do Parecis"),
                               ("Agropecuária", "Confresa", "Confresa"), ("Biocombustíveis", "Confresa", "Confresa"),
                               ("Hospedagem", "Cuiabá", "Cuiabá – Cel. Octayde Jorge da Silva"), ("Qualidade", "Lucas do Rio Verde", "Lucas do Rio Verde"),
                               ("Manutenção Aeronáutica em Célula", "Primavera do Leste", "Primavera do Leste")]:
        T = f"Técnico em {curso} (subsequente, para quem já terminou o ensino médio) – IFMT Campus {campus}"
        ident = id_curso(IFMT, T)
        if ident in por_id:
            continue
        novos.append({"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Instituto Federal de Mato Grosso (IFMT)",
            "Link": IFMT, "Página do curso": IFMT, "Destino do link": "curso", "Local": "BR-MT", "Modalidade": "presencial",
            "País": "BR", "Região": "Mato Grosso", "Cidade": cid,
            "Descrição": (f"Curso técnico gratuito em {curso} no IFMT de {cid}, para quem já terminou o ensino médio. São vagas que "
                          f"sobraram (96 no total em 6 campi); as vagas saem por sorteio público a 17 de dezembro e a matrícula é em janeiro de 2027."),
            "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "Ter terminado o ensino médio (ou equivalente) até à matrícula", "Certificado": "desconhecido",
            "Inscrições até": "2026-12-13", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje,
            "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (pista da auditoria 5 do ChatGPT; Edital 234/2026 do IFMT; frases conferidas por código).",
            "Como me inscrever": ("1. Até 13/12/2026, inscreva-se no site de seleção do IFMT (seletivo.ifmt.edu.br), no Edital 234/2026, "
                                  "escolhendo o campus e o curso.\n2. Se houver mais inscritos do que vagas, há sorteio público a "
                                  "17/12/2026; o resultado sai a 21/12.\n3. A matrícula dos aprovados é de 12 a 14/01/2027."),
            "Nota da verificação": f"{hoje}: notícia oficial do IFMT e página «Estude no IFMT» lidas por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas", "Mudança a rever": "FALSE",
            "O que falta confirmar": "O número de vagas e o turno de cada curso estão no Edital 234/2026, que não abriu a partir daqui."})

# --- EJA da rede municipal de Goiânia (Por abrir, 04/01/2027)
if fldb and fgyn:
    T = "Matrícula 2027 na EJA da rede municipal de Goiânia"
    ident = id_curso(GYN, T)
    if ident not in por_id:
        novos.append({"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Prefeitura de Goiânia – Secretaria Municipal de Educação",
            "Link": GYN, "Página do curso": GYN, "Destino do link": "curso", "Local": "BR-GO", "Modalidade": "presencial", "País": "BR",
            "Região": "Goiás", "Cidade": "Goiânia",
            "Descrição": ("Para jovens, adultos e idosos que querem terminar o ensino fundamental na escola pública municipal de "
                          "Goiânia. O pedido de vaga para 2027 abre a 4 de janeiro, ao meio-dia."),
            "Origem da descrição": "Resumo", "Necessidades": "escola", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "", "Certificado": "desconhecido", "Inscrições abrem em": "2027-01-04", "Inscrições até": "", "Início": "",
            "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial",
            "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (pista da auditoria 5 do ChatGPT; frases conferidas por código).",
            "Como me inscrever": ("1. A partir de 04/01/2027, às 12h, peça a vaga na EJA pelo sistema de matrículas da Prefeitura de "
                                  "Goiânia (o endereço sai no site da Secretaria Municipal de Educação).\n2. Depois, confirme a "
                                  "matrícula na escola indicada."),
            "Nota da verificação": f"{hoje}: notícia oficial da SME Goiânia lida por código; frase conferida.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Por abrir", "Verificar automaticamente": "FALSE",
            "Evidência": f"abertura: «{fgyn['abertura']}» ({GYN}) | gratuito: «{fldb['gratuito']}» ({LDB})",
            "Campos comprovados": "abertura, gratuito", "Mudança a rever": "FALSE",
            "O que falta confirmar": "A notícia não diz até quando se pode pedir vaga nem o endereço do sistema de matrículas."})

# --- IFB Samambaia e Taguatinga: local da inscrição
r = por_id.get("C-c8f3c51e")
if r and fsam:
    alter.append((r["_linha"], {"Como me inscrever": r["Como me inscrever"].replace(
        "no IFB Campus Samambaia (Rodovia DF-460, Subcentro Leste, Complexo Boca da Mata, Lote 2) ou online",
        "on-line ou presencialmente no IFB Campus Samambaia (Rodovia DF-460, Subcentro Leste, Complexo Boca da Mata, Lote 2)"),
        "Evidência": (r["Evidência"] + f" | local: «{fsam['local']}» ({SAM})")[:1800],
        "O que falta confirmar": ("As inscrições de dezembro são para as vagas de ampla concorrência que sobrarem depois das cotas; "
                                  "fecham quando a turma enche."),
        "Nota da verificação": f"{hoje}: auditoria 5: a página do curso diz que a inscrição é on-line ou presencial no Campus Samambaia (conferido por código)."}))
r = por_id.get("C-e1f3a6b7")
if r:
    alter.append((r["_linha"], {"O que falta confirmar": (
        "As inscrições de dezembro são para as vagas de ampla concorrência que sobrarem depois das cotas; fecham quando a turma "
        "enche. A página geral do IFB fala no Campus Gama; o Anexo C do edital (no Google Drive do IFB) indica o Campus Taguatinga "
        "(QNM 40, Área Especial nº 01) e um formulário on-line: confirme na página do curso.")}))

# --- IFMS: frase oficial de gratuidade (conferida no Chrome sem VPN; o IFMS recusa o GitHub)
F_IFMS = "Todos os cursos oferecidos são inteiramente gratuitos."
for r in L:
    if (r.get("Link") or "").startswith("https://selecao.ifms.edu.br/perfil/estudantes/edital-73-2026") and F_IFMS not in (r.get("Evidência") or ""):
        alter.append((r["_linha"], {"Evidência": (f"gratuito: «{F_IFMS}» (https://selecao.ifms.edu.br/perguntas) | " + r["Evidência"])[:1800],
                                    "Nota da verificação": f"{hoje}: auditoria 5: frase de gratuidade do IFMS conferida pelo Claude no navegador (sem VPN)."}))

# --- Jornada da Mulher Trabalhadora (DF): como se preenchem as vagas
r = por_id.get("C-f928d51a")
if r and fsinj:
    alter.append((r["_linha"], {"Evidência": (r["Evidência"] + f" | vagas: «{fsinj['vagas']}» ({SINJ})")[:1800],
        "O que falta confirmar": ("Pelo Edital de Chamamento Público nº 36/2026, as candidatas são classificadas pelos requisitos do "
                                  "edital, com sorteio eletrónico em caso de empate; a ordem de inscrição vale para a pré-matrícula."),
        "Nota da verificação": f"{hoje}: auditoria 5: Edital 36/2026 lido por código (classificação pelos requisitos, sorteio no empate)."}))

base.atualizar("Cursos", alter)
base.acrescentar("Cursos", novos)
base.guardar()
print("novos:", len(novos), [n["Título"][:50] for n in novos]); print("alterados:", len(alter))
