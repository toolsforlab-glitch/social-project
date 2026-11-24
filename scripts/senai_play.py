"""Cursos gratuitos on-line do SENAI Play (play.senai.br), com prova por código.

RETIRADO a 24/11/2026: o certificado do SENAI Play é sempre pago («taxa simbólica», de R$ 14,90 a R$ 247,00), e o
responsável decidiu que curso com certificado pago não entra no site («Ou é grátis ou não é»). Este leitor saiu das
rotinas e os cursos foram ocultados na folha. Fica guardado só para consulta.

Decisões do responsável (24/11/2026): «certificado pago entra, desde que tenha a distinção entre certificado pago e
gratuito» e «tem que colocar o valor do certificado». Entram só os cursos com 16 horas ou mais (sobretudo os
minicursos, que juntam vários microcursos); os cerca de 900 microcursos curtos ficam de fora para não encherem o site.

A plataforma tem uma API pública (a mesma que o site usa). Para cada curso, ela dá a carga horária, a descrição e o
preço do certificado («certificatePrice»), que é o mesmo do Futuro.Digital, o marketplace oficial do SENAI (conferido
no navegador a 24/11/2026: SKU 7641, R$ 14,70 nos dois). O código confere, em cada leitura, a frase oficial da Agência
de Notícias da Indústria (CNI/SENAI): «todos os cursos são 100% online e gratuitos. E, para quem quiser turbinar o
currículo, é possível emitir um certificado do curso por uma taxa simbólica.»

O Claude só escolhe quais cursos servem ao público do site e as necessidades de cada um. Os escolhidos são publicados
sozinhos, com «Certificado pago» e o valor; um curso sem preço na API fica com o certificado por confirmar. Um curso que
sai da plataforma (ou é marcado obsoleto) passa a «Encerrado». A verificação semanal não toca nestes cursos.
"""
import hashlib
import json
import re
import sys

from base import (registar_pendencia, DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config,
                  citacao_valida, exige_prova, hoje_iso, registo_historico, texto_de_html)
from comum import baixar, claude, custo_estimado, extrair_json

SITE = "https://play.senai.br"
GRAPHQL = SITE + "/student-api/graphql"
ENTIDADE = "SENAI Play (SENAI Nacional)"
HORAS_MINIMAS = 16
MARCA = "lida na API oficial do SENAI Play, conferida por código"
NOTICIA = ("https://noticias.portaldaindustria.com.br/noticias/educacao/"
           "parabens-senai-play-cinco-anos-inovando-na-educacao-profissional-do-brasil/")
