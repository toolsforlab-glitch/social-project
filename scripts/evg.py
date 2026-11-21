"""Cursos on-line da Escola Virtual de Governo (EV.G), lidos da API pública oficial (api-evg.enap.gov.br), sem páginas.

As páginas da EV.G são montadas no navegador (a verificação semanal só recebe o cabeçalho), mas o site usa uma API
pública que os servidores do GitHub conseguem ler. Tudo é lido e conferido por código:

- situação e prazo: campo «inscricoes_abertas» do curso e a oferta (turma) em curso, com as datas de inscrição
  («dt_inicio_inscricao» a «dt_termino_inscricao»);
- gratuidade e certificado: frases das Perguntas frequentes oficiais da EV.G (servidas pela mesma API), conferidas
  letra a letra em cada leitura;
- para quem é: o «público-alvo» da oferta tem de dizer que qualquer cidadão (ou pessoa) pode fazer o curso; cursos só
  para servidores públicos ficam de fora.

O que faz:
1. atualiza os cursos da EV.G que já estão na folha (link ou «Página do curso» da EV.G): situação, prazo,
   gratuidade, certificado e página própria do curso; inscrições encerradas → «Encerrado» (sai do site);
2. procura cursos novos no catálogo (cerca de 900): primeiro um filtro por código (em português, ativos, temas e
   palavras ligados ao que o site serve), depois o Claude escolhe os úteis para quem procura qualificação, emprego,
   gestão do dinheiro ou direitos (não os pensados para servidores públicos), e por fim o código confere tudo na API.
   Os que passam em todas as provas são publicados sozinhos (no máximo MAX_NOVOS por ronda); os outros ficam em Novo.
Cursos com «Revisto por pessoa» ou Estado = Oculto nunca são alterados.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

from base import (DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida,
                  hoje_iso, registo_historico, sim)
from comum import claude, custo_estimado, extrair_json

API = "https://api-evg.enap.gov.br/v1"
URL_FAQ = API + "/busca?resource_type=ajuda&limit=100"
PAGINA = "https://www.escolavirtual.gov.br/cursos/{slug}"
ENTIDADE = "Escola Virtual de Governo (EV.G)"
FRASE_GRATUITO = "Todos os cursos online da Escola Virtual.Gov (EV.G) são gratuitos, com emissão de certificados gratuitamente."
FRASE_CERTIFICADO = "A certificação e a emissão do certificado também são gratuitas."
FAQ_LINK = "https://www.escolavirtual.gov.br/faq"
MARCA = "lida na API oficial da EV.G, conferida por código"
MAX_NOVOS = int(os.environ.get("EVG_MAX_NOVOS", "15"))
PUBLICO_ABERTO = re.compile(r"qualquer\s+(cidad[ãa]o|pessoa)|cidad[ãa]os?\s+(em\s+geral|interessad)|"
                            r"p[úu]blico\s+em\s+geral|sociedade\s+em\s+geral|toda\s+a\s+sociedade|aberto\s+a\s+todos", re.I)
# temas da EV.G ligados ao que o site serve (os outros são, quase sempre, de gestão pública)
TEMAS = {42, 43, 50, 51, 57, 58, 60, 65, 11, 12, 2, 16, 22}
PALAVRAS = re.compile(r"finan|dinheiro|or[çc]amento\s+(pessoal|familiar|dom)|empreend|neg[óo]cio|emprego|trabalh|carreira|"
                      r"curr[íi]culo|computador|digital|internet|excel|planilha|word|office|inform[áa]tica|"
                      r"intelig[êe]ncia\s+artificial|\bIA\b|libras|acessib|defici[êe]n|idos|mulher|g[êe]nero|viol[êe]ncia|"
                      r"direitos|cidadania|consumidor|golpe|seguran[çc]a\s+(digital|da\s+informa)|comunica[çc][ãa]o|"
                      r"ingl[êe]s|espanhol|portugu[êe]s|reda[çc][ãa]o|escrita|sa[úu]de\s+mental|primeiros\s+socorros|"
                      r"migra|refugi|racis|LGBT|diversidade|inclus[ãa]o", re.I)
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]

SISTEMA = """Escolhes cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no Brasil a \
encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebes cursos da Escola \
Virtual de Governo. Escolhe só os que servem a qualquer cidadão (não os pensados para servidores públicos, gestão \
pública, compras públicas, legislação de órgãos, etc.) e que ajudem de forma prática. Para cada escolhido, indica as \
necessidades (ids da lista dada) e uma razão curta. Responde só com JSON entre <json></json>: \
[{"id": número, "necessidades": ["id", ...], "razao": "…"}]. Lista vazia se nenhum servir."""


def obter(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto social; leitura da API pública)",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def catalogo():
    cursos, pagina = [], 1
    while pagina <= 20:
        j = obter(f"{API}/busca?resource_type=curso&limit=100&page={pagina}&sort=title&order=asc")
        dados = j.get("data") or []
        cursos += [d.get("attributes") or {} for d in dados]
        if len(dados) < 100:
            break
        pagina += 1
    return cursos


def sem_html(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()


def oferta_atual(det, hoje):
    """A oferta (turma) com inscrições abertas hoje, pelas datas da própria API."""
    atuais = [o for o in det.get("ofertas") or []
              if (o.get("dt_inicio_inscricao") or "9999") <= hoje <= (o.get("dt_termino_inscricao") or "0000")
              and (o.get("tp_situacao_oferta") or "").strip() in ("CONFIRMADA", "")]
    return max(atuais, key=lambda o: o.get("dt_termino_inscricao") or "") if atuais else None


def provas(det, hoje, faq):
    """Lê e confere por código. Devolve dict com situação, prazo, público, evidências e campos comprovados."""
    slug = det.get("tx_slug") or ""
    link_api = f"{API}/cursos/slug/{slug}"
    of = oferta_atual(det, hoje)
    aberto = bool(det.get("inscricoes_abertas")) and of is not None
    publico = sem_html((of or {}).get("tx_publico_alvo") or "")
    ev, comp = [], []
    if aberto:
        ev.append(f"situação: «inscricoes_abertas: true; {of.get('tx_nome_oferta', 'oferta')}: inscrições de "
                  f"{of['dt_inicio_inscricao']} a {of['dt_termino_inscricao']}» ({link_api}; {MARCA})")
        ev.append(f"data: «dt_termino_inscricao: {of['dt_termino_inscricao']}» ({link_api}; {MARCA})")
        comp += ["situação", "data"]
    if faq["gratuito"]:
        ev.append(f"gratuito: «{FRASE_GRATUITO}» ({FAQ_LINK}; {MARCA})")
        comp.append("gratuito")
    if faq["certificado"]:
        ev.append(f"certificado: «{FRASE_CERTIFICADO}» ({FAQ_LINK}; {MARCA})")
        comp.append("certificado")
    m = PUBLICO_ABERTO.search(publico)
    if m:
        frase = next((f for f in re.split(r"(?<=[.;!?])\s+", publico) if PUBLICO_ABERTO.search(f)), publico)[:300]
        ev.append(f"público: «{frase}» ({link_api}; {MARCA})")
        comp.append("público")
    return {"aberto": aberto, "prazo": (of or {}).get("dt_termino_inscricao", ""), "publico_aberto": bool(m),
            "evidencia": " | ".join(ev)[:1500], "comprovados": comp, "slug": slug,
            "inscricoes_abertas": bool(det.get("inscricoes_abertas"))}


def id_ou_slug(link):
    m = re.search(r"escolavirtual\.gov\.br/curso/(\d+)", link or "")
    if m:
        return int(m.group(1)), ""
    m = re.search(r"escolavirtual\.gov\.br/cursos/([\w-]+)", link or "")
    return (None, m.group(1)) if m else (None, "")


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    faq_txt = json.dumps(obter(URL_FAQ), ensure_ascii=False)
    faq = {"gratuito": citacao_valida(FRASE_GRATUITO, faq_txt), "certificado": citacao_valida(FRASE_CERTIFICADO, faq_txt)}
    print(f"Perguntas frequentes da EV.G: gratuidade {'confirmada' if faq['gratuito'] else 'NÃO encontrada'}, "
          f"certificado {'confirmado' if faq['certificado'] else 'NÃO encontrado'}.")
    todos = catalogo()
    por_id = {int(c["id_curso"]): c for c in todos if str(c.get("id_curso", "")).isdigit()}
    por_slug = {c.get("tx_slug"): c for c in todos if c.get("tx_slug")}
    print(f"Catálogo da EV.G: {len(todos)} cursos.")

    linhas = base.tabela("Cursos")
    alteracoes, historico, conhecidos = [], [], set()
    # 1. cursos da EV.G já na folha
    for r in linhas:
        cid, slug = id_ou_slug((r.get("Página do curso") or "").strip() or r.get("Link", ""))
        if cid is None and not slug:
            continue
        c = por_id.get(cid) if cid is not None else por_slug.get(slug)
        if c:
            conhecidos.add(int(c["id_curso"]))
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip() or not c:
            continue
        try:
            det = obter(f"{API}/cursos/slug/{c['tx_slug']}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {r['Título']}: API não respondeu ({e})")
            continue
        p = provas(det, hoje, faq)
        comprovados = [x.strip() for x in (r.get("Campos comprovados") or "").split(",") if x.strip()]
        comprovados = [x for x in comprovados if x not in ("situação", "data", "gratuito", "certificado", "público")]
        campos = {"Página do curso": PAGINA.format(slug=p["slug"]), "Última verificação": hoje,
                  "Evidência": p["evidencia"], "Campos comprovados": ", ".join(comprovados + p["comprovados"]),
                  "Verificar automaticamente": "FALSE", "Destino do link": ""}
        nova = "Aberto" if p["aberto"] else "Encerrado" if not p["inscricoes_abertas"] else "Por confirmar"
        if nova != r.get("Situação das inscrições"):
            campos["Situação das inscrições"] = nova
            historico.append(registo_historico(r, "API da EV.G", nova, campos, f"{API}/cursos/slug/{p['slug']}"))
        campos["Inscrições até"] = p["prazo"] if p["aberto"] else ""
        if faq["certificado"]:
            campos["Certificado"] = "gratuito"
        if not (r.get("Descrição") or "").strip():  # sem descrição: a apresentação oficial do curso, tal como está
            apresentacao = " ".join(re.split(r"(?<=[.!?])\s+", sem_html(det.get("tx_apresentacao")))[:2])[:500]
            if apresentacao:
                campos["Descrição"], campos["Origem da descrição"] = apresentacao, DESCRICAO_PAGINA
        if r.get("Estado") == "Novo" and p["aberto"] and faq["gratuito"] and p["publico_aberto"] and not sim(r.get("Mudança a rever")):
            campos["Estado"] = "Publicado"
            campos["Nota da verificação"] = (f"{hoje}: publicado automaticamente: inscrições abertas, gratuidade e "
                                             "público aberto a qualquer cidadão conferidos por código na API da EV.G.")
        elif r.get("Estado") == "Novo" and p["aberto"] and not p["publico_aberto"]:
            campos["Nota da verificação"] = f"{hoje}: na API da EV.G, o público-alvo não diz que qualquer cidadão pode fazer o curso."
        print(f"  = {r['Título'][:60]} | {nova} | até {p['prazo'] or '—'} | público aberto: {p['publico_aberto']}"
              + (" | publicado" if campos.get("Estado") == "Publicado" else ""))
        alteracoes.append((r["_linha"], campos))

    # 2. cursos novos: filtro por código, escolha do Claude, provas por código
    pre = [c for c in todos if str(c.get("id_idioma")) == "1" and str(c.get("tp_visible")).lower() == "true"
           and (c.get("tp_situacao_curso") or "") == "A" and int(c.get("id_curso") or 0) not in conhecidos
           and (int(c.get("id_tematica_curso") or 0) in TEMAS or PALAVRAS.search(c.get("tx_nome_curso") or ""))
           and PALAVRAS.search((c.get("tx_nome_curso") or "") + " " + sem_html(c.get("tx_apresentacao"))[:300])]
    print(f"Candidatos novos depois do filtro por código: {len(pre)}")
    novos, custo = [], 0.0
    if pre:
        lista = "\n".join(f"{c['id_curso']} | {c['tx_nome_curso']} | {(c.get('tematica') or {}).get('tx_nome_tematica', '') if isinstance(c.get('tematica'), dict) else ''} | "
                          f"{sem_html(c.get('tx_apresentacao'))[:220]}" for c in pre[:250])
        texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                            f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nCursos (id | título | tema | apresentação):\n{lista}",
                            max_tokens=6000)
        custo += custo_estimado(uso, cfg["modelo_cursos"])
        escolha = {int(x["id"]): x for x in (extrair_json(texto) or []) if isinstance(x, dict) and str(x.get("id", "")).isdigit()}
        print(f"O Claude escolheu {len(escolha)} cursos úteis para o público do site.")
        publicados = 0
        for cid, x in escolha.items():
            c = por_id.get(cid)
            if not c:
                continue
            try:
                det = obter(f"{API}/cursos/slug/{c['tx_slug']}")
            except Exception as e:  # noqa: BLE001
                print(f"  ! {c['tx_nome_curso']}: API não respondeu ({e})")
                continue
            p = provas(det, hoje, faq)
            if not p["aberto"]:
                continue
            ok = faq["gratuito"] and p["publico_aberto"] and publicados < MAX_NOVOS
            publicados += 1 if ok else 0
            apresentacao = sem_html(det.get("tx_apresentacao"))
            descricao = " ".join(re.split(r"(?<=[.!?])\s+", apresentacao)[:2])[:500]
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            novo = {"ID": "C-" + __import__("hashlib").sha1(f"evg|{cid}".encode()).hexdigest()[:8],
                    "Estado": "Publicado" if ok else "Novo", "Título": det.get("tx_nome_curso", "")[:200],
                    "Entidade": ENTIDADE, "Link": PAGINA.format(slug=p["slug"]), "Local": "online", "Modalidade": "online",
                    "País": "BR", "Região": "", "Cidade": "", "Descrição": descricao,
                    "Origem da descrição": DESCRICAO_PAGINA if descricao else "", "Necessidades": ", ".join(nec),
                    "Perfis": "todos", "Condição de acesso": "", "Requisitos": "Criar conta na Escola Virtual de Governo",
                    "Certificado": "gratuito" if faq["certificado"] else "desconhecido", "Inscrições até": p["prazo"],
                    "Início": "", "Duração": f"{det.get('qt_carga_horaria_minima')} horas" if det.get("qt_carga_horaria_minima") else "",
                    "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "evg",
                    "Notas": f"Escolhido pelo Claude: {str(x.get('razao') or '')[:200]}", "Como me inscrever": "",
                    **VERIFICACAO_INICIAL,
                    "Nota da verificação": (f"{hoje}: publicado automaticamente: inscrições abertas, gratuidade e público "
                                            "aberto a qualquer cidadão conferidos por código na API da EV.G." if ok else
                                            f"{hoje}: curso criado a partir da API da EV.G; falta prova de que é para qualquer cidadão."),
                    "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": p["evidencia"], "Campos comprovados": ", ".join(p["comprovados"]),
                    "Página do curso": PAGINA.format(slug=p["slug"]),
                    "O que falta confirmar": "" if ok else "O público-alvo da EV.G não diz que qualquer cidadão pode fazer o curso."}
            novos.append(novo)
            print(f"  + {novo['Título'][:60]} | até {p['prazo']} | {novo['Estado']}")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"EV.G: {len(alteracoes)} cursos atualizados, {len(novos)} novos "
          f"({sum(1 for n in novos if n['Estado'] == 'Publicado')} publicados). Custo estimado: {custo:.3f} USD")


if __name__ == "__main__":
    sys.exit(main())
