"""Verificação semanal: o Claude relê a página de cada curso visível, confirma se continua aberto e gratuito
e escreve o passo a passo de inscrição em linguagem simples."""
import html
import os
import re
import sys

from base import HISTORICO, SITUACOES, Base, carregar_config, hoje_iso, registo_historico, sim, visivel
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json

ABA = "Cursos"
MAX_POR_EXECUCAO = int(os.environ.get("MAX_VERIFICACOES", "60"))
MAX_CARACTERES = 12000

SISTEMA = """Verificas cursos gratuitos para um site público. Recebes os dados que temos sobre um curso e \
o texto da página oficial. Responde só com base no texto da página: não inventes.

Devolve JSON entre <json></json> com:
- "situacao": "aberto" (inscrições abertas, acesso livre, ou turma futura), "encerrado" (a página diz \
claramente que as inscrições terminaram ou o curso acabou) ou "incerto".
- "gratuito": "sim", "não" ou "incerto".
- "inscricoes_ate": data AAAA-MM-DD se a página a indicar, senão null.
- "como_me_inscrever": lista de 3 a 5 passos curtos, em linguagem muito simples, com o que a pessoa tem de \
fazer (onde ir, que documentos levar, até quando). Para cursos no Brasil escreve em português do Brasil; \
em Portugal, em português de Portugal. Se a página não explicar, dá os passos gerais que ela permite saber.
- "nota": uma frase curta a explicar o que verificaste (ex.: "Inscrições abertas até 30/11 no site do Senac")."""


def texto_da_pagina(url):
    bruto = baixar(url, timeout=30).decode("utf-8", "replace")
    bruto = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", bruto)
    bruto = re.sub(r"(?s)<[^>]+>", " ", bruto)
    return re.sub(r"\s+", " ", html.unescape(bruto)).strip()[:MAX_CARACTERES]


def main():
    base = Base()
    cfg = carregar_config(base)
    if not cfg.get("verificar_cursos", True):
        print("Verificação desligada na Configuração.")
        return 0
    modelo = cfg.get("modelo_cursos", "claude-haiku-5-5")
    locais = {l["id"] for l in cfg["cursos"]["locais"]}
    hoje_txt = hoje_iso()

    piloto = cfg.get("territorio_piloto", "")
    pais_piloto = "BR" if piloto.startswith("BR") else "PT" if piloto == "PT" else ""
    candidatos = [r for r in base.tabela(ABA)
                  if (visivel(r.get("Estado"), cfg) or r.get("Estado") == "Rever")
                  and r.get("Local") in locais and r.get("Link")
                  and (r.get("Verificar automaticamente", "") == "" or sim(r.get("Verificar automaticamente")))
                  # durante um piloto, os cursos online de outros países não aparecem no site: não gastar com eles
                  and not (r.get("Local") == "online" and pais_piloto
                           and r.get("País") not in (pais_piloto, "Internacional", ""))]
    # primeiro os que ainda não têm passo a passo, depois os verificados há mais tempo
    candidatos.sort(key=lambda r: (bool(r.get("Como me inscrever")), r.get("Nota da verificação") != "",
                                   r.get("Última verificação") or ""))
    candidatos = candidatos[:MAX_POR_EXECUCAO]
    print(f"A verificar {len(candidatos)} cursos")

    historico = []
    alteracoes, custo_total, contagem = [], 0.0, {"aberto": 0, "encerrado": 0, "incerto": 0, "falhou": 0}
    for r in candidatos:
        try:
            pagina = texto_da_pagina(r["Link"])
        except Exception as e:  # noqa: BLE001
            contagem["falhou"] += 1
            alteracoes.append((r["_linha"], {"Nota da verificação": f"{hoje_txt}: não foi possível abrir a página ({type(e).__name__})."}))
            print(f"  ✗ {r['Título']}: página não abriu ({type(e).__name__})")
            continue
        dados = {k: r.get(k, "") for k in ("Título", "Entidade", "Local", "Cidade", "Descrição", "Requisitos",
                                            "Inscrições até", "Início")}
        pedido = (f"Data de hoje: {hoje_txt}.\n\nDados do curso: {dados}\n\nLink: {r['Link']}\n\n"
                  f"Texto da página:\n{pagina}")
        try:
            texto, uso = claude(modelo, SISTEMA, pedido, max_tokens=4000)
        except ErroClaude as e:
            print(f"  ERRO no Claude: {e}")
            continue
        custo_total += custo_estimado(uso, modelo)
        res = extrair_json(texto)
        if not isinstance(res, dict):
            print(f"  ? {r['Título']}: resposta sem JSON")
            continue
        situacao = res.get("situacao") if res.get("situacao") in contagem else "incerto"
        contagem[situacao] += 1
        campos = {"Última verificação": hoje_txt, "Nota da verificação": f"{hoje_txt}: {res.get('nota') or ''}".strip(),
                  "Situação das inscrições": SITUACOES[situacao], "Próxima verificação": ""}
        passos = res.get("como_me_inscrever") or []
        if passos and not r.get("Como me inscrever"):
            campos["Como me inscrever"] = "\n".join(f"{i}. {p.strip()}" for i, p in enumerate(passos[:5], 1))
        if res.get("inscricoes_ate") and not r.get("Inscrições até"):
            campos["Inscrições até"] = str(res["inscricoes_ate"])[:10]
        if situacao == "encerrado" and r.get("Estado") in ("Novo", "Publicado"):
            campos["Estado"] = "Expirado"
        elif res.get("gratuito") == "não" and r.get("Estado") in ("Novo", "Publicado"):
            campos["Estado"] = "Rever"
            campos["Notas"] = ((r.get("Notas") or "") + " A verificação indica que pode não ser gratuito.").strip()
        alteracoes.append((r["_linha"], campos))
        if campos.get("Situação das inscrições") != r.get("Situação das inscrições") or "Estado" in campos:
            historico.append(registo_historico(r, "Claude", situacao, campos, res.get("nota") or ""))
        marca = {"aberto": "✓", "encerrado": "⨯", "incerto": "?"}[situacao]
        print(f"  {marca} {r['Título']}: {res.get('nota')}")

    base.atualizar(ABA, alteracoes)
    if HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nResumo: {contagem} | custo estimado: {round(custo_total, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
