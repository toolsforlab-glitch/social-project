"""O GPT (OpenAI) como auditor das informações duvidosas do site.

Regra do projeto: o GPT só APONTA onde pode estar a resposta (valor, frase e link); quem prova é o código.
Para cada curso que o site mostra hoje (docs/dados/cursos.json) e que tem dúvidas, por esta ordem:

  gratuito       o site mostra «Gratuidade por confirmar»
  situacao       inscrições «Por confirmar» (cursos sem turmas)
  inscricoes_ate data de inscrição sem prova, ou situação por confirmar (cursos sem turmas)
  certificado    o certificado (gratuito, pago, sem certificado) não está comprovado

1. pergunta ao GPT, com pesquisa na web limitada ao domínio oficial da entidade do curso, por uma frase que
   responda a cada dúvida, e pelo link dessa frase (uma pergunta por curso, com todas as dúvidas dele);
2. o código abre cada link e só aceita se:
   - o link (e para onde redireciona) é do domínio oficial da entidade (o mesmo do link do curso, ex.: ac.senac.br);
   - a frase existe letra a letra no texto da página (citacao_valida);
   - a frase diz o que se afirma: gratuidade explícita (o nome do programa não chega); «inscrições abertas» ou
     «encerradas»; a data escrita na própria frase; «certificado» com gratuito, pago ou sem certificado;
3. o que passa fica na Evidência («rótulo: «frase» (link; encontrada pelo GPT, conferida por código)»), em Campos
   comprovados e na coluna do campo; o que não passa fica em «O que falta confirmar» com o motivo, e o curso só
   volta a ser perguntado passados DIAS_ENTRE_CONSULTAS dias.

A verificação semanal (verificar.py) volta a conferir estas frases no link guardado e mantém-nas enquanto lá estiverem.
Desde 22/11/2026 (decisão do responsável: a API custa caro) as rotinas NÃO chamam a API: preparam um texto de
auditoria para o responsável colar no ChatGPT da sua assinatura; a resposta, colada de volta, é provada pelo código
da mesma forma (ver main). Cursos com «Revisto por pessoa» nunca são alterados.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from base import (ACAO_SOB_DEMANDA, CAMPOS_PROVA, gratuidade_comprovada, sim, HISTORICO, MARCA_GPT, MARCA_CHATGPT, Base, carregar_config, certificado_da_frase, citacao_valida, curso_no_site,
                  gratuidade_explicita, registo_historico, texto_de_html)
from comum import baixar_final, caminho, dominio_permitido, extrair_json, gravar_json, ler_json

URL_OPENAI = "https://api.openai.com/v1/responses"
MARCA = "GPT consultado em "
DIAS_ENTRE_CONSULTAS = 7
DIAS_CERTIFICADO = 30
POR_ENTIDADE_CERT = 2  # perguntas só de certificado da mesma entidade em cada texto (para variar as entidades)
ORDEM = ["gratuito", "situacao", "inscricoes_ate", "certificado"]

PERGUNTAS = {
    "gratuito": '"gratuito": uma frase que diga, com essas palavras, que este curso, ou as vagas do programa a que '
                'ele pertence, é gratuito (ex.: "gratuito", "vagas gratuitas", "sem custo", "sem ônus", "bolsa '
                'integral"). O nome do programa sozinho (ex.: "Programa Senac de Gratuidade") não serve.',
    "situacao": '"situacao": se as inscrições deste curso estão abertas ou encerradas HOJE ({hoje}); valor "aberto" '
                'ou "encerrado", com a frase que o diz (ex.: "inscrições abertas", "inscreva-se", "inscrições '
                'encerradas"). Um curso CLARAMENTE sob demanda, sem datas, conta como "aberto" se a página o disser com '
                'palavras (ex.: "faça no seu ritmo", "comece quando quiser", "acesso imediato"); um botão sozinho não chega.',
    "inscricoes_ate": '"inscricoes_ate": a data-limite de inscrição; valor no formato AAAA-MM-DD, com a frase onde '
                      'essa data está escrita.',
    "certificado": '"certificado": se o curso dá certificado e se é gratuito; valor "gratuito", "pago" ou "sem '
                   'certificado", com a frase que fala do certificado.',
}

PEDIDO = """Preciso de provas escritas, não de conclusões.
Curso: {titulo}
Entidade: {entidade}
Página ou edital do curso: {link}

