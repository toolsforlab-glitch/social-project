"""Rotina diária de notícias: lê os feeds, o Claude escolhe as mais relevantes e resume-as em português."""
import calendar
import datetime
import hashlib
import html
import os
import re
import sys

import feedparser

from base import Base, carregar_config
from comum import (ErroClaude, agora_utc, baixar, claude, custo_estimado, extrair_json, gravar_json, hoje,
                   ler_json)

ESTADO = "estado/noticias-vistas.json"
MAX_CANDIDATOS = 120
MAX_POR_FONTE = 15

SISTEMA = """És o editor de notícias de um site em português que liga pessoas a informação e oportunidades \
no setor social. Os leitores são sobretudo pessoas que trabalham ou fazem voluntariado em ONGs, associações \
e fundações no Brasil.

Escolhe APENAS notícias sobre o Brasil: factos que acontecem no Brasil ou que dizem diretamente respeito a pessoas \
ou organizações no Brasil. Uma notícia internacional só entra se o texto disser qual é o efeito no Brasil. Se \
nenhuma candidata for sobre o Brasil, devolve uma lista vazia.

Escolhe as notícias mais úteis e relevantes sobre: ajuda humanitária, pobreza e desenvolvimento, filantropia \
e financiamento, gestão de ONGs, direitos humanos, educação, saúde global, clima com impacto social, \
migrações e refugiados.

Regras:
- Dá prioridade a factos novos e com impacto (decisões, dados, crises, financiamento, políticas, estudos).
- Se a mesma história aparece em várias fontes, escolhe só uma.
- Evita publicidade, angariações de fundos de uma só organização, eventos sem interesse geral e textos sem informação.
- Equilibra os temas e as regiões do Brasil.
- Evita notícias locais de interesse restrito (uma cidade, um condado ou uma organização pequena nos EUA ou noutro país), \
exceto quando têm relevância nacional ou ensinam algo útil a qualquer ONG.
- Escreve em português do Brasil, simples e claro.
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
    base = Base()
    cfg_total = carregar_config(base)
    cfg = cfg_total["noticias"]
    registos = base.tabela("Notícias")
    estado = ler_json(ESTADO, {"vistas": []})
    vistos = set(estado["vistas"]) | {r.get("Link", "") for r in registos}

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
    corte_recentes = (hoje() - datetime.timedelta(days=3)).isoformat()
    recentes = [r["Título"] for r in registos if r.get("Data", "") >= corte_recentes]
    ja_publicadas = ("Já publicadas nos últimos dias (não repitas a mesma história, mesmo vinda de outra fonte):\n"
                     + "\n".join(f"- {t}" for t in recentes) + "\n\n") if recentes else ""
    pedido = (
        f"Data de hoje: {hoje().isoformat()}.\n\n{ja_publicadas}Notícias candidatas:\n\n{lista}\n\n"
        f"Escolhe até {cfg['max_por_dia']} notícias sobre o Brasil (menos, ou nenhuma, se não houver candidatas relevantes). "
        f"Temas possíveis: {', '.join(temas)}.\n"
        "Não expliques a escolha. Responde só com JSON entre <json></json>, uma lista na ordem de importância, assim:\n"
        '<json>[{"id": "...", "titulo": "título em português", "resumo": "1-2 frases", '
        '"tema": "um dos temas", "regiao": "Brasil"}]</json>')
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
    novas = []
    dia = hoje().isoformat()
    for s in escolhidas:
        c = por_id.get(str(s.get("id")))
        if not c or not s.get("titulo") or not s.get("resumo") or s.get("tema") not in temas:
            continue
        if (s.get("regiao") or "").strip() != "Brasil":
            continue  # o site só mostra notícias do Brasil
        novas.append({
            "ID": "N-" + hashlib.sha1(c["link"].encode()).hexdigest()[:8], "Estado": "Publicado", "Data": dia,
            "Título": s["titulo"].strip(), "Resumo": s["resumo"].strip(), "Tema": s["tema"],
            "Região": s.get("regiao") or "", "Fonte": c["fonte"], "Idioma original": c["idioma"],
            "Link": c["link"], "Notas": "",
        })
    print(f"Escolhidas: {len(novas)}  |  custo estimado: {custo_estimado(uso, modelo)} USD")
    for n in novas:
        print(f"  • [{n['Tema']}] {n['Título']} ({n['Fonte']})")
    base.acrescentar("Notícias", novas)
    base.guardar()

    estado["vistas"] = (estado["vistas"] + [c["link"] for c in candidatos])[-4000:]
    gravar_json(ESTADO, estado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
