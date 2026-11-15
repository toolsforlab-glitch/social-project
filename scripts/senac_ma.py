"""Editais do Programa Senac de Gratuidade do Maranhão (Senac MA): turmas lidas do documento oficial.

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
import zipfile
import html as _html

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, sim
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json, gravar_json, ler_json
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

API = "https://ma.senac.br/v1/public/notices?type=psg&page=1&per_page=30"
SITE = "https://ma.senac.br"
LISTA = "https://ma.senac.br/editais-psg/"
ENTIDADE = "Senac Maranhão (Programa Senac de Gratuidade)"
ESTADO = "estado/senac_ma.json"
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
- Em "turmas", uma entrada por curso e turno do Anexo I ("PROGRAMAÇÃO DOS CURSOS E TURNOS"; a tabela pode \
aparecer com as células separadas por " | " numa só linha: copia a linha com os " | "). Se o edital tem \
cursos, "turmas" nunca vem vazio. "frase" é o texto da linha do Anexo I desse curso, \
copiado tal como aparece no texto que recebes (começa no nome do curso e inclui a data de início das aulas).
- "cidade": o município onde o curso decorre, como está escrito no edital.
- "gratuidade": a frase exata do edital que diz que o curso é do Programa Senac de Gratuidade ou gratuito.
- "renda": a frase exata com o critério de renda, se existir.

Devolve só JSON entre <json></json>:
{"inscricao": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD", "frase": "..."} ou null,
 "modo": "presencial|online|ambos" ou null, "local_inscricao": "..." ou null, "frase_local": "..." ou null,
 "gratuidade": "..." ou null, "renda": "..." ou null,
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
    renda = str(res.get("renda") or "") if citacao_valida(str(res.get("renda") or ""), texto) else ""
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
        if cidade and chave(cidade) not in chave(texto):
            cidade = ""
        turmas.append({**t, "curso": curso, "inicio_aulas": inicio, "cidade": cidade,
                       "fim_aulas": data_valida(t.get("fim_aulas")),
                       "horario": horario_confirmado(t.get("horario"), frase)})
    return {"ini": ini, "fim": fim, "frase_insc": frase_insc if fim else "", "local": local, "modo": modo,
            "gratuito": gratuito, "renda": renda, "turmas": turmas}, problemas


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

def numero_alterado(n):
    m = re.match(r"(\d+)", str(n or ""))
    return m.group(1) if m else ""


def main():
    base = Base()
    cfg = carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    modelo = cfg.get("modelo_cursos") or "claude-haiku-5-5"
    estado = ler_json(ESTADO, {"tratados": {}})
    try:
        editais = json.loads(baixar(API, timeout=40).decode("utf-8"))["data"]
    except Exception as e:  # noqa: BLE001
        print(f"Senac MA: a lista de editais não abriu ({type(e).__name__}). Nada alterado.")
        editais = []
    corte = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_RECENTES)).isoformat()

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(LISTA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(SITE + "/editais_psg/")}

    novas, alteracoes, cursos_novos, historico, custo = [], [], [], [], 0.0
    lidos = 0
    for e in editais:
        chave_estado = f"{e.get('id')}|{e.get('updated_at')}"
        feito = estado["tratados"].get(chave_estado)
        if (e.get("published_at") or "")[:10] < corte or (feito and (not isinstance(feito, dict)
                                                                       or feito.get("tentativas", 0) >= MAX_TENTATIVAS
                                                                       or feito.get("cursos"))):
            continue
        docs = e.get("documents") or []
        pagina = SITE + (e.get("path") or "")
        # termo aditivo: as turmas do edital alterado vão para Rever
        if "TERMO" in str(e.get("number", "")).upper() or any(d.get("type") == "aditivo" for d in docs):
            n = numero_alterado(e.get("number"))
            nota = f"{hoje}: saiu um termo aditivo ao edital nº {n} ({pagina}); confirmar prazos e turmas antes de publicar."
            for link, t in existentes.items():
                if re.search(rf"edital-psg-n[ºo°]?-?{n}-", link) and t.get("Estado") == "Publicado":
                    alteracoes.append((t["_linha"], {"Estado": "Rever", "Notas": nota}))
                    historico.append(registo(t, "Senac MA", "Rever", nota))
            estado["tratados"][chave_estado] = hoje
            continue
        if not docs or lidos >= MAX_POR_EXECUCAO:
            continue
        doc = docs[0]
        try:
            dados = baixar(SITE + doc["url"], timeout=60)
            texto = recortar(texto_do_documento(dados, doc.get("mime_type", "")))
        except Exception as ex:  # noqa: BLE001
            print(f"  ✗ edital {e.get('number')}: documento ilegível ({type(ex).__name__})")
            continue
        if len(texto.strip()) < 500:
            print(f"  ✗ edital {e.get('number')}: o documento não tem texto legível (pode ser digitalizado)")
            estado["tratados"][chave_estado] = hoje
            continue
        try:
            resposta, uso = claude(modelo, SISTEMA, f"Título do edital: {e.get('title')}\n\nTexto do edital:\n{texto}",
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
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": (f"«{edital['frase_insc']}» | «{t['frase']}»"
                              + (f" | local: «{edital['local']}»" if edital["local"] else ""))[:900],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(p) + ".") if p else
                f"{hoje}: ok (frases conferidas no documento do edital; datas e horário coerentes).",
            }
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
                    "ID": id_curso(LISTA, titulo), "Estado": "Novo", "Título": titulo[:200], "Entidade": ENTIDADE,
                    "Link": LISTA, "Página do curso": pagina, "Local": "BR-MA", "Modalidade": "presencial", "País": "BR", "Região": "Maranhão",
                    "Cidade": "", "Descrição": "", "Necessidades": necessidades("", titulo), "Perfis": "todos",
                    "Condição de acesso": "", "Requisitos": "", "Certificado": "desconhecido", "Inscrições até": "",
                    "Início": "", "Duração": str(t.get("carga_horaria") or ""), "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", **VERIFICACAO_INICIAL,
                    "Nota da verificação": f"{hoje}: curso criado a partir do edital nº {e.get('number')} do Senac MA.",
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
        nova = "Aberto" if abertas.get(r["ID"].strip()) else "Encerrado"
        if nova != r.get("Situação das inscrições"):
            campos["Situação das inscrições"] = nova
        if (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and abertas.get(r["ID"].strip())
                and "gratuito" in (r.get("Campos comprovados") or "") and not sim(r.get("Mudança a rever"))):
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
    gravar_json(ESTADO, estado)
    print(f"\nSenac MA: {lidos} editais lidos, {len(novas)} turmas novas, {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados) | custo estimado {round(custo, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