Procure em páginas OFICIAIS desta entidade (domínio {dominio}): primeiro na própria página ou edital do curso, \
depois na página do programa no site da entidade. Não servem notícias, blogs nem sites de terceiros. Não deduza.
Para cada pergunta abaixo, copie a frase EXATA, letra a letra, sem resumir, e o link exato da página onde está:
{perguntas}

Responda só com JSON entre <json></json>, com uma chave por pergunta, assim:
{{"chave": {{"valor": "…ou null", "frase": "…", "url": "…"}}}}
Quando não encontrar uma frase para uma pergunta, ponha {{"valor": null, "frase": null, "url": null}} nessa chave."""

ABERTO = re.compile(r"inscri[çc][õo]es\s+(est[ãa]o\s+|j[áa]\s+est[ãa]o\s+)?abertas|matr[íi]culas?\s+abertas|"
                    r"inscreva-se|matricule-se|fa[çc]a\s+(a\s+sua\s+|sua\s+)?inscri[çc][ãa]o|"
                    r"(curso|inscri[çc][ãa]o)\s+(é\s+)?(aberto|aberta)|acesso\s+(livre|imediato)", re.I)
ENCERRADO = re.compile(r"encerrad|esgotad|finalizad|inscri[çc][õo]es\s+fechadas|n[ãa]o\s+h[áa]\s+vagas", re.I)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


def dominio_oficial(link):
    """Domínio da entidade a partir do link do curso: portal.ac.senac.br → ac.senac.br; www.ev.org.br → ev.org.br."""
    host = (urllib.parse.urlparse(link or "").hostname or "").lower()
    partes = host.split(".")
    return ".".join(partes[-3:] if partes and partes[-1] == "br" and len(partes) >= 3 else partes[-2:])


def gpt(modelo, pedido, dominio, chave):
    corpo = {"model": modelo, "input": pedido,
             "tools": [{"type": "web_search", "filters": {"allowed_domains": [dominio]}}]}
    req = urllib.request.Request(URL_OPENAI, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {chave}"})
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.load(r)
    texto = "".join(c.get("text", "") for item in resp.get("output", []) if item.get("type") == "message"
                    for c in item.get("content", []) if c.get("type") == "output_text")
    return texto, resp.get("usage", {})


def data_na_frase(iso, frase):
    """A data tem de estar escrita na frase (dd/mm/aaaa, dd/mm, dd.mm.aaaa ou «d de mês»)."""
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return False
    f = frase.lower()
    formas = [f"{d.day:02d}/{d.month:02d}", f"{d.day}/{d.month:02d}", f"{d.day:02d}.{d.month:02d}",
              f"{d.day} de {MESES[d.month - 1]}", f"{d.day:02d} de {MESES[d.month - 1]}", d.isoformat()]
    return any(x in f for x in formas)


def valor_diz(campo, valor, frase):
    """O código confere que a frase diz o que se afirma. Devolve (valor normalizado, motivo se falhar)."""
    valor = str(valor or "").strip().lower()
    if campo == "gratuito":
        return ("sim", "") if gratuidade_explicita(frase) else ("", "a frase não diz que não há custo")
    if campo == "situacao":
        if valor == "aberto" and (ABERTO.search(frase) or ACAO_SOB_DEMANDA.search(frase)) and not ENCERRADO.search(frase):
            return "Aberto", ""
        if valor == "encerrado" and ENCERRADO.search(frase):
            return "Encerrado", ""
        return "", "a frase não diz se as inscrições estão abertas ou encerradas"
    if campo == "inscricoes_ate":
        return (valor[:10], "") if data_na_frase(valor[:10], frase) else ("", "a data não está escrita na frase")
    if campo == "certificado":
        v = certificado_da_frase(valor, frase)
        return (v, "") if v else ("", "a frase não diz se o certificado é gratuito, pago ou inexistente")
    return "", "campo desconhecido"


def conferir(campo, resposta, dominio, paginas):
    """Prova por código de uma resposta do GPT. Devolve (valor, frase, url, motivo)."""
    resposta = resposta if isinstance(resposta, dict) else {}
    url = str(resposta.get("url") or "").strip()
    frase = re.sub(r"\s+", " ", str(resposta.get("frase") or "")).strip()
    if not url or not frase:
        return "", frase, url, "o GPT não encontrou frase"
    if not dominio_permitido(url, [dominio]):
        return "", frase, url, f"link fora do domínio oficial ({url[:80]})"
    valor, motivo = valor_diz(campo, resposta.get("valor"), frase)
    if motivo:
        return "", frase, url, f"{motivo} (“{frase[:100]}”)"
    if url not in paginas:
        try:
            bruto, final = baixar_final(url, timeout=40)
            paginas[url] = texto_de_html(bruto) if dominio_permitido(final, [dominio]) else None
        except Exception as e:  # noqa: BLE001
            paginas[url] = f"ERRO {str(e)[:60]}"
    texto = paginas[url]
    if texto is None:
        return "", frase, url, "o link redireciona para fora do domínio oficial"
    if texto.startswith("ERRO "):
        return "", frase, url, f"não foi possível abrir o link ({texto[5:]})"
    if not citacao_valida(frase, texto):
        return "", frase, url, "a frase não está na página indicada"
    return valor, frase, url, ""


def duvidas_do_curso(c):
    """Dúvidas de um curso tal como o site o mostra (docs/dados/cursos.json)."""
    d = []
    if c.get("gratuidade_comprovada") is False:
        d.append("gratuito")
    if not c.get("turmas"):
        if c.get("situacao") == "Por confirmar":
            d.append("situacao")
        if c.get("data_por_confirmar") or c.get("situacao") == "Por confirmar":
            d.append("inscricoes_ate")
    if c.get("certificado_comprovado") is False:
        d.append("certificado")
    return d


def consultado_ha_pouco(r, hoje, consultas, so_certificado=False):
    """Uma semana entre perguntas; um mês quando a única dúvida é o certificado (pesa pouco e custa o mesmo).
    A data da última pergunta fica em estado/gpt_consultas.json (a nota na folha pode ser reescrita por outras rotinas)."""
    ultima = consultas.get(r.get("ID", ""))
    if not ultima:
        m = re.search(MARCA + r"(\d{4}-\d{2}-\d{2})", r.get("O que falta confirmar") or "")
        ultima = m.group(1) if m else ""
    dias = DIAS_CERTIFICADO if so_certificado else DIAS_ENTRE_CONSULTAS
    return bool(ultima) and (hoje - datetime.date.fromisoformat(ultima)).days < dias


def registar_uso(usado, motivo, perguntas=0, resolvidas=0, tokens=None):
    """Regista cada ronda em estado/gpt.json (o resumo semanal diz se o GPT foi usado ou não) e no resumo do GitHub."""
    tokens = tokens or {}
    entrada = {"quando": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"), "usado": usado,
               "motivo": motivo, "perguntas": perguntas, "resolvidas": resolvidas,
               "tokens_entrada": int(tokens.get("input_tokens") or 0), "tokens_saida": int(tokens.get("output_tokens") or 0)}
    registo = ler_json("estado/gpt.json", [])
    gravar_json("estado/gpt.json", (registo + [entrada])[-120:])
    linha = (f"GPT usado: {perguntas} pergunta(s), {resolvidas} dúvida(s) resolvida(s) com prova, "
             f"{entrada['tokens_entrada']} tokens de entrada e {entrada['tokens_saida']} de saída." if usado
             else f"GPT não usado: {motivo}.")
    print(linha)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"### Auditoria do GPT\n\n{linha}\n")


def candidatos_do_dia(base, cfg, linhas, hoje, consultas, forcar):
    """Cursos com dúvidas, por ordem de importância (gratuidade, situação, data, depois só certificado)."""
    no_site = {c.get("id"): duvidas_do_curso(c)
               for c in ler_json("docs/dados/cursos.json", {"cursos": []}).get("cursos", [])}
    candidatos = [(r, no_site[r["ID"]]) for r in linhas if no_site.get(r.get("ID")) and curso_no_site(r, cfg)
                  and not (r.get("Revisto por pessoa") or "").strip()
                  and (forcar or not consultado_ha_pouco(r, hoje, consultas, no_site[r["ID"]] == ["certificado"]))]
    # Cursos com "Mudança a rever" marcada pelas rotinas (situação ou gratuidade em dúvida): na dúvida, o GPT audita
    # e, se o código confirmar tudo, a marca sai sozinha (regra do responsável, 21/11/2026).
    ja = {r["ID"] for r, _ in candidatos}
    for r in linhas:
        if (r.get("ID") in ja or not sim(r.get("Mudança a rever")) or r.get("Estado") not in ("Novo", "Publicado")
                or (r.get("Revisto por pessoa") or "").strip() or not r.get("Link")
                or (not forcar and consultado_ha_pouco(r, hoje, consultas))):
            continue
        comp = [c.strip() for c in (r.get("Campos comprovados") or "").split(",")]
        duv = ([] if r.get("Situação das inscrições") == "Aberto" and "situação" in comp else ["situacao"]) + \
              ([] if gratuidade_comprovada(r) else ["gratuito"])
        if duv:
            candidatos.append((r, duv))
    candidatos.sort(key=lambda x: min(ORDEM.index(d) for d in x[1]))
    return candidatos


def perguntas_agrupadas(candidatos, maximo):
    """[{n, link, dominio, duvidas, titulo, entidade, ids}] — cursos do mesmo edital com as mesmas dúvidas: uma pergunta."""
    grupos, so_cert = {}, {}
    for r, duvidas in candidatos:
        if duvidas == ["certificado"]:  # só certificado: no máximo POR_ENTIDADE_CERT perguntas da mesma entidade por texto
            dom = dominio_oficial((r.get("Página do curso") or "").strip() or r["Link"])
            if so_cert.get(dom, 0) >= POR_ENTIDADE_CERT:
                continue
            so_cert[dom] = so_cert.get(dom, 0) + 1
        link = (r.get("Página do curso") or "").strip() or r["Link"]
        especificas = any(d in ("situacao", "inscricoes_ate") for d in duvidas)
        chave = (link, tuple(duvidas), r["Título"] if especificas else "")
        if chave not in grupos:
            if len(grupos) >= maximo:
                continue
            grupos[chave] = {"n": len(grupos) + 1, "link": link, "dominio": dominio_oficial(link), "duvidas": duvidas,
                             "titulo": r["Título"], "entidade": r.get("Entidade", ""), "ids": []}
        grupos[chave]["ids"].append(r["ID"])
    return list(grupos.values())


TEXTO_CHATGPT = """Você vai me ajudar a auditar informações de cursos gratuitos para pessoas em situação de \
vulnerabilidade no Brasil. Preciso de provas escritas, não de conclusões. Use a pesquisa na web.