FRASE_GRATUITO = "todos os cursos são 100% online e gratuitos"
FRASE_CERTIFICADO = "é possível emitir um certificado do curso por uma taxa simbólica"
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe cursos do \
SENAI Play (on-line, gratuitos, de 16 horas ou mais). Escolha os que servem a qualquer pessoa que quer aprender uma \
profissão, melhorar no trabalho ou abrir um negócio (deixe de fora os pensados só para engenheiros, gestores de \
empresas ou profissionais de áreas industriais muito específicas). Para cada escolhido, indique as necessidades (ids \
da lista dada). Responda só com JSON entre <json></json>: [{"n": número do curso na lista, "necessidades": ["id", ...]}]."""

Q_LISTA = """query CoursesWithCategories($options: FindOptionsInput = {}) { CoursesWithCategories(options: $options) {
 items { id name workload courseCategory { description } } pageInfo { nextPage totalItems } } }"""
Q_CURSO = """query Course($id: ID!) { course(id: $id) { id name description workload published obsoleteAt
 certificatePrice courseCategory { description } } }"""


def gql(query, variables):
    corpo = json.dumps({"query": query, "variables": variables}).encode()
    dados = json.loads(baixar_post(GRAPHQL, corpo).decode("utf-8", "replace"))
    if dados.get("errors"):
        raise RuntimeError(dados["errors"][0].get("message", "erro na API"))
    return dados["data"]


def baixar_post(url, corpo):
    import urllib.request
    req = urllib.request.Request(url, data=corpo, headers={"Content-Type": "application/json",
                                                           "User-Agent": "Mozilla/5.0 (projeto social; catálogo público)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def catalogo():
    itens, vistos = [], set()
    for n_tipo, tipo in enumerate(("Aulas em Vídeos", "Aulas pelo WhatsApp", "Aulas em Podcast")):
        for pagina in range(1, 60):
            try:
                d = gql(Q_LISTA, {"options": {"filters": {"type": tipo}, "paginate": {"page": pagina, "offset": 100},
                                          "orderBy": {"set": "name", "order": "ASC"}}})["CoursesWithCategories"]
            except RuntimeError:
                if n_tipo == 0:
                    raise
                break  # tipo de aula sem lista própria (só o de vídeos é obrigatório)
            for i in d["items"]:
                if i["id"] not in vistos:
                    vistos.add(i["id"])
                    itens.append(i)
            if not d["pageInfo"].get("nextPage"):
                break
    return itens


def valor_br(preco):
    return "R$ " + f"{preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def detalhe(cid):
    c = gql(Q_CURSO, {"id": cid})["course"]
    texto = texto_de_html((c.get("description") or "").encode())
    frases = [f for f in re.split(r"(?<=[.!?])\s+", texto) if len(f) > 20]
    preco = c.get("certificatePrice")
    return {"id": cid, "url": f"{SITE}/curso/{cid}", "titulo": (c.get("name") or "").strip(), "horas": c.get("workload") or 0,
            "categoria": (c.get("courseCategory") or {}).get("description", ""), "descricao": " ".join(frases[:2])[:500],
            "ativo": bool(c.get("published")) and not c.get("obsoleteAt"),
            "preco": float(preco) if isinstance(preco, (int, float)) and preco > 0 else None,
            "prova": exige_prova(texto)}


def provas(d):
    ev = [f"gratuito: «{FRASE_GRATUITO}» ({NOTICIA}; Agência de Notícias da Indústria, conferida por código)",
          f"situação: curso publicado e não obsoleto na plataforma ({d['url']}; {MARCA}; curso sob demanda)"]
    comp = ["gratuito", "situação"]
    if d["preco"]:
        ev.append(f"certificado: «{FRASE_CERTIFICADO}» ({NOTICIA})")
        ev.append(f"valor do certificado: «{valor_br(d['preco'])}» (preço do certificado na API oficial do SENAI Play, "
                  f"igual ao do Futuro.Digital; {MARCA})")
        comp.append("certificado")
    return " | ".join(ev)[:1500], comp


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    try:
        noticia = texto_de_html(baixar(NOTICIA, timeout=40))
        frases_ok = citacao_valida(FRASE_GRATUITO, noticia) and citacao_valida(FRASE_CERTIFICADO, noticia)
        itens = catalogo()
    except Exception as e:  # noqa: BLE001
        print(f"  ! SENAI Play: {e}")
        registar_pendencia(base, "SENAI Play: a API oficial ou a notícia da gratuidade não abriu.",
                           "Se o SENAI Play abre no seu navegador.", SITE, origem="senai_play.py")
        base.guardar()
        return 0
    print(f"SENAI Play: {len(itens)} cursos na plataforma; frases da gratuidade e do certificado "
          f"{'conferidas' if frases_ok else 'NÃO conferidas'}.")
    if not frases_ok:
        registar_pendencia(base, "SENAI Play: a frase oficial da gratuidade mudou ou saiu da notícia; nada publicado.",
                           "Se os cursos continuam gratuitos e qual é a regra do certificado.", NOTICIA,
                           origem="senai_play.py")
        base.guardar()
        return 0
    longos = {i["id"]: i for i in itens if (i.get("workload") or 0) >= HORAS_MINIMAS}
    linhas = base.tabela("Cursos")
    por_id = {}
    for r in linhas:
        m = re.search(r"play\.senai\.br/curso/([0-9a-f-]{20,})", r.get("Link", "") or "")
        if m:
            por_id[m.group(1)] = r
    alteracoes, historico = [], []
    todos_ids = {i["id"] for i in itens}
    for cid, r in por_id.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        situacao = "Aberto" if cid in todos_ids else "Encerrado"
        if situacao != r.get("Situação das inscrições"):
            alteracoes.append((r["_linha"], {"Situação das inscrições": situacao, "Última verificação": hoje}))
            print(f"  = {r['Título'][:60]} | {situacao}")
    novos_lidos = []
    for cid in longos:
        if cid in por_id:
            continue
        try:
            d = detalhe(cid)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {cid}: {e}")
            continue
        if d["titulo"] and d["ativo"] and not d["prova"]:
            novos_lidos.append(d)
    novos, custo = [], 0.0
    if novos_lidos:
        lista = "\n".join(f"{i} | {d['titulo'][:120]} | {d['categoria']} | {d['horas']}h | {d['descricao'][:200]}"
                          for i, d in enumerate(novos_lidos, 1))
        texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                            f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nCursos (número | título | tipo | horas | "
                            f"descrição):\n{lista}", max_tokens=6000)
        custo += custo_estimado(uso, cfg["modelo_cursos"])
        escolha = {}
        for x in (extrair_json(texto) or []):
            if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(novos_lidos):
                escolha[novos_lidos[int(x["n"]) - 1]["id"]] = x
        print(f"Cursos novos do SENAI Play com {HORAS_MINIMAS} h ou mais: {len(novos_lidos)}; o Claude escolheu {len(escolha)}.")
        nota = (f"{hoje}: publicado automaticamente: curso do SENAI Play (on-line, gratuito pela frase oficial da "
                f"Agência de Notícias da Indústria, conferida por código); certificado pago com o valor da API oficial.")
        for d in novos_lidos:
            x = escolha.get(d["id"])
            if not x:
                continue
            evid, comp = provas(d)
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            linha = {
                "ID": "C-" + hashlib.sha1(f"senaiplay|{d['id']}".encode()).hexdigest()[:8],
                "Estado": "Publicado", "Título": d["titulo"][:200], "Entidade": ENTIDADE, "Link": d["url"],
                "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": d["descricao"], "Origem da descrição": DESCRICAO_PAGINA if d["descricao"] else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "", "Requisitos": "",
                "Certificado": "pago" if d["preco"] else "desconhecido", "Inscrições até": "", "Início": "",
                "Duração": f"{d['horas']} horas", "Link verificado": "SIM", "Primeiro visto": hoje,
                "Última verificação": hoje, "Origem": "senai_play",
                "Notas": (f"Curso gratuito; certificado opcional por {valor_br(d['preco'])}." if d["preco"]
                          else "Curso gratuito; a API não diz o preço do certificado."),
                "Como me inscrever": ("1. Abra a página do curso no SENAI Play.\n"
                                      "2. Clique em \"Inscreva-se\" e faça o cadastro gratuito.\n"
                                      "3. Estude no seu ritmo, pelo computador ou pelo celular.\n"
                                      + ("4. Se quiser o certificado, pague o valor indicado no fim do curso." if d["preco"]
                                         else "4. No fim, veja na plataforma como pedir o certificado.")),
                **VERIFICACAO_INICIAL, "Nota da verificação": nota,
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": ", ".join(comp), "Página do curso": d["url"]}
            novos.append(linha)
            historico.append(registo_historico(linha, "Catálogo SENAI Play", "Publicado", linha, d["url"]))
            print(f"  + {d['titulo'][:55]} | {d['horas']}h | {valor_br(d['preco']) if d['preco'] else 'sem preço'}")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"SENAI Play: {len(alteracoes)} cursos atualizados, {len(novos)} novos publicados. Custo estimado: {custo:.3f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
