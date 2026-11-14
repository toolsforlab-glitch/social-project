"""Verificação semanal: o Claude relê a página de cada curso visível, confirma se continua aberto e gratuito
e escreve o passo a passo de inscrição em linguagem simples."""
import html
import os
import re
import sys

from base import texto_de_html, CAMPOS_PROVA, HISTORICO, SITUACOES, Base, citacao_valida, carregar_config, hoje_iso, registo_historico, sim, visivel
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json

ABA = "Cursos"
MAX_POR_EXECUCAO = int(os.environ.get("MAX_VERIFICACOES", "60"))
MAX_CARACTERES = 12000

SISTEMA = """Verificas cursos gratuitos para um site público lido por pessoas com pouca escolaridade e \
poucos recursos. Uma informação errada pode fazer alguém perder tempo e dinheiro. Recebes os dados que temos \
sobre um curso e o texto da página oficial.

REGRA PRINCIPAL: usa só o que a página diz explicitamente. Se a página não diz, a resposta é null ou "incerto". \
Nunca deduzas, nunca completes com o que é habitual e nunca uses conhecimento geral. Exemplos do que NÃO fazer: \
transformar "etapas até 22/12" em "inscrições até 22/12"; concluir que é gratuito porque a entidade costuma \
ter cursos gratuitos; usar a data de início das aulas como data limite de inscrição.

Para cada afirmação importante tens de copiar, em "evidencias", a frase EXATA da página que a prova \
(copiada letra a letra, até 25 palavras). Sem frase exata, a afirmação não vale e o campo fica null/"incerto".

Devolve JSON entre <json></json> com:
- "situacao": "aberto" (a página diz que as inscrições estão abertas, que o acesso é livre, ou indica uma turma \
futura com inscrição), "encerrado" (a página diz que as inscrições terminaram ou o curso acabou) ou "incerto" \
(tudo o resto, incluindo quando o curso não aparece na página).
- "gratuito": "sim" ou "não" só se a página o disser para ESTE curso; senão "incerto".
- "inscricoes_ate": data AAAA-MM-DD só se a página indicar a data limite de INSCRIÇÃO; senão null.
- "restricoes": quem pode entrar (idade, renda, escolaridade, morada, já ser estudante…), só se a página o \
disser; senão null.
- "evidencias": objeto com as frases exatas para "situacao", "gratuito", "inscricoes_ate" e "restricoes" \
(null quando não houver).
- "em_falta": lista curta, em linguagem simples, do que a página não esclarece e a pessoa tem de confirmar \
(ex.: "Não diz até quando são as inscrições").
- "como_me_inscrever": 3 a 5 passos curtos, em linguagem muito simples, só com o que a página explica (onde ir, \
que documentos levar, até quando). Se a página não explicar como se inscrever, devolve um único passo: \
"A página não explica como se inscrever: contacte a entidade." seguido do contacto, se a página o tiver. \
Para cursos no Brasil escreve em português do Brasil; em Portugal, em português de Portugal.
- "nota": uma frase curta a explicar o que verificaste."""


def texto_da_pagina(url):
    return texto_de_html(baixar(url, timeout=30))[:MAX_CARACTERES]


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
                  if (visivel(r.get("Estado"), cfg) or r.get("Estado") in ("Novo", "Rever"))
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
        ev = res.get("evidencias") if isinstance(res.get("evidencias"), dict) else {}
        provas, rejeitadas = {}, []
        for chave in CAMPOS_PROVA:
            frase = ev.get(chave)
            if frase and citacao_valida(str(frase), pagina):
                provas[chave] = str(frase).strip()
            elif frase:
                rejeitadas.append(CAMPOS_PROVA[chave])
        em_falta = [str(x).strip() for x in (res.get("em_falta") or []) if str(x).strip()]

        # Sem prova não há afirmação
        situacao = res.get("situacao") if res.get("situacao") in ("aberto", "encerrado") else "incerto"
        if situacao != "incerto" and "situacao" not in provas:
            situacao = "incerto"
        gratuito = res.get("gratuito") if "gratuito" in provas else "incerto"
        data = str(res.get("inscricoes_ate") or "")[:10] if "inscricoes_ate" in provas else ""
        contagem[situacao] += 1

        campos = {"Última verificação": hoje_txt, "Nota da verificação": f"{hoje_txt}: {res.get('nota') or ''}".strip(),
                  "Próxima verificação": "",
                  "Evidência": " | ".join(f"{CAMPOS_PROVA[k]}: «{v}»" for k, v in provas.items()),
                  "Campos comprovados": ", ".join(CAMPOS_PROVA[k] for k in provas)}
        motivos = []
        if rejeitadas:
            motivos.append("O Claude afirmou " + ", ".join(rejeitadas) + " sem frase da página que o prove (ignorado).")
        revisto = bool((r.get("Revisto por pessoa") or "").strip())
        nova_situacao = SITUACOES[situacao]
        passos = res.get("como_me_inscrever") or []

        if revisto:
            # Curso confirmado por uma pessoa: a rotina não altera os campos importantes, só avisa.
            if nova_situacao != (r.get("Situação das inscrições") or "") and situacao != "incerto":
                motivos.append(f"Revisto por pessoa, mas a página agora indica: {nova_situacao}.")
            if gratuito == "não":
                motivos.append("Revisto por pessoa, mas a página indica que pode não ser gratuito.")
        else:
            campos["Situação das inscrições"] = nova_situacao
            if passos and not r.get("Como me inscrever"):
                campos["Como me inscrever"] = "\n".join(f"{i}. {p.strip()}" for i, p in enumerate(passos[:5], 1))
            if data and not r.get("Inscrições até"):
                campos["Inscrições até"] = data
            elif r.get("Inscrições até") and "inscricoes_ate" not in provas:
                motivos.append(f"A data {r['Inscrições até']} não está confirmada na página.")
            if situacao == "encerrado" and r.get("Estado") in ("Novo", "Publicado"):
                campos["Estado"] = "Expirado"
                motivos.append("A página diz que as inscrições terminaram: passou a Expirado.")
            elif gratuito == "não" and r.get("Estado") in ("Novo", "Publicado"):
                campos["Estado"] = "Rever"
                motivos.append("A página indica que pode não ser gratuito: passou a Rever.")
            if r.get("Situação das inscrições") == "Aberto" and situacao == "incerto":
                motivos.append("Estava Aberto e a página já não o confirma.")
        if gratuito == "incerto":
            em_falta.append("A página não diz se este curso é gratuito.")
        if motivos:
            campos["Mudança a rever"] = "TRUE"
        frases = [f if f.endswith((".", "!", "?")) else f + "." for f in motivos + em_falta]
        campos["O que falta confirmar"] = " ".join(dict.fromkeys(frases))[:900]
        alteracoes.append((r["_linha"], campos))
        if (campos.get("Situação das inscrições", r.get("Situação das inscrições")) != r.get("Situação das inscrições")
                or "Estado" in campos or motivos):
            historico.append(registo_historico(r, "Claude", situacao, campos, " ".join(motivos) or res.get("nota") or ""))
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
