"""Segunda opinião do GPT (OpenAI) para tirar dúvidas que a rotina não conseguiu provar. Hoje: gratuidade.

Regra do projeto: o GPT só APONTA onde pode estar a resposta (link e frase); quem prova é o código.
Para cada curso visível no site cuja gratuidade não está comprovada (o site mostra «Gratuidade por confirmar»):

1. pergunta ao GPT, com pesquisa na web limitada ao domínio oficial da entidade do curso, por uma frase que diga
   explicitamente que o curso (ou as vagas do programa) é gratuito, e pelo link dessa frase;
2. o código abre o link e só aceita se:
   - o link é do domínio oficial da entidade (o mesmo domínio do link do curso, ex.: ac.senac.br);
   - a frase existe letra a letra no texto da página (citacao_valida);
   - a frase diz que não há custo (gratuidade_explicita: o nome do programa não chega);
3. se passar, grava a frase na Evidência («gratuito: «…» (link) — encontrada pelo GPT, conferida por código») e
   «gratuito» em Campos comprovados; se não passar, regista a consulta em «O que falta confirmar» e só volta a
   perguntar passados DIAS_ENTRE_CONSULTAS dias.

Sem o segredo OPENAI_API_KEY, o script não faz nada. Cursos com «Revisto por pessoa» nunca são alterados.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from base import (HISTORICO, Base, carregar_config, citacao_valida, curso_no_site, gratuidade_comprovada,
                  gratuidade_explicita, registo_historico, texto_de_html)
from comum import baixar_final, dominio_permitido, extrair_json

URL_OPENAI = "https://api.openai.com/v1/responses"
MARCA = "GPT consultado em "
DIAS_ENTRE_CONSULTAS = 7

PEDIDO = """Preciso de uma prova escrita, não de uma conclusão.
Curso: {titulo}
Entidade: {entidade}
Página ou edital do curso: {link}

Procure numa página OFICIAL desta entidade (domínio {dominio}) uma frase que diga, com essas palavras, que este \
curso, ou as vagas do programa a que ele pertence, é gratuito (ex.: "gratuito", "vagas gratuitas", "sem custo", \
"bolsa integral"). Procure primeiro na própria página ou edital do curso e depois na página do programa no site \
da entidade. Não servem notícias, blogs nem sites de terceiros. O nome do programa sozinho (ex.: "Programa Senac \
de Gratuidade") não serve. Não deduza.

