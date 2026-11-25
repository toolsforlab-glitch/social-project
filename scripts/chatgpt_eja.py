"""Rodada do ChatGPT (assinatura do responsável): matrícula na EJA das redes estaduais, um estado por pergunta
(25/11/2026; pedido do responsável: EJA na varredura dos estados).

As vigias de notícias (vigiar.py, «EJA – <estado>») só avisam quando sai notícia. Esta rodada procura já as páginas
OFICIAIS das secretarias de educação com o período de matrícula na EJA para 2027 (ou a matrícula o ano todo).

Dois modos (variável GPT_MODO):
- "texto" (por omissão): grava o texto para colar no ChatGPT (estado/chatgpt_eja.md) e a lista dos estados
  (estado/chatgpt_eja.json). Não chama a OpenAI e não mexe na planilha.
- "resposta": lê a resposta colada em estado/resposta_eja.txt e PROVA cada frase por código:
  · link de um domínio público do estado (….<uf>.gov.br, incluindo prefeituras) ou do MEC (gov.br), também depois
    de redirecionar;
  · a frase está letra a letra na página ou no PDF, e a página fala de EJA / Educação de Jovens e Adultos;
  · a frase do período fala de matrícula ou inscrição e traz uma data (ou diz que é o ano todo).
  O que passa vira uma linha nas «Pendências para verificar» (com a frase e o link) e fica em
  estado/chatgpt_eja_resultado.json. Os cursos são criados depois, a partir dessas páginas, como manda a regra:
  nenhum curso entra só pela resposta do ChatGPT.
"""
import os
import re
import sys

from base import Base, citacao_valida, registar_pendencia
from chatgpt_certificado import texto_do_link
from comum import caminho, extrair_json, gravar_json, ler_json
from consultar_gpt import registar_uso

TEXTO = "estado/chatgpt_eja.md"
LISTA = "estado/chatgpt_eja.json"
RESPOSTA = "estado/resposta_eja.txt"
RESULTADO = "estado/chatgpt_eja_resultado.json"
ESTADOS = [("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"), ("BA", "Bahia"), ("CE", "Ceará"),
           ("MA", "Maranhão"), ("PA", "Pará"), ("PB", "Paraíba"), ("PE", "Pernambuco"), ("PI", "Piauí"),
           ("RN", "Rio Grande do Norte"), ("RO", "Rondônia"), ("RR", "Roraima"), ("SE", "Sergipe"), ("TO", "Tocantins")]
DATA = re.compile(r"\b\d{1,2}\s*(/|de)\s*(\d{1,2}|janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|"
                  r"outubro|novembro|dezembro)\b|o ano (todo|inteiro)|durante todo o ano|ao longo (de todo )?do ano|"
                  r"permanente|fluxo cont[íi]nuo", re.I)
EJA = re.compile(r"\bEJA\b|jovens,? e adultos", re.I)

PEDIDO = """Você vai me ajudar a encontrar onde e quando pessoas jovens e adultas podem se matricular na EJA \
(Educação de Jovens e Adultos) da rede pública estadual, para voltar a estudar. Preciso de provas escritas, não de \
conclusões. Use a pesquisa na web. Hoje é {hoje}.

Para cada estado abaixo, procure a página OFICIAL da Secretaria de Educação do estado (domínio terminado em \
.<sigla do estado>.gov.br, por exemplo seduc.ce.gov.br ou educacao.ba.gov.br) que diga:
- "periodo": o período de matrícula ou inscrição na EJA para 2027 (ou para o 1º semestre de 2027), ou que a \
matrícula na EJA fica aberta o ano todo. Pode ser uma notícia no site da própria secretaria, uma portaria ou um \
edital de matrícula.
- "como": como e onde a pessoa se matricula na EJA (site de matrícula, na escola, telefone).
- "requisitos": idade mínima ou documentos pedidos para a matrícula na EJA.

Regras:
- Só sites oficiais do governo do estado (….<sigla>.gov.br). Não servem jornais, blogs, portais de notícias nem \
sites de terceiros.
- Copie cada frase EXATA, letra a letra, sem resumir nem corrigir, com o link exato da página ou do PDF.
- Se só houver informação de 2026 (matrícula já encerrada), diga isso no campo "observacao" e ponha as frases de \
2027 como null.
- Não deduza. Quando não encontrar, ponha null. É melhor null do que uma frase aproximada.

Estados:
{estados}

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por sigla do estado:
{{"CE": {{"periodo": {{"frase": "…", "url": "…"}}, "como": {{"frase": "…", "url": "…"}}, \
"requisitos": {{"frase": "…", "url": "…"}}, "observacao": "…"}}, "BA": {{…}}}}"""


