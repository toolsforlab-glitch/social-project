"""Editais do Programa Senac de Gratuidade do Maranhão (Senac MA) e do Acre (Senac AC): turmas lidas do documento
oficial. A lista de editais muda de um Senac para o outro (Maranhão: lista pública em JSON; Acre: página com os PDFs
no separador «Aberto», sem datas); a leitura, a prova por código e a auditoria são as mesmas (ver FONTES).

O Senac MA publica um edital por oferta (cerca de três por semana), com um documento (PDF ou Word) que diz o
período de inscrição, onde e como se inscrever e, no Anexo I, os cursos com datas, horário, vagas e local.
O site tem uma lista pública dos editais (ma.senac.br/v1/public/notices). Este script:

1. lê a lista e escolhe os editais recentes que ainda não foram tratados;
2. tira o texto do documento (PDF: pypdf; Word antigo: antiword; Word novo: o XML do ficheiro);
3. pede ao Claude que extraia o período de inscrição, o modo e o local, e cada curso do Anexo I, SEMPRE com a
   frase exata do documento;
4. confere por código cada frase no texto do documento, e que a frase de cada curso contém o nome do curso e a
   data de início; o que não se confirma é deitado fora;
5. AUDITORIA antes de publicar: datas válidas e coerentes (início ≤ fim da inscrição, inscrição perto da data do
   edital, aulas depois da inscrição), horário com sentido, cidade escrita no documento;
6. grava uma linha por curso no separador Turmas e cria o curso em Cursos (Local BR-MA). O curso é publicado
   sozinho quando tem turma aberta aprovada e o documento diz que é do Programa Senac de Gratuidade;
7. termo aditivo: as turmas do edital alterado passam a Rever (o aditivo muda prazos), até uma pessoa rever.

A situação de cada turma vem só das datas do documento: Aberta até ao fim do dia em que a inscrição termina.
O selo "aberto/encerrado" da lista do Senac não é usado.
"""
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import zipfile
import html as _html

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, perfis_da_frase, sim
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json, gravar_json, ler_json
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

# Cada Senac regional publica os editais do Programa Senac de Gratuidade à sua maneira; o resto é igual.
FONTES = [
    {"nome": "Senac MA", "uf": "MA", "local": "BR-MA", "regiao": "Maranhão",
     "entidade": "Senac Maranhão (Programa Senac de Gratuidade)", "estado": "estado/senac_ma.json",
     "lista": "https://ma.senac.br/editais-psg/", "prefixo_turma": "https://ma.senac.br/editais_psg/",
     "api": "https://ma.senac.br/v1/public/notices?type=psg&page=1&per_page=30", "site": "https://ma.senac.br"},
    {"nome": "Senac AC", "uf": "AC", "local": "BR-AC", "regiao": "Acre",
     "entidade": "Senac Acre (Programa Senac de Gratuidade)", "estado": "estado/senac_ac.json",
     "lista": "https://portal.ac.senac.br/psg/editais", "prefixo_turma": "https://portal.ac.senac.br/psg/assets/arquivos/"},
    {"nome": "Senai MA", "uf": "MA", "local": "BR-MA", "regiao": "Maranhão",
     "entidade": "Senai Maranhão (Programa SENAI de Gratuidade Regimental)", "estado": "estado/senai_ma.json",
     "programa": "Programa SENAI de Gratuidade Regimental", "listar": "senai_ma",
     "lista": "https://www.fiema.org.br/editais/11/Processos+Seletivos+-+Alunos",
     "prefixo_turma": "https://www.fiema.org.br/edital/"},
]
MESES = {m: i + 1 for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                                          "setembro", "outubro", "novembro", "dezembro"])}
MAX_RECENTES_SEM_DATA = 20  # Acre: a lista não tem datas; só os 20 editais mais recentes do ano entram
DIAS_RECENTES = 15       # inscrições duram 3 a 7 dias: editais mais antigos já não têm inscrição aberta
MAX_POR_EXECUCAO = 12    # limite de documentos lidos com o Claude por execução (controla o custo)
MAX_CARACTERES = 30000
DIAGNOSTICO = os.environ.get("SENAC_MA_DIAGNOSTICO", "")  # pasta onde guardar texto e resposta de cada edital
MAX_TENTATIVAS = 2       # um edital sem nada comprovado é relido uma vez; à segunda fica de lado