Responda só com JSON entre <json></json>: {{"url": "link exato da página onde está a frase", "frase": "a frase \
copiada letra a letra, sem resumir"}}. Se não encontrar, responda <json>{{"url": null, "frase": null}}</json>."""


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
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)
    texto = "".join(c.get("text", "") for item in resp.get("output", []) if item.get("type") == "message"
                    for c in item.get("content", []) if c.get("type") == "output_text")
    return texto, resp.get("usage", {})


def conferir(url, frase, dominio):
    """Prova por código. Devolve (ok, motivo)."""
    if not url or not frase:
        return False, "o GPT não encontrou frase"
    if not dominio_permitido(url, [dominio]):
        return False, f"link fora do domínio oficial ({url})"
    if not gratuidade_explicita(frase):
        return False, f"a frase não diz que não há custo («{frase[:120]}»)"
    try:
        bruto, final = baixar_final(url, timeout=40)
    except Exception as e:  # noqa: BLE001
        return False, f"não foi possível abrir o link ({str(e)[:80]})"
    if not dominio_permitido(final, [dominio]):
        return False, f"o link redireciona para fora do domínio oficial ({final})"
    if not citacao_valida(frase, texto_de_html(bruto)):
        return False, "a frase não está na página indicada"
    return True, ""


def consultado_ha_pouco(r, hoje):
    m = re.search(MARCA + r"(\d{4}-\d{2}-\d{2})", r.get("O que falta confirmar") or "")
    return bool(m) and (hoje - datetime.date.fromisoformat(m.group(1))).days < DIAS_ENTRE_CONSULTAS


def main():
    chave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not chave:
        print("Sem OPENAI_API_KEY: segunda opinião do GPT desligada.")
        return
    base = Base()
    cfg = carregar_config(base)
    conf = cfg.get("gpt", {})
    modelo = conf.get("modelo", "gpt-5.5")
    maximo = int(os.environ.get("GPT_MAX_CONSULTAS", conf.get("max_consultas", 10)))
    forcar = os.environ.get("GPT_FORCAR", "") == "1"  # ignora o intervalo entre consultas (testes)
    hoje = datetime.date.today()
    linhas = base.tabela("Cursos")
    candidatos = [r for r in linhas if curso_no_site(r, cfg) and not (r.get("Revisto por pessoa") or "").strip()
                  and not gratuidade_comprovada(r) and (forcar or not consultado_ha_pouco(r, hoje))]
    print(f"Cursos com gratuidade por confirmar a consultar: {len(candidatos)} (máximo {maximo}); modelo {modelo}")
    alteracoes, historico, por_link, tokens = [], [], {}, {"input_tokens": 0, "output_tokens": 0}
    for r in candidatos[:maximo]:
        link = (r.get("Página do curso") or "").strip() or r["Link"]
        dominio = dominio_oficial(link)
        if link not in por_link:  # cursos do mesmo edital: uma só pergunta
            try:
                texto, uso = gpt(modelo, PEDIDO.format(titulo=r["Título"], entidade=r.get("Entidade", ""), link=link,
                                                      dominio=dominio), dominio, chave)
                for k in tokens:
                    tokens[k] += int(uso.get(k) or 0)
                res = extrair_json(texto) or {}
            except urllib.error.HTTPError as e:
                print(f"  ! OpenAI respondeu {e.code}: {e.read()[:300]!r}")
                if e.code in (401, 403, 429):
                    break
                continue
            except Exception as e:  # noqa: BLE001
                print(f"  ! {r['Título']}: {e}")
                continue
            url, frase = str(res.get("url") or "").strip(), re.sub(r"\s+", " ", str(res.get("frase") or "")).strip()
            por_link[link] = (url, frase, *conferir(url, frase, dominio))
        url, frase, ok, motivo = por_link[link]
        falta = re.sub(MARCA + r"\d{4}-\d{2}-\d{2}[^.]*\.\s*", "", r.get("O que falta confirmar") or "").strip()
        if ok:
            comprovados = [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()]
            comprovados = ["gratuito"] + [c for c in comprovados if c not in ("gratuito", "programa")]
            falta = re.sub(r"O edital não diz por escrito que o curso é gratuito[^.]*\.\s*", "", falta).strip()
            evid = f"gratuito: «{frase}» ({url}; encontrada pelo GPT, conferida por código)"
            campos = {"Campos comprovados": ", ".join(comprovados),
                      "Evidência": (evid + " | " + (r.get("Evidência") or "")).strip(" |")[:1500],
                      "O que falta confirmar": falta[:900]}
            print(f"  ✓ {r['Título']}: «{frase[:90]}» ({url})")
            historico.append(registo_historico(r, "GPT + código", "Gratuidade comprovada", {}, f"«{frase[:200]}» {url}"))
        else:
            campos = {"O que falta confirmar": (f"{MARCA}{hoje.isoformat()}: {motivo}. " + falta).strip()[:900]}
            print(f"  ✗ {r['Título']}: {motivo}")
        alteracoes.append((r["_linha"], campos))
    base.atualizar("Cursos", alteracoes)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Consultas: {len(por_link)}; comprovados: {sum(1 for v in por_link.values() if v[2])}; "
          f"tokens: {tokens['input_tokens']} de entrada, {tokens['output_tokens']} de saída.")


if __name__ == "__main__":
    sys.exit(main())
