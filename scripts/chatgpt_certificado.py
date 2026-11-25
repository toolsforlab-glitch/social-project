"""Rodada do ChatGPT (assinatura do responsável): o CERTIFICADO dos cursos, uma pergunta por entidade (25/11/2026).

Porquê: cerca de 390 cursos do site não têm prova de que o certificado é gratuito, e quase todos são de poucas
entidades (Sebrae, SENAI Pará, Senac Pará, Senac Ceará, Ifap…). Pela regra «ou é grátis ou não é», um certificado
pago tira o curso do site. Uma frase oficial por entidade resolve dezenas de cursos de uma vez.

Dois modos (variável GPT_MODO):
- "texto" (por omissão): escolhe as entidades com 3 ou mais cursos no site sem certificado provado e grava o texto
  para colar no ChatGPT (estado/chatgpt_certificado.md) e a lista das entidades (estado/chatgpt_certificado.json).
  Não chama a OpenAI e não mexe na planilha.
- "resposta": lê a resposta colada em estado/resposta_certificado.txt e PROVA cada frase por código:
  link do domínio oficial da entidade (também depois de redirecionar), frase letra a letra na página ou no PDF, e a
  frase tem de dizer como é o CERTIFICADO (certificado_da_frase; «curso gratuito e com certificado» não chega).
  · «gratuito» ou «sem certificado» provados: grava em todos os cursos dessa entidade sem certificado provado
    (coluna Certificado, Evidência com a marca do ChatGPT, Campos comprovados).
  · «pago» provado: NÃO grava (tiraria os cursos do site); abre uma pendência para uma pessoa decidir.
  Cursos com «Revisto por pessoa» nunca são alterados.
"""
import io
import json
import os
import re
import sys

from base import (HISTORICO, MARCA_CHATGPT, Base, certificado_da_frase, citacao_valida, registar_pendencia,
                  registo_historico, texto_de_html)
from comum import baixar_final, caminho, dominio_permitido, extrair_json, gravar_json, ler_json
from consultar_gpt import dominio_oficial, registar_uso

MINIMO_CURSOS = 3
TEXTO = "estado/chatgpt_certificado.md"
LISTA = "estado/chatgpt_certificado.json"
RESPOSTA = "estado/resposta_certificado.txt"

CONTEXTO = {  # o que já se sabe, para o ChatGPT não repetir caminhos que não deram em nada
    "sebrae.com.br": "Os Termos de Uso da Loja Sebrae (item 7.3) dizem que, depois de concluir o curso online e "
                     "responder à pesquisa de satisfação, o certificado fica disponível na área do cliente, mas não "
                     "dizem se é gratuito. Os cursos têm a etiqueta «R$ 0,00 Gratuito».",
    "senaipa.org.br": "Cursos do Programa SENAI de Gratuidade Regimental, pelo «Edital Unificado» GEEP nº 06-2026.",
    "pa.senac.br": "Cursos do Programa Senac de Gratuidade (PSG), pelas seleções do portal pa.senac.br/psg.",
    "ce.senac.br": "Cursos do Programa Senac de Gratuidade (PSG), turmas em psg.ce.senac.br.",
    "ifap.edu.br": "Cursos técnicos integrados ao ensino médio (Proeja), Edital nº 18/2026 – Proen/Ifap. "
                   "Procure no edital ou no regulamento dos cursos se o diploma/certificado é emitido sem custo.",
}

PEDIDO = """Você vai me ajudar a auditar informações de cursos gratuitos para pessoas em situação de \
vulnerabilidade no Brasil. Preciso de provas escritas, não de conclusões. Use a pesquisa na web.

Pergunta, para cada entidade abaixo: existe alguma página OFICIAL dessa entidade (no domínio indicado: página de \
curso, edital, regulamento, perguntas frequentes, ajuda, termos de uso) que diga EXPLICITAMENTE como é o \
CERTIFICADO dos cursos: gratuito (sem custo), pago, ou que não há certificado?

Regras:
- A frase tem de falar do CERTIFICADO. Não basta dizer que o curso é gratuito ("curso gratuito e com certificado" \
não serve: tem de ser o certificado que é gratuito).
- Só páginas do domínio oficial indicado em cada entidade. Não servem notícias, blogs nem sites de terceiros.
- Copie cada frase EXATA, letra a letra, sem resumir nem corrigir, com o link exato da página ou do PDF.
- Diga a que cursos a frase se aplica (todos os cursos da entidade, só os de um programa, só um curso).
- Não deduza. Quando não encontrar, responda uma lista vazia para essa entidade. É melhor vazio do que uma frase \
aproximada.
- Até 3 frases por entidade.

Entidades:
{entidades}

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por número de entidade:
{{"1": [{{"valor": "gratuito|pago|sem certificado", "frase": "…", "url": "…", "aplica_se_a": "…"}}], "2": []}}"""