SISTEMA = """Extrais dados de um edital oficial do Senac Maranhão (Programa Senac de Gratuidade) para uma base \
de dados pública. Cada valor que devolves vai ser conferido por código no texto do edital: só conta se vier \
acompanhado da frase EXATA do documento (copiada letra a letra, sem corrigir erros, até 40 palavras).

Regras:
- Nunca deduzas. Se o edital não diz, devolve null.
- O período de inscrição é o do processo seletivo (item "DA INSCRIÇÃO"), não as datas das aulas.
- Datas no formato AAAA-MM-DD. Se o documento tiver um erro evidente numa data (ex.: "10/02/20227"), devolve \
null nesse campo.
- "modo": "presencial" se a inscrição é feita num local físico, "online" se é pela internet, "ambos" se o \
edital disser as duas, null se não disser.
- Em "turmas", uma entrada por curso e turno do Anexo I (ou do anexo com a tabela dos cursos) ("PROGRAMAÇÃO DOS CURSOS E TURNOS"; a tabela pode \
aparecer com as células separadas por " | " numa só linha: copia a linha com os " | "). Se o edital tem \
cursos, "turmas" nunca vem vazio. "frase" é o texto da linha do Anexo I desse curso, \
copiado tal como aparece no texto que recebes (começa no nome do curso e inclui a data de início das aulas).
- "cidade": o município onde o curso decorre, como está escrito no edital.
- "gratuidade": a frase exata do edital que diz que o curso é do Programa Senac de Gratuidade ou gratuito.
- "renda": a frase exata com o critério de renda, se existir.
- "reserva": a frase exata que reserva vagas ou dá prioridade a um grupo de pessoas (ex.: pessoas com deficiência, \
mulheres, pessoas negras, quilombolas), se existir; senão null.

Devolve só JSON entre <json></json>:
{"inscricao": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD", "frase": "..."} ou null,
 "modo": "presencial|online|ambos" ou null, "local_inscricao": "..." ou null, "frase_local": "..." ou null,
 "gratuidade": "..." ou null, "renda": "..." ou null, "reserva": "..." ou null,
 "turmas": [{"curso": "...", "cidade": "...", "inicio_aulas": "AAAA-MM-DD" ou null, "fim_aulas": "AAAA-MM-DD" ou null,
   "horario": "..." ou null, "dias": "..." ou null, "vagas": "..." ou null, "carga_horaria": "..." ou null,
   "local_curso": "..." ou null, "frase": "..."}]}"""


# ------------------------------------------------------------------ documento

def texto_do_documento(dados, tipo):
    """Texto de um PDF, Word antigo (.doc) ou Word novo (.docx)."""
    if "pdf" in tipo or dados[:4] == b"%PDF":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(dados)).pages)
    if dados[:4] == b"PK\x03\x04":  # .docx
        return texto_docx(dados)
    # Word antigo (.doc): o LibreOffice converte para .docx sem perder as linhas das tabelas (o antiword perde
    # as linhas do Anexo I quando a tabela tem um título em células unidas); o antiword fica como recurso
    with tempfile.TemporaryDirectory() as pasta:
        origem = os.path.join(pasta, "edital.doc")
        with open(origem, "wb") as f:
            f.write(dados)
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "docx", "--outdir", pasta, origem],
                           capture_output=True, timeout=120)
            with open(os.path.join(pasta, "edital.docx"), "rb") as f:
                return texto_docx(f.read())
        except (OSError, subprocess.SubprocessError):
            return subprocess.run(["antiword", "-w", "0", origem], capture_output=True, text=True,
                                  timeout=60).stdout