Regras:
- Procure só em páginas OFICIAIS da entidade de cada curso (o domínio indicado em cada curso): primeiro na própria \
página ou edital do curso, depois na página do programa no site da entidade. Não servem notícias, blogs nem sites de \
terceiros. Não deduza.
- Para cada pergunta, copie a frase EXATA, letra a letra, sem resumir, e o link exato da página onde ela está.
- Quando não encontrar uma frase, responda null nessa pergunta. É melhor null do que uma frase aproximada.
- Hoje é {hoje}.

O que significa cada pergunta:
{definicoes}

Cursos:
{cursos}

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por número de curso e, dentro, uma chave \
por pergunta, assim:
{{"1": {{"gratuito": {{"valor": "…ou null", "frase": "…", "url": "…"}}}}, "2": {{…}}}}
Quando não encontrar uma frase, ponha {{"valor": null, "frase": null, "url": null}} nessa pergunta."""


def texto_para_chatgpt(itens, hoje):
    usadas = [d for d in ORDEM if any(d in it["duvidas"] for it in itens)]
    definicoes = "\n".join("- " + PERGUNTAS[d].format(hoje=hoje.isoformat()) for d in usadas)
    cursos = "\n\n".join(f"{it['n']}. {it['titulo']}\n   Entidade: {it['entidade']}\n   Página ou edital: {it['link']}\n"
                          f"   Domínio oficial: {it['dominio']}\n   Perguntas: {', '.join(it['duvidas'])}" for it in itens)
    return TEXTO_CHATGPT.format(hoje=hoje.isoformat(), definicoes=definicoes, cursos=cursos)


def aplicar_respostas(base, linhas, itens, respostas, hoje, consultas, marca):
    """O código prova cada resposta (conferir) e grava o que passa. Devolve o número de dúvidas resolvidas."""
    por_id = {r.get("ID"): r for r in linhas}
    alteracoes, historico, paginas, provados = [], [], {}, 0
    for it in itens:
        res = respostas.get(str(it["n"])) or respostas.get(it["n"])
        if not isinstance(res, dict):
            print(f"  – {it['n']}. {it['titulo'][:50]}: sem resposta")
            continue
        for id_ in it["ids"]:
            r = por_id.get(id_)
            if not r or (r.get("Revisto por pessoa") or "").strip():
                continue
            consultas[r["ID"]] = hoje.isoformat()
            comprovados = [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()]
            evid_novas, campos, falhas = [], {}, []
            for d in it["duvidas"]:
                valor, frase, url, motivo = conferir(d, res.get(d), it["dominio"], paginas)
                rotulo = CAMPOS_PROVA[d]
                if motivo:
                    falhas.append(f"{rotulo}: {motivo}")
                    continue
                provados += 1
                evid_novas.append(f"{rotulo}: «{frase}» ({url}; {marca})")
                tirar = {rotulo, "programa"} if d == "gratuito" else {rotulo}
                comprovados = [c for c in comprovados if c not in tirar] + [rotulo]
                if d == "situacao":
                    campos["Situação das inscrições"] = valor
                elif d == "inscricoes_ate":
                    campos["Inscrições até"] = valor
                elif d == "certificado":
                    campos["Certificado"] = valor
                print(f"  ✓ {r['Título'][:50]} | {rotulo} = {valor} | «{frase[:80]}» ({url[:70]})")
                historico.append(registo_historico(r, "GPT + código", f"{rotulo} comprovado: {valor}", campos,
                                                   f"«{frase[:200]}» {url}"))
            for f in falhas:
                print(f"  ✗ {r['Título'][:50]} | {f}")
            falta = re.sub(r"\[" + MARCA + r"\d{4}-\d{2}-\d{2}:[^\]]*\]\s*", "", r.get("O que falta confirmar") or "").strip()
            if evid_novas:
                if any(e.startswith("gratuito:") for e in evid_novas):
                    falta = re.sub(r"O edital não diz por escrito que o curso é gratuito[^.]*\.\s*", "", falta).strip()
                campos["Campos comprovados"] = ", ".join(dict.fromkeys(comprovados))
                campos["Evidência"] = (" | ".join(evid_novas) + " | " + (r.get("Evidência") or "")).strip(" |")[:1500]
            if falhas:
                falta = (f"[{MARCA}{hoje.isoformat()}: " + "; ".join(f.replace("]", ")") for f in falhas) + "] "
                         + falta).strip()
            campos["O que falta confirmar"] = falta[:900]
            if sim(r.get("Mudança a rever")) and not falhas and evid_novas:
                campos["Mudança a rever"] = "FALSE"
                nota = f"{hoje.isoformat()}: “Mudança a rever” desmarcada depois da auditoria do GPT, conferida por código."
                if r.get("Estado") == "Novo" and campos.get("Situação das inscrições", r.get("Situação das inscrições")) == "Aberto":
                    campos["Estado"] = "Publicado"
                    nota += " Publicado: inscrições abertas e gratuidade comprovadas."
                campos["Nota da verificação"] = (nota + " " + (r.get("Nota da verificação") or ""))[:900]
                historico.append(registo_historico(r, "GPT + código", "Mudança a rever desmarcada", campos, nota))
            alteracoes.append((r["_linha"], campos))
    base.atualizar("Cursos", alteracoes)
    gravar_json("estado/gpt_consultas.json", consultas)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    return provados


def main():
    """Três modos (variável GPT_MODO):
    - "texto" (o normal desde 22/11/2026, decisão do responsável: a API custa caro): prepara o texto da auditoria
      para colar no ChatGPT da assinatura do responsável. Grava estado/auditoria_chatgpt.md (o texto) e
      estado/auditoria_chatgpt.json (a que cursos corresponde cada número). Não chama a OpenAI.
    - "resposta": lê a resposta do ChatGPT em estado/resposta_chatgpt.txt (colada pelo responsável), prova cada
      frase por código, como sempre, e grava o que passa.
    - "api": o modo antigo, pela API da OpenAI (só com o segredo OPENAI_API_KEY; desligado nas rotinas)."""
    modo = os.environ.get("GPT_MODO", "texto").strip().lower()
    base = Base()
    cfg = carregar_config(base)
    conf = cfg.get("gpt", {})
    maximo = int(os.environ.get("GPT_MAX_CONSULTAS", conf.get("max_consultas", 10)))
    forcar = os.environ.get("GPT_FORCAR", "") == "1"  # ignora o intervalo entre consultas
    hoje = datetime.date.today()
    linhas = base.tabela("Cursos")
    consultas = ler_json("estado/gpt_consultas.json", {})

    if modo == "resposta":
        pedido = ler_json("estado/auditoria_chatgpt.json", {})
        try:
            with open(caminho("estado", "resposta_chatgpt.txt"), encoding="utf-8") as f:
                bruto = f.read()
        except OSError:
            bruto = ""
        texto_json = bruto if "<json>" in bruto else f"<json>{bruto[bruto.find('{'):bruto.rfind('}') + 1]}</json>"
        respostas = extrair_json(texto_json) if bruto.strip() else None
        if not pedido.get("itens") or not isinstance(respostas, dict):
            registar_uso(False, "resposta do ChatGPT em falta ou sem JSON")
            return
        print(f"Resposta do ChatGPT ao texto de {pedido.get('data')}: {len(respostas)} curso(s) respondidos.")
        provados = aplicar_respostas(base, linhas, pedido["itens"], respostas, hoje, consultas, MARCA_CHATGPT)
        registar_uso(True, "ChatGPT (assinatura), resposta colada pelo responsável", len(pedido["itens"]), provados)
        return

    candidatos = candidatos_do_dia(base, cfg, linhas, hoje, consultas, forcar)
    itens = perguntas_agrupadas(candidatos, maximo)
    print(f"Cursos com dúvidas: {len(candidatos)}; perguntas nesta rodada: {len(itens)} (máximo {maximo})")

    if modo != "api":
        if not itens:
            registar_uso(False, "nenhuma dúvida para perguntar nesta rodada")
            return
        texto = texto_para_chatgpt(itens, hoje)
        with open(caminho("estado", "auditoria_chatgpt.md"), "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        gravar_json("estado/auditoria_chatgpt.json", {"data": hoje.isoformat(), "itens": itens})
        registar_uso(False, f"API desligada; texto de auditoria para o ChatGPT preparado ({len(itens)} perguntas, "
                            f"estado/auditoria_chatgpt.md)")
        return

    chave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not chave:
        registar_uso(False, "sem chave da OpenAI (segredo OPENAI_API_KEY ou SOCIAL_PROJECT)")
        return
    modelo = conf.get("modelo", "gpt-5.5")
    respostas, tokens, erro_conta = {}, {"input_tokens": 0, "output_tokens": 0}, ""
    for it in itens:
        pedido = PEDIDO.format(titulo=it["titulo"], entidade=it["entidade"], link=it["link"], dominio=it["dominio"],
                               perguntas="\n".join("- " + PERGUNTAS[d].format(hoje=hoje.isoformat())
                                                   for d in it["duvidas"]))
        try:
            texto, uso = gpt(modelo, pedido, it["dominio"], chave)
            for k in tokens:
                tokens[k] += int(uso.get(k) or 0)
            respostas[str(it["n"])] = extrair_json(texto) or {}
        except urllib.error.HTTPError as e:
            print(f"  ! OpenAI respondeu {e.code}: {e.read()[:300]!r}")
            if e.code in (401, 403, 429):
                erro_conta = f"a OpenAI recusou o pedido ({e.code})"
                break
        except Exception as e:  # noqa: BLE001
            print(f"  ! {it['titulo']}: {e}")
    provados = aplicar_respostas(base, linhas, itens, respostas, hoje, consultas, MARCA_GPT)
    if tokens["input_tokens"]:
        registar_uso(True, erro_conta, len(respostas), provados, tokens)
    else:
        registar_uso(False, erro_conta or "sem resposta da OpenAI")


if __name__ == "__main__":
    sys.exit(main())