def entidades_sem_prova():
    """Entidades com MINIMO_CURSOS ou mais cursos no site sem certificado provado, das que têm mais para as que têm menos."""
    cursos = ler_json("docs/dados/cursos.json", {"cursos": []}).get("cursos", [])
    grupos = {}
    for c in cursos:
        if c.get("certificado_comprovado") is not False or not c.get("entidade") or not c.get("url"):
            continue
        g = grupos.setdefault(c["entidade"], {"entidade": c["entidade"], "dominio": dominio_oficial(c["url"]),
                                              "exemplos": [], "cursos": 0})
        g["cursos"] += 1
        if len(g["exemplos"]) < 2 and c["url"] not in g["exemplos"]:
            g["exemplos"].append(c["url"])
    lista = [g for g in grupos.values() if g["cursos"] >= MINIMO_CURSOS]
    lista.sort(key=lambda g: -g["cursos"])
    for n, g in enumerate(lista, 1):
        g["n"] = n
    return lista


def texto_do_link(url, dominio):
    """Texto da página ou do PDF, só se o link (e o destino final) for do domínio oficial. (texto, motivo)."""
    try:
        bruto, final = baixar_final(url, timeout=60)
    except Exception as e:  # noqa: BLE001
        return "", f"não foi possível abrir o link ({str(e)[:60]})"
    if not dominio_permitido(final, [dominio]):
        return "", "o link redireciona para fora do domínio oficial"
    if bruto[:5] == b"%PDF-":
        try:
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(bruto)).pages), ""
        except Exception as e:  # noqa: BLE001
            return "", f"não foi possível ler o PDF ({str(e)[:60]})"
    return texto_de_html(bruto), ""


def provar(r, dominio, paginas):
    """(valor, frase, url, motivo) de uma frase da resposta."""
    frase = re.sub(r"\s+", " ", str((r or {}).get("frase") or "")).strip()
    url = str((r or {}).get("url") or "").strip()
    if not frase or not url:
        return "", frase, url, "sem frase ou sem link"
    if not dominio_permitido(url, [dominio]):
        return "", frase, url, f"link fora do domínio oficial ({url[:80]})"
    valor = certificado_da_frase(r.get("valor"), frase)
    if not valor:
        return "", frase, url, "a frase não diz como é o CERTIFICADO (gratuito, pago ou sem certificado)"
    if url not in paginas:
        paginas[url] = texto_do_link(url, dominio)
    texto, motivo = paginas[url]
    if motivo:
        return "", frase, url, motivo
    if not citacao_valida(frase, texto):
        return "", frase, url, "a frase não está na página indicada"
    return valor, frase, url, ""