def texto_docx(dados):
    """Texto de um .docx com cada linha de tabela numa só linha (células separadas por " | ")."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")

    def linha(m):
        celulas = re.findall(r"<w:tc\b.*?</w:tc>", m.group(0), flags=re.S)
        return " | ".join(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"</w:p>", " ", c))).strip()
                          for c in celulas) + "\n"
    xml = re.sub(r"<w:tr\b.*?</w:tr>", linha, xml, flags=re.S)
    xml = re.sub(r"<w:tab/>", " ", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    texto = re.sub(r"<[^>]+>", "", xml)
    return _html.unescape(texto)


def recortar(texto):
    """Os editais longos são cortados no meio, nunca no fim: o Anexo I (a tabela dos cursos) fica no fim."""
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n+", "\n", texto)
    if len(texto) <= MAX_CARACTERES:
        return texto
    anexo = [m.start() for m in re.finditer(r"ANEXO\s+I\b", texto)]
    inicio_anexo = anexo[-1] if anexo else len(texto) - MAX_CARACTERES // 2
    cauda = texto[inicio_anexo:inicio_anexo + MAX_CARACTERES // 2]
    return texto[:MAX_CARACTERES - len(cauda)] + "\n[...]\n" + cauda


def data_br(iso):
    try:
        return datetime.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""


def data_valida(iso):
    try:
        datetime.date.fromisoformat(str(iso))
        return str(iso)
    except (TypeError, ValueError):
        return ""


def horario_curto(h):
    m = re.findall(r"(\d{1,2})\s*(?:[:hH]\s*(\d{2}))?", h or "")
    horas = [(int(a), int(b or 0)) for a, b in m if a and int(a) <= 23][:2]
    return f"{horas[0][0]:02d}:{horas[0][1]:02d} - {horas[1][0]:02d}:{horas[1][1]:02d}" if len(horas) == 2 else ""


MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_cidade(c):
    """'SÃO DOMINGOS DO MARANHÃO/MA' → 'São Domingos do Maranhão' (o edital escreve a cidade de várias formas)."""
    c = re.sub(r"\s*(?:[/,–-]\s*|\()(MA|AC|Maranh[ãa]o|Acre)\)?\s*$", "", re.sub(r"\s+", " ", c or "").strip(),
               flags=re.I).strip(" -–/")
    if c.isupper() or c.islower():
        c = " ".join(p.lower() if i and p.lower() in MINUSCULAS else p.capitalize()
                     for i, p in enumerate(c.split(" ")))
    return c


def horario_confirmado(h, frase):
    """Horário normalizado, só se as horas aparecerem na frase do Anexo I."""
    curto = horario_curto(h)
    if not curto:
        return ""
    horas = {int(x) for x in re.findall(r"\d{1,2}", re.sub(r"\d{1,2}/\d{1,2}/\d{2,5}", " ", frase))}
    return curto if int(curto[:2]) in horas and int(curto[8:10]) in horas else ""


# ------------------------------------------------------------------ prova e auditoria

def provar(res, texto, publicado):
    """Fica só o que está escrito no documento. Devolve (dados limpos, problemas do edital)."""
    problemas = []
    insc = res.get("inscricao") if isinstance(res.get("inscricao"), dict) else {}
    ini, fim, frase_insc = data_valida(insc.get("inicio")), data_valida(insc.get("fim")), str(insc.get("frase") or "")
    if not (ini and fim and citacao_valida(frase_insc, texto) and data_br(fim)[:5] in frase_insc.replace(" ", "")):
        problemas.append("o período de inscrição não foi confirmado no documento")
        ini = fim = ""
    elif ini > fim:
        problemas.append(f"o fim da inscrição ({fim}) é anterior ao início ({ini})")
    elif publicado and not (publicado[:10] <= fim <= (datetime.date.fromisoformat(publicado[:10])
                                                         + datetime.timedelta(days=60)).isoformat()):
        problemas.append(f"o fim da inscrição ({fim}) não está perto da data do edital ({publicado[:10]})")
    local = str(res.get("local_inscricao") or "") if citacao_valida(str(res.get("frase_local") or ""), texto) else ""
    modo = res.get("modo") if res.get("modo") in ("presencial", "online", "ambos") else ""
    if modo in ("presencial", "ambos") and not local:
        modo = ""  # inscrição presencial sem local comprovado não serve a ninguém
    gratuito = citacao_valida(str(res.get("gratuidade") or ""), texto) and "gratuid" in str(res.get("gratuidade")).lower()
    if not gratuito:
        # o nome do programa está escrito no próprio documento: a prova é o texto, conferido por código
        m = re.search(r"[^.\n]{0,80}(?:programa\s+senac\s+de\s+gratuidade|gratuidade\s+regimental)[^.\n]{0,80}",
                      texto, flags=re.I)
        if m:
            gratuito, res["gratuidade"] = True, re.sub(r"\s+", " ", m.group(0)).strip()
    renda = str(res.get("renda") or "") if citacao_valida(str(res.get("renda") or ""), texto) else ""
    reserva = str(res.get("reserva") or "") if citacao_valida(str(res.get("reserva") or ""), texto) else ""
    if not perfis_da_frase(reserva):
        reserva = ""  # a frase tem de nomear um grupo que conhecemos
    turmas = []
    for t in res.get("turmas") or []:
        if not isinstance(t, dict):
            continue
        frase, curso = str(t.get("frase") or ""), str(t.get("curso") or "").strip()
        inicio = data_valida(t.get("inicio_aulas"))
        if not curso or not citacao_valida(frase, texto) or chave(curso) not in chave(frase):
            continue
        if inicio and data_br(inicio) not in re.sub(r"\s", "", frase):
            inicio = ""
        cidade = str(t.get("cidade") or "").strip()
        cidade = nome_cidade(cidade) if cidade and chave(cidade) in chave(texto) else ""
        turmas.append({**t, "curso": curso, "inicio_aulas": inicio, "cidade": cidade,
                       "fim_aulas": data_valida(t.get("fim_aulas")),
                       "horario": horario_confirmado(t.get("horario"), frase)})
    return {"ini": ini, "fim": fim, "frase_insc": frase_insc if fim else "", "local": local, "modo": modo,
            "gratuito": gratuito, "renda": renda, "reserva": reserva, "turmas": turmas}, problemas


def auditar(t, edital, problemas_edital):
    p = list(problemas_edital)
    if not edital["fim"]:
        p.append("sem período de inscrição comprovado")
    if not t["inicio_aulas"]:
        p.append("sem data de início das aulas comprovada")
    elif edital["fim"] and t["inicio_aulas"] < edital["ini"]:
        p.append(f"as aulas começam ({t['inicio_aulas']}) antes de abrir a inscrição ({edital['ini']})")
    if t.get("fim_aulas") and t["inicio_aulas"] and t["fim_aulas"] < t["inicio_aulas"]:
        p.append(f"o fim das aulas ({t['fim_aulas']}) é anterior ao início ({t['inicio_aulas']})")
    if not t["cidade"]:
        p.append("a cidade do curso não foi confirmada no documento")
    if not edital["modo"]:
        p.append("o documento não confirma como e onde se faz a inscrição")
    h = re.match(r"(\d{2}):(\d{2}) - (\d{2}):(\d{2})", t.get("horario") or "")
    if h and (int(h.group(1)) < 5 or h.group(1) + h.group(2) >= h.group(3) + h.group(4)):
        p.append(f"o horário ({t['horario']}) não faz sentido")
    return p


# ------------------------------------------------------------------ principal

def listar_ma(fonte):
    dados = json.loads(baixar(fonte["api"], timeout=40).decode("utf-8"))["data"]
    for e in dados:
        n = numero_alterado(e.get("number"))
        e["pagina"] = fonte["site"] + (e.get("path") or "")
        e["padrao"] = rf"edital-psg-n[ºo°]?-?{n}-"
        e["aditivo"] = "TERMO" in str(e.get("number", "")).upper() or any(
            d.get("type") == "aditivo" for d in e.get("documents") or [])
        for d in e.get("documents") or []:
            d["url"] = fonte["site"] + d["url"] if d.get("url", "").startswith("/") else d.get("url", "")
    return dados


def listar_ac(fonte):
    """Senac Acre: a página lista, no separador «Aberto», os editais do ano com o PDF e os avisos (prorrogação,
    alteração de vagas). Não tem datas: o período de inscrição vem sempre do próprio PDF."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    inicio = html.find('id="abertos"')
    fim = html.find('id="emAndamento"', inicio)
    if inicio < 0:
        raise ValueError("separador «Aberto» não encontrado")
    ano = hoje_ceara()[:4]
    por_numero = {}
    for card in html[inicio:fim if fim > 0 else None].split('<div class="card">')[1:]:
        titulo = re.search(r'card-header.*?</i>(.*?)</div>', card, flags=re.S)
        titulo = _html.unescape(re.sub(r"\s+", " ", titulo.group(1))).strip() if titulo else ""
        for href in re.findall(r'href="([^"]+\.pdf)"', card, flags=re.I):
            url = href if href.startswith("http") else "https://portal.ac.senac.br" + href
            url = urllib.parse.quote(_html.unescape(url), safe=":/%")  # os nomes têm espaços e acentos
            m = re.search(r"Edital_PSG_(\d{2,3})_(\d{4})", url, flags=re.I)
            if not m or m.group(2) != ano or re.search(r"lista|matriculad|classifica|resultado", url, flags=re.I):
                continue
            g = por_numero.setdefault(int(m.group(1)), {"edital": "", "avisos": [], "titulo": titulo})
            if re.search(r"aviso|retifica|prorroga|altera|errata", url, flags=re.I):
                g["avisos"].append(url)
            elif not g["edital"]:
                g["edital"] = url
    editais = []
    for n in sorted(por_numero, reverse=True)[:MAX_RECENTES_SEM_DATA]:
        g = por_numero[n]
        padrao = rf"Edital_PSG_0*{n}_{ano}"
        if g["edital"]:
            editais.append({"id": f"ac-{ano}-{n}", "updated_at": g["edital"].rsplit("/", 1)[-1], "number": f"{n:03d}",
                            "published_at": "", "title": g["titulo"] or f"Edital PSG nº {n:03d}/{ano} do Senac Acre",
                            "pagina": g["edital"], "padrao": padrao, "aditivo": False, "tem_aviso": bool(g["avisos"]),
                            "documents": [{"type": "edital", "mime_type": "application/pdf", "url": g["edital"]}]})
        for a in g["avisos"]:
            editais.append({"id": f"ac-{ano}-{n}", "updated_at": a.rsplit("/", 1)[-1], "number": f"{n:03d}-AVISO",
                            "published_at": "", "title": "Aviso", "pagina": a, "padrao": padrao, "aditivo": True,
                            "documents": [{"type": "aditivo", "mime_type": "application/pdf", "url": a}]})
    return editais


