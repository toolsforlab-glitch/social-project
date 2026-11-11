"""Rotina diária de notícias: lê os feeds, o Claude escolhe as mais relevantes e resume-as em português."""
import calendar
import datetime
import hashlib
import html
import os
import re
import sys

import feedparser

from comum import (ErroClaude, agora_utc, baixar, claude, config, custo_estimado, extrair_json,
                   gravar_json, hoje, ler_json)

FICHEIRO = "docs/dados/noticias.json"
ESTADO = "estado/noticias-vistas.json"
MAX_CANDIDATOS = 120
MAX_POR_FONTE = 15

SISTEMA = """És o editor de notícias de um site em português que liga pessoas a informação e oportunidades \
no setor social. Os leitores são sobretudo pessoas que trabalham ou fazem voluntariado em ONGs, associações \
e fundações, em Portugal, no Brasil e noutros países de língua portuguesa.

Escolhe as notícias mais úteis e relevantes sobre: ajuda humanitária, pobreza e desenvolvimento, filantropia \
e financiamento, gestão de ONGs, direitos humanos, educação, saúde global, clima com impacto social, \
migrações e refugiados.

Regras:
- Dá prioridade a factos novos e com impacto (decisões, dados, crises, financiamento, políticas, estudos).
- Se a mesma história aparece em várias fontes, escolhe só uma.
- Evita publicidade, angariações de fundos de uma só organização, eventos sem interesse geral e textos sem informação.
- Equilibra temas e regiões; inclui pelo menos uma notícia de Portugal ou do Brasil quando houver boas candidatas.
- Escreve em português neutro, compreensível em Portugal e no Brasil, sem regionalismos.
- O título e o resumo são escritos por ti, com as tuas palavras: não copies frases do original. \
O resumo tem 1 ou 2 frases curtas e diz o essencial. Não acrescentes factos que não estejam no texto dado.
- Sem pormenores gráficos de violência."""


def limpar(texto, limite):
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(re.sub(r"\s+", " ", texto)).strip()
    return texto[:limite]


def data_entrada(e):
    for campo in ("published_parsed", "updated_parsed"):
        t = e.get(campo)
        if t:
            return datetime.datetime.fromtimestamp(calendar.timegm(t), datetime.timezone.utc)
    return None


def recolher(cfg, vistos):
    limite = agora_utc() - datetime.timedelta(hours=cfg.get("horas_janela", 36))
    candidatos, relatorio = [], []
    for fonte in cfg["fontes"]:
        try:
            feed = feedparser.parse(baixar(fonte["url"]))
        except Exception as e:  # noqa: BLE001
            relatorio.append(f"  ✗ {fonte['nome']}: não foi possível ler ({type(e).__name__}: {e})")
            continue
        if feed.bozo and not feed.entries:
            relatorio.append(f"  ✗ {fonte['nome']}: feed inválido ({feed.bozo_exception})")
            continue
        n = 0
        for e in feed.entries:
            link = (e.get("link") or "").strip()
            if not link or link in vistos:
                continue
            quando = data_entrada(e)
            if quando and quando < limite:
                continue
            nome_fonte = fonte["nome"]
            src = e.get("source")
            if src and getattr(src, "get", None) and src.get("title"):
                nome_fonte = src.get("title")
            candidatos.append({
                "id": hashlib.sha1(link.encode()).hexdigest()[:10],
                "fonte": nome_fonte, "idioma": fonte.get("idioma", "en"),
                "titulo": limpar(e.get("title"), 300),
                "resumo": limpar(e.get("summary") or e.get("description"), 500),
                "link": link, "data": quando.isoformat() if quando else None,
            })
            n += 1
            if n >= MAX_POR_FONTE:
                break
        relatorio.append(f"  ✓ {fonte['nome']}: {len(feed.entries)} no feed, {n} novas")
    return candidatos, relatorio


def main():
    cfg_total = config()
    cfg = cfg_total["noticias"]
    dados = ler_json(FICHEIRO, {"atualizado": None, "dias": []})
    estado = ler_json(ESTADO, {"vistas": []})
    vistos = set(estado["vistas"]) | {it["link"] for d in dados["dias"] for it in d["itens"]}

    candidatos, relatorio = recolher(cfg, vistos)
    print("Fontes:")
    print("\n".join(relatorio))
    print(f"Candidatas novas: {len(candidatos)}")
    if not candidatos:
        print("Nada de novo hoje.")
        return 0

    candidatos.sort(key=lambda c: c["data"] or "", reverse=True)
    candidatos = candidatos[:MAX_CANDIDATOS]
    temas = cfg["temas"]
    lista = "\n\n".join(
        f"[{c['id']}] ({c['fonte']}, {c['idioma']}) {c['titulo']}\n{c['resumo']}" for c in candidatos)
    pedido = (
        f"Data de hoje: {hoje().isoformat()}.\n\nNotícias candidatas:\n\n{lista}\n\n"
        f"Escolhe entre 5 e {cfg['max_por_dia']} notícias (menos só se não houver mais candidatas relevantes). "
        f"Temas possíveis: {', '.join(temas)}.\n"
        "Não expliques a escolha. Responde só com JSON entre <json></json>, uma lista na ordem de importância, assim:\n"
        '<json>[{"id": "...", "titulo": "título em português", "resumo": "1-2 frases", '
        '"tema": "um dos temas", "regiao": "Mundo, Portugal, Brasil, África, Europa, Américas, Ásia ou Médio Oriente"}]</json>')
    modelo = cfg_total.get("modelo_noticias", "claude-haiku-5-5")
    try:
        texto, uso = claude(modelo, SISTEMA, pedido, max_tokens=12000)
    except ErroClaude as e:
        print(f"ERRO: {e}")
        return 1
    escolhidas = extrair_json(texto) or []
    if not escolhidas:
        print(f"  Resposta sem lista válida. Início: {texto[:500]!r}")
    por_id = {c["id"]: c for c in candidatos}
    itens = []
    for s in escolhidas:
        c = por_id.get(str(s.get("id")))
        if not c or not s.get("titulo") or not s.get("resumo"):
            continue
        itens.append({
            "titulo": s["titulo"].strip(), "resumo": s["resumo"].strip(),
            "tema": s.get("tema") if s.get("tema") in temas else None,
            "regiao": s.get("regiao"), "fonte": c["fonte"], "idioma_original": c["idioma"],
            "link": c["link"], "data": c["data"],
        })
    print(f"Escolhidas: {len(itens)}  |  custo estimado: {custo_estimado(uso, modelo)} USD")
    for it in itens:
        print(f"  • [{it['tema']}] {it['titulo']} ({it['fonte']})")

    dia = hoje().isoformat()
    if dados["dias"] and dados["dias"][0]["data"] == dia:
        ja = {i["link"] for i in dados["dias"][0]["itens"]}
        dados["dias"][0]["itens"].extend(i for i in itens if i["link"] not in ja)
    elif itens:
        dados["dias"].insert(0, {"data": dia, "itens": itens})
    corte = (hoje() - datetime.timedelta(days=cfg.get("dias_guardados", 30))).isoformat()
    dados["dias"] = [d for d in dados["dias"] if d["data"] >= corte]
    dados["atualizado"] = agora_utc().isoformat(timespec="minutes")
    gravar_json(FICHEIRO, dados)

    estado["vistas"] = (estado["vistas"] + [c["link"] for c in candidatos])[-4000:]
    gravar_json(ESTADO, estado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