def aplicar(lista, respostas):
    base = Base()
    linhas = base.tabela("Cursos")
    alteracoes, historico, paginas, provadas = [], [], {}, 0
    for e in lista:
        frases = respostas.get(str(e["n"])) or respostas.get(e["n"]) or []
        print(f"\n=== {e['n']}. {e['entidade']} ({e['dominio']}, {e['cursos']} cursos sem certificado provado) ===")
        if not isinstance(frases, list) or not frases:
            print("  sem frase na resposta")
            continue
        escolhida = None
        for r in frases:
            valor, frase, url, motivo = provar(r, e["dominio"], paginas)
            print(f"  {'✓' if not motivo else '✗'} {valor or r.get('valor')} | «{frase[:120]}» ({url[:80]})"
                  + (f" — recusada: {motivo}" if motivo else f" — aplica-se a: {str(r.get('aplica_se_a') or '')[:80]}"))
            if not motivo and (escolhida is None or (valor == "gratuito" and escolhida[0] != "gratuito")):
                escolhida = (valor, frase, url, str(r.get("aplica_se_a") or ""))
        if not escolhida:
            continue
        provadas += 1
        valor, frase, url, aplica = escolhida
        if valor == "pago":
            registar_pendencia(base, f"{e['entidade']}: o ChatGPT achou uma frase oficial dizendo que o certificado é "
                                     f"PAGO (conferida por código). Pela regra, esses cursos sairiam do site.",
                               f"Ler a frase e decidir. Frase: «{frase[:300]}». Aplica-se a: {aplica[:150]}. "
                               f"Se valer para todos os cursos da entidade, marcar o Certificado como «pago».",
                               url, e["exemplos"][0] if e["exemplos"] else "", origem="chatgpt_certificado.py")
            print("  → certificado PAGO: pendência aberta, nada gravado")
            continue
        # A frase vale para a entidade inteira só se vier de um documento geral (regimento, resolução, regulamento,
        # perguntas frequentes, termos) ou se o ChatGPT disser que se aplica a todos os cursos. Se vier da página de
        # OUTRO curso (ex.: a loja do Sebrae de Santa Catarina), o código procura a mesma frase na página de cada um
        # dos nossos cursos e só grava onde a encontra (25/11/2026: não se deduz de um curso para outro).
        geral = bool(re.search(r"\btodos\b|regimento|resolu[çc]|normativ|regulamento|perguntas frequentes|faq|termos",
                               aplica + " " + url, re.I))
        print(f"  frase {'geral (vale para a entidade)' if geral else 'de um curso: confere-se curso a curso'}")
        n = 0
        for r in linhas:
            if (r.get("Entidade") != e["entidade"] or (r.get("Revisto por pessoa") or "").strip()
                    or "certificado" in [c.strip() for c in (r.get("Campos comprovados") or "").split(",")]):
                continue
            url_curso = url
            if not geral:
                url_curso = (r.get("Página do curso") or "").strip() or r.get("Link", "")
                if url_curso not in paginas:
                    paginas[url_curso] = texto_do_link(url_curso, e["dominio"])
                texto_curso, motivo_curso = paginas[url_curso]
                if motivo_curso or not citacao_valida(frase, texto_curso):
                    continue
            comp = [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()] + ["certificado"]
            evid = (f"certificado: «{frase}» ({url_curso}; {MARCA_CHATGPT}"
                    + ("; frase da entidade, vale para os seus cursos)" if geral else "; na página do próprio curso)"))
            campos = {"Certificado": valor, "Campos comprovados": ", ".join(dict.fromkeys(comp)),
                      "Evidência": (evid + " | " + (r.get("Evidência") or "")).strip(" |")[:1500]}
            alteracoes.append((r["_linha"], campos))
            historico.append(registo_historico(r, "ChatGPT + código", f"certificado comprovado: {valor}", campos,
                                               f"«{frase[:200]}» {url}"))
            n += 1
        print(f"  → certificado «{valor}» gravado em {n} curso(s)")
    base.atualizar("Cursos", alteracoes)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    return provadas


def main():
    modo = os.environ.get("GPT_MODO", "texto").strip().lower()
    if modo == "resposta":
        pedido = ler_json(LISTA, {})
        try:
            with open(caminho(*RESPOSTA.split("/")), encoding="utf-8") as f:
                bruto = f.read()
        except OSError:
            bruto = ""
        respostas = extrair_json(bruto if "<json>" in bruto else f"<json>{bruto[bruto.find('{'):bruto.rfind('}') + 1]}</json>")
        if not pedido.get("entidades") or not isinstance(respostas, dict):
            registar_uso(False, "certificado por entidade: resposta do ChatGPT em falta ou sem JSON")
            return
        provadas = aplicar(pedido["entidades"], respostas)
        registar_uso(True, "certificado por entidade (ChatGPT da assinatura)", len(pedido["entidades"]), provadas)
        return
    lista = entidades_sem_prova()
    if not lista:
        registar_uso(False, "certificado por entidade: nenhuma entidade com cursos sem certificado provado")
        return
    blocos = []
    for e in lista:
        dom = e["dominio"]
        ctx = next((v for k, v in CONTEXTO.items() if dom == k or dom.endswith("." + k)), "")
        blocos.append(f"{e['n']}. {e['entidade']}\n   Domínio oficial: {dom}\n   Cursos no nosso site: {e['cursos']}\n"
                      f"   Exemplos de curso: {' ; '.join(e['exemplos'])}" + (f"\n   O que já sabemos: {ctx}" if ctx else ""))
    with open(caminho(*TEXTO.split("/")), "w", encoding="utf-8") as f:
        f.write(PEDIDO.format(entidades="\n\n".join(blocos)) + "\n")
    gravar_json(LISTA, {"entidades": lista})
    print(f"Texto para o ChatGPT: {TEXTO} ({len(lista)} entidades, {sum(e['cursos'] for e in lista)} cursos)")
    for e in lista:
        print(f"  {e['n']}. {e['entidade']} | {e['dominio']} | {e['cursos']}")


if __name__ == "__main__":
    sys.exit(main())