def data_por_extenso(t):
    """'5 de outubro de 2026' → '2026-10-05'."""
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", (t or "").lower())
    return f"{m.group(3)}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in MESES else ""


def listar_senai_ma(fonte):
    """Senai Maranhão: a lista «Processos Seletivos – Alunos» (fiema.org.br) dá o código, a data de publicação e o
    período de inscrição de cada edital. Só entram os do Programa SENAI de Gratuidade Regimental com inscrição ainda
    aberta; o documento (PDF) está na página de cada edital."""
    html = baixar(fonte["lista"] + "?page=1&per-page=30", timeout=60).decode("utf-8", "replace")
    hoje = hoje_ceara()
    editais = []
    padrao = (r'<a href="(/edital/(\d+)/[^"]+)" title="([^"]+)">.*?C[óo]digo:</strong>\s*([^<]+)<br.*?'
              r'Data de Publica[çc][ãa]o: </strong>\s*([^<]+)<br.*?Data de In[íi]cio: </strong>\s*([^<]+?)\s*<br.*?'
              r'Data Fim: </strong>\s*([^<]+?)\s*<br')
    for caminho, num, titulo, codigo, pub, ini, fim in re.findall(padrao, html, flags=re.S):
        titulo = _html.unescape(titulo)
        ini, fim, pub = data_por_extenso(ini), data_por_extenso(fim), data_por_extenso(pub)
        if "GRATUIDADE" not in titulo.upper() or not fim or fim < hoje:
            continue
        pagina = "https://www.fiema.org.br" + caminho
        detalhe = baixar(pagina, timeout=60).decode("utf-8", "replace")
        pdfs = re.findall(r'href="(/uploads/edital/\d+/[^"]+\.pdf)"', detalhe, flags=re.I)
        if not pdfs:
            continue
        editais.append({"id": f"senai-ma-{num}", "updated_at": pdfs[0].rsplit("/", 1)[-1],
                        "number": _html.unescape(codigo).strip(), "published_at": pub, "title": titulo,
                        "pagina": pagina, "padrao": re.escape(f"/edital/{num}/"), "aditivo": False,
                        "periodo_lista": (ini, fim),
                        "documents": [{"type": "edital", "mime_type": "application/pdf",
                                       "url": "https://www.fiema.org.br" + pdfs[0]}]})
    return editais


