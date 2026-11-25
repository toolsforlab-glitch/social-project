"""Cursos gratuitos do Cetam (Centro de Educação Tecnológica do Amazonas, Governo do Amazonas), lidos dos editais
oficiais, sem Claude (24/11/2026).

O Cetam publica cerca de 11 editais por ano na página «Tudo sobre inscrições» (https://www.cetam.am.gov.br/tudo-sobre-
inscricoes/, abre a partir do GitHub): cursos presenciais na capital (por unidade), no interior (por município, com o
local de realização de cada turma) e EaD, com inscrições de 2 a 4 dias no Portal do Candidato
(https://inscricao.cetam.am.gov.br/) e vagas por ordem de chegada. Os editais presenciais são enormes (127 e 205
páginas em 2026, centenas de turmas), por isso a tabela do Anexo II é lida por código (pdftotext -layout), linha a
linha: cada turma tem uma linha com o número, a carga horária, o horário, as datas de início e de término e as vagas;
o nome do curso, o local e os pré-requisitos partem-se nas linhas à volta e são juntados pela coluna (posição no
cabeçalho) e pela linha de turma mais próxima.

Regras do responsável (24/11/2026):
- os presenciais entram, com aviso: o edital diz que são gratuitos «nas etapas: inscrições, matrículas e certificação»
  e que, «na etapa de execução», o aluno compra os materiais individuais das aulas práticas (vai para «Requisitos»);
- os cursos «avançados» (certificado de um curso básico OU portfólio/experiência avaliados) entram;
- ficam fora as turmas cujo pré-requisito exige já ser da área (acadêmico, técnico, profissional, docente, servidor).

Provas, tiradas do próprio edital a cada leitura: a frase da gratuidade, a da ocupação das vagas (ordem de chegada
ou de preenchimento online), o período de inscrição (item 4.1) e, por turma, a linha da tabela. Conferência extra: a
soma das vagas lidas tem de bater com o total anunciado no início do edital; se não bater, as turmas desse edital vão
para «Rever». Erratas: os cursos nomeados numa errata vão para «Rever» (se a errata falar da inscrição, todos).

As turmas só são publicadas quando a inscrição abre (como nos outros editais) e passam a «Encerrado» depois do fim.
Um curso no site = um curso num município (ou EaD) num edital, com as unidades, horários e datas nas notas.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date, timedelta

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, hoje_iso, registar_pendencia, registo_historico
from comum import baixar, gravar_json, ler_json
from turmas import necessidades

SITE = "https://www.cetam.am.gov.br"
PAGINA = SITE + "/tudo-sobre-inscricoes/"
PORTAL = "https://inscricao.cetam.am.gov.br/"
ENTIDADE = "Cetam – Centro de Educação Tecnológica do Amazonas (Governo do Amazonas)"
ESTADO = "estado/cetam.json"  # editais já lidos (período de inscrição), para não baixar de novo os fechados
MESES_RECENTES = 3  # só se leem editais publicados nos últimos meses (pasta AAAA/MM do upload)
AVISO_MATERIAL = "o aluno compra o material individual das aulas práticas (o curso é gratuito)"
DA_AREA = re.compile(r"ACAD[ÊE]MIC|T[ÉE]CNICOS? (?:EM|DE)\b|PROFISSIONA(?:L|IS) (?:D|QUE)|ATUA(?:R|NTE|ÇÃO)|SERVIDOR|"
                     r"DOCENTES?\b|PROFESSOR(?:ES|A)?\b", re.I)
DATA = r"\d{2}/\d{2}/\d{4}"
RODAPE = re.compile(r"cetam\.am\.gov\.br|instagram\.com|youtube\.com|facebook\.com|Fone:|Pedro Teixeira|CEP:|"
                    r"EDITAL CETAM|INSCRIÇÕES ONLINE|UNIDADES DE EDUCAÇÃO|ESTADO DO AMAZONAS|ANEXO", re.I)


def sem_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(c))


def normal(t):
    return re.sub(r"\s+", " ", (t or "").replace("​", " ")).strip()


def iso(d):
    dd, mm, aa = d.split("/")
    return f"{aa}-{mm}-{dd}"


def titulo(s):
    s = re.sub(r"\s*\((?:EaD|EAD)\)\s*$", "", normal(s))
    s = re.sub(r"(\w)- (\w)", r"\1-\2", s)  # «PRÉ- HOSPITALAR» (hífen partido na linha)
    s = s[:1].upper() + s[1:].lower() if s.isupper() else s
    for sigla in ("esg", "tea", "sgi", "tbo", "ead", "clp", "nr", "ia", "ti", "pcd", "libras", "excel", "word",
                  "power bi", "python", "cad"):
        s = re.sub(rf"\b{sigla}\b", sigla.upper() if sigla not in ("libras", "excel", "word", "python") else sigla.title(), s)
    s = re.sub(r"\((\w{2,5})\)", lambda m: "(" + m.group(1).upper() + ")", s)  # siglas: (APH), (ACS), (PAE)
    return s.replace("Power bi", "Power BI")


def nome_municipio(s):
    pequenas = {"da", "de", "do", "das", "dos", "e"}
    return " ".join(p.lower() if i and p.lower() in pequenas else p.capitalize() for i, p in enumerate(normal(s).split()))


def texto_layout(dados):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(dados)
        f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, check=True).stdout.decode(
            "utf-8", "replace")


def pedacos(linha):
    """Pedaços de texto separados por 2 ou mais espaços, com a posição do centro."""
    return [(m.group(0), (m.start() + m.end()) / 2) for m in re.finditer(r"\S+(?: \S+)*", linha)]


def editais_da_pagina(html):
    urls = list(dict.fromkeys(re.findall(r'href="(https://www\.cetam\.am\.gov\.br/wp-content/uploads/\d{4}/\d{2}/[^"]+\.pdf)"', html)))
    editais, erratas = [], {}
    for u in urls:
        nome = u.rsplit("/", 1)[-1]
        m = re.search(r"Edital[-_ ]?(\d{3})[-_](\d{4})", nome, re.I)
        if not m:
            continue
        num = f"{m.group(1)}/{m.group(2)}"
        if re.search(r"errata", nome, re.I):
            erratas.setdefault(num, []).append(u)
        elif re.match(r"edital", nome, re.I) and not re.search(r"lista|relac|inscritos", nome, re.I):
            editais.append((num, u))
    return editais, erratas


def repartir(itens, filas, minimo=1):
    """Divide os itens de uma coluna (lista ordenada de (linha, texto)) em blocos contínuos, um por turma (linhas das
    turmas em «filas»), com o centro de cada bloco o mais perto possível da linha da turma (o PDF centra cada célula
    na sua linha). Programação dinâmica; devolve a lista de blocos ou None se não houver itens que cheguem."""
    m, n = len(itens), len(filas)
    if n == 0 or m < n * minimo:
        return None
    inf = float("inf")
    custo = [[inf] * (m + 1) for _ in range(n + 1)]
    corte = [[0] * (m + 1) for _ in range(n + 1)]
    custo[0][0] = 0.0
    for k in range(1, n + 1):
        for j in range(k * minimo, m + 1):
            for a in range((k - 1) * minimo, j - minimo + 1):
                if custo[k - 1][a] == inf:
                    continue
                bloco = itens[a:j]
                c = ((sum(x for x, _ in bloco) / len(bloco) - filas[k - 1]) ** 2) if bloco else 4.0
                if custo[k - 1][a] + c < custo[k][j]:
                    custo[k][j], corte[k][j] = custo[k - 1][a] + c, a
    if custo[n][m] == inf:
        return None
    blocos, j = [], m
    for k in range(n, 0, -1):
        a = corte[k][j]
        blocos.append(itens[a:j])
        j = a
    return blocos[::-1]


def ler_tabela(layout):
    """Turmas do Anexo II. Devolve (turmas, avisos)."""
    linhas = layout.split("\n")
    ini = next((i for i, l in enumerate(linhas) if re.search(r"ANEXO\s+(?:ll|II)\b", l) and "LISTA" in l.upper()), None)
    if ini is None:
        return [], ["Anexo II não encontrado"]
    fim = next((i for i in range(ini + 1, len(linhas))
                if (m_a := re.search(r"\bANEXO\s+([IVXl]+)\b", linhas[i])) and m_a.group(1) not in ("II", "ll")), len(linhas))
    turmas, avisos = [], []
    r_avisos = avisos
    municipio = unidade = endereco = ""
    centros = None  # colunas do cabeçalho atual
    online = False
    segmento = []  # (índice, linha) da tabela atual
    ultimas = []  # linhas recentes fora de tabela (para achar o nome da unidade)

    def fechar_segmento():
        if not segmento or not centros:
            return
        dados_idx = [i for i, l in segmento if eh_turma(l)]
        if not dados_idx:
            return
        info = {i: ler_linha_turma(l) for i, l in segmento if eh_turma(l)}
        partes = {i: {"curso": [], "local": [], "req": []} for i in dados_idx}
        colunas = {"curso": [], "local": [], "req": []}
        for i, l in segmento:
            if i > dados_idx[-1] + 4:
                break  # depois da última turma só podem vir as últimas linhas das suas células
            if i in info:
                for col, txt in info[i]["esquerda"]:
                    colunas[col].append((i, txt))
                if info[i]["req"]:
                    colunas["req"].append((i, info[i]["req"]))
                continue
            perto = min(dados_idx, key=lambda j: abs(j - i))
            for col, txt in dividir(l, info[perto]["desvio"]):
                if col in colunas:
                    colunas[col].append((i, txt))
        for col, itens in colunas.items():
            # várias peças na mesma linha ficam juntas
            por_linha = []
            for i, txt in itens:
                if por_linha and por_linha[-1][0] == i:
                    por_linha[-1] = (i, por_linha[-1][1] + " " + txt)
                else:
                    por_linha.append((i, txt))
            blocos = None
            if col == "req":
                # os pré-requisitos começam sempre pela idade («16 ANOS …»): parte-se aí, se a conta bater
                texto = " ".join(t for _, t in por_linha)
                itens_req = [x.strip() for x in re.split(r"(?=\b\d{2} ANOS\b)", texto) if x.strip()]
                if len(itens_req) == len(dados_idx) and all(re.match(r"\d{2} ANOS", x) for x in itens_req):
                    for i, x in zip(dados_idx, itens_req):
                        partes[i]["req"] = [(i, x)]
                    continue
            blocos = repartir(por_linha, dados_idx, minimo=1 if col in ("curso", "req") else 0)
            if blocos is None:
                for i, txt in por_linha:  # recurso: a turma mais perto
                    partes[min(dados_idx, key=lambda j: (abs(j - i), -j))][col].append((i, txt))
                r_avisos.append(f"coluna {col}: repartição pela turma mais perto ({len(por_linha)} linhas, {len(dados_idx)} turmas)")
            else:
                for i, b in zip(dados_idx, blocos):
                    partes[i][col] = b
        for i in dados_idx:
            t = info[i]
            curso = normal(" ".join(x for _, x in sorted(partes[i]["curso"])))
            local = normal(" ".join(x for _, x in sorted(partes[i]["local"])))
            req = normal(" ".join(x for _, x in sorted(partes[i]["req"])))
            ead = online or (t.get("horario") or "").upper() == "EAD"
            turmas.append({**{k: v for k, v in t.items() if k not in ("esquerda", "desvio")}, "curso": curso, "local": local or unidade,
                           "req": req, "municipio": municipio, "endereco": endereco, "online": ead,
                           "linha": normal(linhas[i])})

    def coluna(c):
        return min(centros, key=lambda k: abs(centros[k] - c))

    def dividir(texto, desvio):
        """Pedaços com a sua coluna; entre «local» e «curso» o PDF às vezes deixa um só espaço, por isso aí a
        divisão é palavra a palavra, pela fronteira a meio dos dois cabeçalhos."""
        saida = []
        for txt, c in pedacos(texto):
            col = coluna(c + desvio)
            if "local" in centros and col in ("local", "curso"):
                fronteira = (centros["local"] + centros["curso"]) / 2
                ini_p = c - len(txt) / 2
                for w in re.finditer(r"\S+", txt):
                    cw = ini_p + (w.start() + w.end()) / 2 + desvio
                    cw_col = "local" if cw < fronteira else "curso"
                    if saida and saida[-1][0] == cw_col and saida[-1][2]:
                        saida[-1] = (cw_col, saida[-1][1] + " " + w.group(0), True)
                    else:
                        saida.append((cw_col, w.group(0), True))
            else:
                saida.append((col, txt, False))
        return [(a, b) for a, b, _ in saida]

    def eh_turma(l):
        return bool(re.match(r"^\s{0,6}\d{1,3}\s{2,}", l)) and len(re.findall(DATA, l)) >= 2

    def ler_linha_turma(l):
        m0 = re.match(r"^\s*(\d{1,3})(?=\s{2,})", l)
        resto_ini = m0.end()
        m = re.search(rf"(?<=\s\s)(\d{{2,4}})\s{{2,}}(?:(\S(?:.*?\S)?)\s{{2,}})?({DATA})\s+({DATA})\s{{2,}}([\d.]+)"
                      rf"(?:\s{{2,}}([\d.]+))?(.*)$", l[resto_ini:])
        if not m:
            return {"n": m0.group(1), "ch": "", "horario": "", "inicio": "", "fim": "", "vagas": "", "espera": "",
                    "dias": "", "esquerda": [], "req": "", "desvio": 0}
        esquerda = []
        pos_ch = resto_ini + m.start(1) + len(m.group(1)) / 2
        desvio = (centros["CH"] - pos_ch) if "CH" in centros else 0  # a tabela muda de posição de página para página
        for col, txt in dividir(" " * resto_ini + l[resto_ini:resto_ini + m.start()], desvio):
            esquerda.append(("local" if col == "local" else "curso", txt))
        dias, req = [], []
        base_x = resto_ini + m.start(7)
        for txt, c in pedacos(m.group(7)):
            if re.match(r"(SEG|TER|QUA|QUI|SEX|S[ÁA]B|DOM|EaD$|EAD$)\b", txt):
                dias.append(txt)
            else:
                req.append(txt)
        return {"n": m0.group(1), "ch": m.group(1), "horario": m.group(2) or "", "inicio": iso(m.group(3)),
                "fim": iso(m.group(4)), "vagas": m.group(5).replace(".", ""), "espera": (m.group(6) or "").replace(".", ""),
                "dias": " ".join(dias), "esquerda": esquerda, "req": " ".join(req), "desvio": desvio}

    for i in range(ini + 1, fim):
        l = linhas[i]
        if not l.strip():
            continue
        if re.match(r"^\s*N\.º\s", l) and "CURSO" in l:
            fechar_segmento()
            segmento = []
            cab = {txt: c for txt, c in pedacos(l)}
            centros = {}
            for txt, c in cab.items():
                if txt.startswith("REALIZA") or txt.startswith("LOCAL"):
                    centros["local"] = c
                elif txt == "CURSO":
                    centros["curso"] = c
                elif txt.startswith("PRÉ-REQ") or txt.startswith("PRE-REQ"):
                    centros["req"] = c
                elif txt in ("CH", "HORÁRIO", "VAGAS", "N.º"):
                    centros[txt] = c
            online = "HORÁRIO" not in cab
            continue
        if RODAPE.search(l) or re.search(r"Cursos de Educação a Distância", l) or (l.strip().isdigit() and len(l.strip()) <= 3 and len(l) - len(l.lstrip()) > 40):
            continue
        if re.match(r"^\s*(DATA|INÍCIO|SEMANA|LOCAL DE|CURSO|REGULAR|ESPERA|VAGA|DIAS DA|TÉRMINO)\b", l.strip()) and not eh_turma(l):
            if all(re.match(r"(DATA|INÍCIO|TÉRMINO|SEMANA|DIAS DA|LOCAL DE|CURSO|VAGA.*|REGULAR|ESPERA|DE ESPERA)$", p)
                   for p, _ in pedacos(l)):
                continue
        mm = re.match(r"^\s*\d{1,3}\.\s+([A-ZÀ-Ü][A-ZÀ-Ü'\- ]+?)\s*$", l)
        if mm:
            fechar_segmento()
            segmento, centros = [], None
            municipio, unidade, endereco = nome_municipio(mm.group(1)), "", ""
            ultimas = []
            continue
        if re.search(r"\bENDEREÇO\b", l):
            # nome da unidade (capital): a última linha em maiúsculas antes do endereço; o que vem a partir dela (ou
            # do endereço, duas linhas acima) não pertence à tabela anterior
            u_idx, nova = i - 2, ""
            if not municipio:
                for j in range(i - 1, max(ini, i - 14), -1):
                    x = normal(linhas[j])
                    if (x and x.isupper() and "@" not in x and "E-MAIL" not in x and not RODAPE.search(x)
                            and not re.search(r"\d{4,}|^\d+$", x) and len(x) > 6 and not re.match(r"N\.º", x)):
                        nova, u_idx = x, j
                        break
            segmento = [(j, x) for j, x in segmento if j < min(u_idx, i - 2)]
            fechar_segmento()  # a tabela anterior fecha com a unidade anterior
            segmento, centros = [], None
            if nova:
                unidade = nova
            end = [p for p, _ in pedacos(l) if p not in ("ENDEREÇO",) and "@" not in p and "E-MAIL" not in p]
            prox = [p for x in linhas[i - 2:i + 3] for p, c in pedacos(x)
                    if p not in ("ENDEREÇO", "E-MAIL", "TELEFONE") and "@" not in p and not re.match(r"\(\d\d\)", p)
                    and c < 90]
            endereco = normal(" ".join(dict.fromkeys(end + prox)))
            continue
        if centros:
            segmento.append((i, l))
        else:
            ultimas.append(normal(l))
    fechar_segmento()
    return turmas, avisos


def cidade_da_turma(t):
    if t["online"]:
        return ""
    if t["municipio"]:
        return t["municipio"]
    m = re.findall(r"([A-ZÀ-Úa-zà-ú' ]+)/AM", t["endereco"])
    return nome_municipio(m[-1].strip(" -–")) if m else "Manaus"


def chave_curso(num, curso, cidade):
    return "C-" + hashlib.sha1(f"cetam|{num}|{sem_acentos(curso)}|{sem_acentos(cidade)}".encode()).hexdigest()[:8]


def ler_edital(num, url, erratas):
    dados = baixar(url, timeout=120)
    layout = texto_layout(dados)
    t = normal(layout)
    r = {"num": num, "url": url, "problemas": []}
    m = re.search(rf"4\.1\.?\s*Data:\s*({DATA})[^.]*?\ba\s*({DATA})[^.]*\.", t)
    r["ini"], r["fim"], r["frase_insc"] = (iso(m.group(1)), iso(m.group(2)), m.group(0)) if m else ("", "", "")
    m = re.search(r"Os cursos ofertados neste edital são (?:totalmente )?gratuitos[^.]*?(?:certificação\)?|etapas)\.?", t)
    r["gratuidade"] = m.group(0) if m else ""
    m = re.search(r"[^.]*responsável por providenciar os materiais[^.]*\.", t)
    r["materiais"] = normal(m.group(0)).lstrip("0123456789. ") if m else ""
    m = re.search(r"As vagas ofertadas serão ocupadas[^.]*\.", t)
    r["selecao"] = m.group(0) if m and re.search(r"ordem de chegada|ordem de preenchimento", m.group(0), re.I) else ""
    m = re.search(r"oferta de ([\d.]+) \(", t)
    r["total"] = int(m.group(1).replace(".", "")) if m else 0
    r["portal"] = PORTAL if "inscricao.cetam.am.gov.br" in t else ""
    r["turmas"], avisos = ler_tabela(layout)
    r["problemas"] += avisos
    soma = sum(int(x["vagas"] or 0) for x in r["turmas"])
    r["soma"] = soma
    if r["total"] and soma != r["total"]:
        r["problemas"].append(f"a soma das vagas lidas ({soma}) não bate com o total do edital ({r['total']})")
    r["texto_errata"] = ""
    for u in erratas.get(num, []):
        try:
            r["texto_errata"] += " " + normal(texto_layout(baixar(u, timeout=60)))
        except Exception:  # noqa: BLE001
            r["problemas"].append(f"errata ilegível ({u})")
    return r


def agrupar(r):
    """Um curso por (curso, município ou EaD) dentro do edital."""
    cursos, fora = {}, []
    for t in r["turmas"]:
        if not t["curso"] or not t["inicio"]:
            r["problemas"].append(f"turma sem nome ou sem datas: {t['linha'][:120]}")
            continue
        if DA_AREA.search(t["req"]) and "PORTFÓLIO" not in t["req"].upper():
            fora.append(f"{t['curso']} ({t['req']})")
            continue
        cidade = cidade_da_turma(t)
        k = chave_curso(r["num"], t["curso"], cidade or "online")
        c = cursos.setdefault(k, {"curso": t["curso"], "cidade": cidade, "online": t["online"], "turmas": []})
        c["turmas"].append(t)
    # nome com palavras em falta no meio (ex.: «AGENTE DE INCLUSÃO PARA COM TRANSTORNO…» ao lado de «…PARA PESSOA COM
    # TRANSTORNO…»): não se adivinha a palavra; o curso vai para «Rever»
    nomes = {titulo(c["curso"]).lower() for c in cursos.values()}
    for c in cursos.values():
        n = titulo(c["curso"]).lower().split()
        for outro in nomes:
            o = outro.split()
            if len(o) > len(n) >= 2 and o[0] == n[0] and o[-1] == n[-1] and _em_ordem(n, o):
                c["suspeito"] = f"o nome parece incompleto (há «{outro}» no mesmo edital)"
                break
    return cursos, fora


def _em_ordem(curto, longo):
    pos = 0
    for p in curto:
        try:
            pos = longo.index(p, pos) + 1
        except ValueError:
            return False
    return True


def main():
    seco = bool(os.environ.get("SECO"))
    hoje = (os.environ.get("HOJE_ENSAIO") if seco else "") or hoje_iso()
    base = None if seco else Base()
    if base:
        carregar_config(base)
    try:
        html = baixar(PAGINA, timeout=90).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"Cetam: a página de inscrições não abriu ({type(e).__name__}); fica para amanhã.")
        return 0
    editais, erratas = editais_da_pagina(html)
    so = os.environ.get("CETAM_EDITAL")  # ensaio: só este edital (número, ex.: 009/2026)
    corte = date.fromisoformat(hoje) - timedelta(days=31 * MESES_RECENTES)
    recentes = [(n, u) for n, u in editais if (so and n == so) or (not so and re.search(r"/uploads/(\d{4})/(\d{2})/", u)
                and date(*map(int, re.search(r"/uploads/(\d{4})/(\d{2})/", u).groups()), 1) >= corte.replace(day=1))]
    print(f"Cetam: {len(editais)} editais na página; {len(recentes)} recentes: {', '.join(n for n, _ in recentes) or '—'}.")

    linhas = base.tabela("Cursos") if base else []
    na_folha = {r["ID"]: r for r in linhas if r.get("Origem") == "cetam"}
    alteracoes, novos, historico = [], [], []
    for cid, r in na_folha.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        if (r.get("Inscrições até") or "9999") < hoje and r.get("Situação das inscrições") != "Encerrado":
            alteracoes.append((r["_linha"], {"Situação das inscrições": "Encerrado", "Última verificação": hoje}))

    cache = ler_json(ESTADO, {})
    for num, url in recentes:
        if not so and (cache.get(url, {}).get("fim") or "9999") < hoje:
            continue  # edital já fechado: não se volta a baixar
        try:
            r = ler_edital(num, url, erratas)
            cache[url] = {"num": num, "ini": r["ini"], "fim": r["fim"], "turmas": len(r["turmas"])}
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ edital {num}: ilegível ({type(e).__name__}: {e})")
            continue
        cursos, fora = agrupar(r)
        aberto = bool(r["ini"] and r["fim"] and r["ini"] <= hoje <= r["fim"])
        print(f"  edital {num}: inscrição {r['ini'] or '?'} a {r['fim'] or '?'} ({'aberta' if aberto else 'fechada'}); "
              f"{len(r['turmas'])} turmas, {r['soma']} vagas (edital: {r['total'] or '?'}); {len(cursos)} cursos; "
              f"{len(fora)} fora por serem só para quem já é da área; gratuidade {'sim' if r['gratuidade'] else 'NÃO'}; "
              f"seleção {'sim' if r['selecao'] else 'NÃO'}; material pago {'sim' if r['materiais'] else 'não'}"
              + (f" | PROBLEMAS: {'; '.join(r['problemas'][:5])}" if r["problemas"] else ""))
        if seco:
            for c in list(cursos.values())[:6]:
                t0 = c["turmas"][0]
                print(f"    · {titulo(c['curso'])} | {c['cidade'] or 'EaD'} | {len(c['turmas'])} turmas | "
                      f"{t0['local']} | {t0['ch']}h {t0['horario']} {t0['inicio']}→{t0['fim']} | vagas {t0['vagas']} | "
                      f"req: {t0['req'][:90]}")
            susp = [c for c in cursos.values() if c.get("suspeito")]
            print(f"    para rever por nome incompleto: {len(susp)}: " + "; ".join(titulo(c['curso']) for c in susp[:5]))
            for f in fora[:4]:
                print(f"    - fora: {f[:150]}")
            sem_idade = [t for t in r["turmas"] if not re.match(r"\d{2} ANOS", t["req"])]
            estranhos = [t for t in r["turmas"] if re.search(r"ESCOLA|UNIDADE|CENTRO|\d|ANOS", t["curso"]) or len(t["curso"]) < 5]
            print(f"    conferência: {len(sem_idade)} turmas com pré-requisito sem idade; {len(estranhos)} nomes estranhos")
            for t in (sem_idade + estranhos)[:6]:
                print(f"    ? {t['curso'][:60]} | local {t['local'][:50]} | req {t['req'][:100]}")
            nomes = sorted({titulo(t["curso"]) for t in r["turmas"]})
            print("    nomes:", " · ".join(nomes)[:1500])
            locais = sorted({t["local"] for t in r["turmas"]})
            print("    locais:", " · ".join(locais)[:900])
            continue
        if not (r["gratuidade"] and r["ini"] and r["fim"]):
            registar_pendencia(base, f"Cetam: o edital {num} não tem a frase da gratuidade ou o período de inscrição "
                                     "no formato conhecido; não foi publicado.",
                               "Peça ao Claude para ver o edital e ajustar o leitor (cetam.py).", url, origem="cetam.py")
            continue
        if not aberto:
            continue
        rever_tudo = bool(r["problemas"]) or bool(re.search(r"inscri|4\.1", r["texto_errata"], re.I))
        evid_base = " | ".join(x for x in [
            f"gratuito: «{r['gratuidade']}» ({url})",
            f"vagas: «{r['selecao']}»" if r["selecao"] else "",
            f"inscrição: «{r['frase_insc']}»",
            f"material: «{r['materiais']}»" if r["materiais"] else "",
        ] if x)
        for cid, c in cursos.items():
            if cid in na_folha:
                continue
            rever = (rever_tudo or bool(c.get("suspeito"))
                     or bool(r["texto_errata"] and sem_acentos(c["curso"]) in sem_acentos(r["texto_errata"])))
            nome = titulo(c["curso"])
            reqs = list(dict.fromkeys(titulo(t["req"]) for t in c["turmas"] if t["req"]))
            requisitos = "; ".join(reqs[:3] + ([AVISO_MATERIAL] if r["materiais"] and not c["online"] else []))
            inicio = min(t["inicio"] for t in c["turmas"])
            notas_turmas = "; ".join(
                f"{titulo(t['local'])}: {t['horario'] + ', ' if t['horario'] else ''}{t['dias'] + ', ' if t['dias'] else ''}"
                f"{t['inicio'][8:]}/{t['inicio'][5:7]} a {t['fim'][8:]}/{t['fim'][5:7]}, {t['vagas']} vagas"
                if t["local"] else f"{t['inicio'][8:]}/{t['inicio'][5:7]} a {t['fim'][8:]}/{t['fim'][5:7]}, {t['vagas']} vagas"
                for t in c["turmas"])
            evid = (evid_base + f" | turma: «{c['turmas'][0]['linha'][:250]}»")[:1500]
            linha = {
                "ID": cid, "Estado": "Rever" if rever else "Publicado", "Título": nome[:200], "Entidade": ENTIDADE,
                "Link": PORTAL, "Local": "BR-AM", "Modalidade": "online" if c["online"] else "presencial", "País": "BR",
                "Região": "Amazonas", "Cidade": c["cidade"], "Descrição": "", "Origem da descrição": "",
                "Necessidades": necessidades("", nome), "Perfis": "todos", "Condição de acesso": "",
                "Requisitos": requisitos[:500], "Certificado": "gratuito", "Inscrições até": r["fim"], "Início": inicio,
                "Duração": f"{c['turmas'][0]['ch']} horas" if c["turmas"][0]["ch"] else "", "Link verificado": "SIM",
                "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "cetam",
                "Notas": (f"Edital Cetam {num}. Turmas: {notas_turmas}")[:900],
                "Como me inscrever": ("1. Entre no Portal do Candidato do Cetam (inscricao.cetam.am.gov.br) e faça o "
                                      "cadastro, com CPF, RG e comprovante de escolaridade.\n"
                                      f"2. Escolha o curso \"{nome}\"" + (f" e a unidade em {c['cidade']}" if c["cidade"] else "")
                                      + f" e inscreva-se entre {r['ini'][8:]}/{r['ini'][5:7]} e {r['fim'][8:]}/{r['fim'][5:7]}.\n"
                                      "3. As vagas são preenchidas por ordem de chegada: inscreva-se logo no primeiro dia.\n"
                                      + ("4. Se for chamado, confirme a matrícula presencialmente na unidade, com os "
                                         "documentos originais." if not c["online"] else "4. Acompanhe o e-mail: o Cetam "
                                         "manda a confirmação e o acesso à plataforma.")),
                **VERIFICACAO_INICIAL,
                "Nota da verificação": f"{hoje}: publicado automaticamente a partir do edital Cetam {num} (Anexo II)."
                                       + (" Rever: " + "; ".join(r["problemas"][:3]) if r["problemas"] else "")
                                       + (" Rever: há errata que nomeia este curso ou a inscrição." if rever and r["texto_errata"] else "")
                                       + (f" Rever: {c['suspeito']}." if c.get("suspeito") else ""),
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": "gratuito, situação, certificado", "Página do curso": url,
            }
            novos.append(linha)
            historico.append(registo_historico(linha, "Edital Cetam", linha["Estado"], linha, url))
        print(f"  edital {num}: {sum(1 for n in novos if num in n['Notas'])} cursos novos.")
    if seco:
        return 0
    gravar_json(ESTADO, cache)
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Cetam: {len(alteracoes)} cursos atualizados, {len(novos)} novos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