def dominio_ok(url, uf):
    m = re.match(r"https?://([^/:?#]+)", url or "")
    host = (m.group(1).lower() if m else "")
    return host.endswith(f".{uf.lower()}.gov.br") or host == f"{uf.lower()}.gov.br" or host in ("gov.br", "www.gov.br") \
        or host.endswith(".mec.gov.br")


def provar(item, uf, campo, paginas):
    item = item if isinstance(item, dict) else {}
    frase = re.sub(r"\s+", " ", str(item.get("frase") or "")).strip()
    url = str(item.get("url") or "").strip()
    if not frase or not url:
        return "", "", "sem frase"
    if not dominio_ok(url, uf):
        return frase, url, f"link fora dos sites oficiais do estado ({url[:80]})"
    if campo == "periodo" and not (DATA.search(frase) and re.search(r"matr[íi]cul|inscri", frase, re.I)):
        return frase, url, "a frase não traz período de matrícula (data ou «o ano todo»)"
    if url not in paginas:
        paginas[url] = texto_do_link(url, f"{uf.lower()}.gov.br") if not re.search(r"(^|\.)mec\.gov\.br|//(www\.)?gov\.br", url) \
            else texto_do_link(url, "gov.br")
    texto, motivo = paginas[url]
    if motivo:
        return frase, url, motivo
    if not citacao_valida(frase, texto):
        return frase, url, "a frase não está na página indicada"
    if not EJA.search(texto):
        return frase, url, "a página não fala de EJA"
    return frase, url, ""


def main():
    import datetime
    modo = os.environ.get("GPT_MODO", "texto").strip().lower()
    hoje = datetime.date.today().isoformat()
    if modo != "resposta":
        estados = "\n".join(f"- {uf}: {nome}" for uf, nome in ESTADOS)
        with open(caminho(*TEXTO.split("/")), "w", encoding="utf-8") as f:
            f.write(PEDIDO.format(hoje=hoje, estados=estados) + "\n")
        gravar_json(LISTA, {"data": hoje, "estados": [uf for uf, _ in ESTADOS]})
        print(f"Texto para o ChatGPT: {TEXTO} ({len(ESTADOS)} estados)")
        return
    try:
        with open(caminho(*RESPOSTA.split("/")), encoding="utf-8") as f:
            bruto = f.read()
    except OSError:
        bruto = ""
    respostas = extrair_json(bruto if "<json>" in bruto else f"<json>{bruto[bruto.find('{'):bruto.rfind('}') + 1]}</json>")
    if not isinstance(respostas, dict):
        registar_uso(False, "EJA: resposta do ChatGPT em falta ou sem JSON")
        return
    base = Base()
    nomes = dict(ESTADOS)
    paginas, resultado, achados = {}, {}, 0
    for uf in [u for u, _ in ESTADOS]:
        r = respostas.get(uf) or {}
        print(f"\n=== {uf} – {nomes[uf]} ===" + (f" (observação: {str(r.get('observacao'))[:160]})" if r.get("observacao") else ""))
        provadas = {}
        for campo in ("periodo", "como", "requisitos"):
            frase, url, motivo = provar(r.get(campo), uf, campo, paginas)
            if not frase and motivo == "sem frase":
                print(f"  – {campo}: sem frase")
                continue
            print(f"  {'✓' if not motivo else '✗'} {campo}: «{frase[:140]}» ({url[:80]})" + (f" — recusada: {motivo}" if motivo else ""))
            if not motivo:
                provadas[campo] = {"frase": frase, "url": url}
        if provadas:
            resultado[uf] = provadas
        if "periodo" in provadas:
            achados += 1
            p = provadas["periodo"]
            extra = " | ".join(f"{k}: «{v['frase'][:200]}» ({v['url']})" for k, v in provadas.items() if k != "periodo")
            registar_pendencia(base, f"EJA – {nomes[uf]}: página oficial com o período de matrícula (ChatGPT, conferida "
                                     f"por código): «{p['frase'][:200]}»",
                               "Pedir ao Claude para criar o curso de EJA em «Terminar a escola» a partir desta página "
                               f"(período, onde e como se matricular, requisitos). {extra}"[:900],
                               p["url"], (provadas.get("como") or {}).get("url", ""), origem="chatgpt_eja.py")
    gravar_json(RESULTADO, {"data": hoje, "estados": resultado})
    base.guardar()
    registar_uso(True, "EJA por estado (ChatGPT da assinatura)", len(ESTADOS), achados)


if __name__ == "__main__":
    sys.exit(main())