def numero_alterado(n):
    m = re.match(r"(\d+)", str(n or ""))
    return m.group(1) if m else ""


def main():
    for fonte in FONTES:
        correr(fonte)
    return 0


def correr(fonte):
    base = Base()
    cfg = carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    modelo = cfg.get("modelo_cursos") or "claude-haiku-5-5"
    estado = ler_json(fonte["estado"], {"tratados": {}})
    try:
        editais = {"senai_ma": listar_senai_ma}.get(fonte.get("listar"), listar_ma if fonte.get("api") else listar_ac)(fonte)
    except Exception as e:  # noqa: BLE001
        print(f"{fonte['nome']}: a lista de editais não abriu ({type(e).__name__}: {e}). Nada alterado.")
        editais = []
    corte = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_RECENTES)).isoformat()

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(fonte["lista"])]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(fonte["prefixo_turma"])}

    novas, alteracoes, cursos_novos, historico, custo = [], [], [], [], 0.0
    gratuidade_provada = {}
    lidos = 0
    for e in editais:
        chave_estado = f"{e.get('id')}|{e.get('updated_at')}"
        feito = estado["tratados"].get(chave_estado)
        if (e.get("published_at") and e["published_at"][:10] < corte) or (feito and (not isinstance(feito, dict)
                                                                       or feito.get("tentativas", 0) >= MAX_TENTATIVAS
                                                                       or feito.get("cursos"))):
            continue
        docs = e.get("documents") or []
        pagina = e["pagina"]
        # termo aditivo ou aviso de alteração: as turmas do edital alterado vão para Rever
        if e.get("aditivo"):
            n = numero_alterado(e.get("number"))
            nota = f"{hoje}: saiu um termo aditivo ou aviso ao edital nº {n} ({pagina}); confirmar prazos e turmas antes de publicar."
            for link, t in existentes.items():
                if re.search(e["padrao"], link, flags=re.I) and t.get("Estado") == "Publicado":
                    alteracoes.append((t["_linha"], {"Estado": "Rever", "Notas": nota}))
                    historico.append(registo(t, fonte["nome"], "Rever", nota))
            estado["tratados"][chave_estado] = hoje
            continue
        if not docs or lidos >= MAX_POR_EXECUCAO:
            continue
        doc = docs[0]
        try:
            dados = baixar(doc["url"], timeout=60)
            texto = recortar(texto_do_documento(dados, doc.get("mime_type", "")))
        except Exception as ex:  # noqa: BLE001
            print(f"  ✗ edital {e.get('number')}: documento ilegível ({type(ex).__name__})")
            continue
        if len(texto.strip()) < 500:
            print(f"  ✗ edital {e.get('number')}: o documento não tem texto legível (pode ser digitalizado)")
            estado["tratados"][chave_estado] = hoje
            continue
        try:
            sistema = SISTEMA.replace("Senac Maranhão (Programa Senac de Gratuidade)", fonte["entidade"]).replace(
                "Programa Senac de Gratuidade", fonte.get("programa", "Programa Senac de Gratuidade"))
            resposta, uso = claude(modelo, sistema, f"Título do edital: {e.get('title')}\n\nTexto do edital:\n{texto}",
                                   max_tokens=6000)
        except ErroClaude as ex:
            print(f"  ERRO no Claude (edital {e.get('number')}): {ex}")
            continue
        lidos += 1
        custo += custo_estimado(uso, modelo)
        res = extrair_json(resposta)
        if not isinstance(res, dict):
            print(f"  ? edital {e.get('number')}: resposta ilegível; volta a tentar na próxima execução")
            continue
        edital, problemas = provar(res, texto, e.get("published_at") or "")
        if e.get("periodo_lista") and edital["fim"] and edital["fim"] != e["periodo_lista"][1]:
            # segunda prova: a lista oficial também diz até quando há inscrição; têm de coincidir
            problemas.append(f"o fim da inscrição no documento ({edital['fim']}) não coincide com a lista oficial "
                             f"({e['periodo_lista'][1]})")
        if DIAGNOSTICO:
            os.makedirs(DIAGNOSTICO, exist_ok=True)
            with open(os.path.join(DIAGNOSTICO, f"{e.get('id')}.json"), "w", encoding="utf-8") as f:
                json.dump({"edital": e, "texto": texto, "resposta": resposta}, f, ensure_ascii=False, indent=1)
        propostas = len(res.get("turmas") or [])
        if not edital["turmas"]:  # para se perceber no registo da execução porque não ficou nenhum curso
            m = list(re.finditer(r"ANEXO\s+I\b", texto.upper()))
            pos = m[-1].start() if m else -1
            print(f"    texto com {len(texto)} caracteres; Anexo I na posição {pos}: "
                  + re.sub(r"\s+", " ", texto[pos:pos + 1500] if pos >= 0 else texto[-1500:]))
            for t in (res.get("turmas") or [])[:3]:
                print(f"    proposta não comprovada: {str(t)[:300]}")
        print(f"  edital nº {e.get('number')} ({(e.get('published_at') or '')[:10]}): inscrição "
              f"{edital['ini'] or '?'} a {edital['fim'] or '?'}, modo {edital['modo'] or '?'}, "
              f"{len(edital['turmas'])}/{propostas} cursos comprovados" + (f" | {'; '.join(problemas)}" if problemas else ""))
        for t in edital["turmas"]:
            link = f"{pagina}#{re.sub(r'[^a-z0-9]+', '-', chave(t['curso'] + ' ' + (t.get('horario') or ''))).strip('-')}"
            k = chave(t["curso"])
            if k in ocultos:
                continue
            p = auditar(t, edital, problemas)
            if e.get("tem_aviso"):
                p.append("o edital tem aviso de prorrogação ou alteração: confirmar prazos e vagas")
            situacao = "Aberta" if edital["fim"] and hoje <= edital["fim"] else "Encerrada"
            campos = {
                "Título na fonte": t["curso"], "Unidade na fonte": t.get("local_curso") or "", "Cidade": t["cidade"],
                "Unidade": "", "Link de matrícula": "", "Início": t["inicio_aulas"], "Fim": t.get("fim_aulas") or "",
                "Horário": t.get("horario") or "", "Dias": str(t.get("dias") or ""), "Vagas": str(t.get("vagas") or ""),
                "Carga horária": str(t.get("carga_horaria") or ""), "Prazo de inscrição": edital["fim"],
                "Idade mínima": "", "Escolaridade": "", "Documentos": "",
                "Mais informações": (f"Inscrições de {data_br(edital['ini'])} a {data_br(edital['fim'])}"
                                     if edital["fim"] else ""),
                "Local na fonte": edital["local"], "Modo de inscrição": edital["modo"], "Situação": situacao,
                "Vagas reservadas": edital["reserva"][:300],
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": (f"«{edital['frase_insc']}» | «{t['frase']}»"
                              + (f" | local: «{edital['local']}»" if edital["local"] else ""))[:900],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(p) + ".") if p else
                f"{hoje}: ok (frases conferidas no documento do edital; datas e horário coerentes).",
            }
            if edital["gratuito"] and (existentes.get(link, {}).get("Curso") or cursos.get(k)):
                gratuidade_provada[(existentes.get(link, {}).get("Curso") or cursos.get(k)).strip()] = str(res.get("gratuidade"))
            if link in existentes:
                alteracoes.append((existentes[link]["_linha"], campos))
                continue
            if situacao != "Aberta":
                continue
            curso = cursos.get(k)
            if not curso:
                titulo = re.sub(r"\s+", " ", t["curso"]).strip()
                titulo = titulo[:1].upper() + titulo[1:].lower() if titulo.isupper() else titulo
                provados = ["internet"] + (["renda"] if edital["renda"] else [])
                novo = {
                    "ID": id_curso(fonte["lista"], titulo), "Estado": "Novo", "Título": titulo[:200],
                    "Entidade": fonte["entidade"], "Link": fonte["lista"], "Página do curso": pagina,
                    "Local": fonte["local"], "Modalidade": "presencial", "País": "BR", "Região": fonte["regiao"],
                    "Cidade": "", "Descrição": "", "Necessidades": necessidades("", titulo),
                    "Perfis": ", ".join(perfis_da_frase(edital["reserva"])) or "todos",
                    "Condição de acesso": "", "Requisitos": "", "Certificado": "desconhecido", "Inscrições até": "",
                    "Início": "", "Duração": str(t.get("carga_horaria") or ""), "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", **VERIFICACAO_INICIAL,
                    "Nota da verificação": f"{hoje}: curso criado a partir do edital nº {e.get('number')} do {fonte['nome']}.",
                    "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": (f"gratuito: «{res.get('gratuidade')}»" if edital["gratuito"] else "")
                    + (f" | renda: «{edital['renda']}»" if edital["renda"] else ""),
                    "Campos comprovados": ", ".join((["gratuito"] if edital["gratuito"] else []) + provados),
                    "Renda máxima": edital["renda"][:200], "Precisa de internet": "Não" if edital["modo"] == "presencial" else "",
                    "O que falta confirmar": "" if edital["gratuito"] else "O edital não confirmou a gratuidade.",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if p else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            print(f"  + {t['curso'][:40]} | {t['cidade']} | inscrição até {edital['fim'] or '—'} | {situacao}"
                  + (f" | AUDITORIA: {'; '.join(p)}" if p else ""))
        estado["tratados"][chave_estado] = {
            "data": hoje, "inscricao_ate": edital["fim"], "cursos": len(edital["turmas"]),
            "tentativas": (feito.get("tentativas", 0) if isinstance(feito, dict) else 0) + 1}
        time.sleep(1)

    # situação das turmas já conhecidas: só pelas datas do documento
    for link, t in existentes.items():
        prazo = (t.get("Prazo de inscrição") or "")[:10]
        if t.get("Situação") == "Aberta" and prazo and prazo < hoje:
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje}))

    # publicar cursos e atualizar a situação de cada curso pelas suas turmas
    turmas_finais = {l: (t.get("Curso"), t.get("Situação"), t.get("Estado")) for l, t in existentes.items()}
    for linha, campos in alteracoes:
        for l, t in existentes.items():
            if t["_linha"] == linha:
                antes = turmas_finais[l]
                turmas_finais[l] = (antes[0], campos.get("Situação", antes[1]), campos.get("Estado", antes[2]))
    for n in novas:
        turmas_finais[n["Link da turma"]] = (n["Curso"], n["Situação"], n["Estado"])
    abertas = {}
    for curso, sit, est in turmas_finais.values():
        if est == "Publicado" and sit == "Aberta":
            abertas[curso] = abertas.get(curso, 0) + 1
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade escrita no edital."
    for n in cursos_novos:
        if abertas.get(n["ID"]) and "gratuito" in n["Campos comprovados"]:
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        campos = {}
        comprovados = r.get("Campos comprovados") or ""
        frase = gratuidade_provada.get(r["ID"].strip())
        if frase and "gratuito" not in comprovados:
            comprovados = ", ".join(["gratuito"] + [c for c in comprovados.split(", ") if c])
            campos.update({"Campos comprovados": comprovados,
                           "Evidência": f"gratuito: «{frase}»" + (" | " + r["Evidência"] if r.get("Evidência") else ""),
                           "O que falta confirmar": ""})
        nova = "Aberto" if abertas.get(r["ID"].strip()) else "Encerrado"
        if nova != r.get("Situação das inscrições"):
            campos["Situação das inscrições"] = nova
        if (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and abertas.get(r["ID"].strip())
                and "gratuito" in comprovados and not sim(r.get("Mudança a rever"))):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
        if campos:
            alteracoes_cursos.append((r["_linha"], campos))

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    gravar_json(fonte["estado"], estado)
    print(f"\n{fonte['nome']}: {lidos} editais lidos, {len(novas)} turmas novas, {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados) | custo estimado {round(custo, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
