"""Cursos gratuitos on-line da FGV (cursosgratuitos.fgv.br, consórcio Open Education Global), com prova por código.

Sugestão do responsável a 24/11/2026 («as universidades possuem cursos gratuitos com certificado, a FGV acredito
que tenha»). O portal tem cerca de 230 cursos autoinstrucionais, sem datas, e uma API pública (a mesma que o site
usa) que abre a partir do GitHub. O código confere, em cada leitura, nas perguntas frequentes oficiais:

- a gratuidade: «Não. Os cursos da FGV em parceria com o OEG são inteiramente gratuitos.»;
- que o curso fica disponível enquanto estiver no portfólio (curso sob demanda, sem prazo de inscrição);

e a frase da aba «Certificado» das páginas dos cursos (texto fixo do site, lido no navegador a 24/11/2026): os cursos gratuitos da FGV NÃO dão certificado, só uma
declaração de participação (impressa no sistema depois do pós-teste com nota 7 ou mais). O site mostra isso.

O Claude só escolhe quais cursos servem ao público do site (deixa de fora os pensados só para professores, gestores
ou profissionais de áreas muito específicas) e as necessidades de cada um. Os escolhidos são publicados sozinhos;
cursos já na planilha com «Mudança a rever» marcada ou «Revisto por pessoa» não mudam de Estado. Um curso que sai do
portfólio passa a «Encerrado». A verificação semanal não toca nestes cursos.
"""
import hashlib
import json
import re
import sys

from base import (NECESSIDADES, necessidades_para_claude, registar_pendencia, DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config,
                  certificado_da_frase, citacao_valida, exige_prova, hoje_iso, registo_historico, sim, texto_de_html)
from comum import baixar, claude, custo_estimado, extrair_json

SITE = "https://cursosgratuitos.fgv.br"
API = "https://cursosgratuitosapi.fgv.br/api/services/app"
ENTIDADE = "FGV (Cursos gratuitos, Open Education Global)"
MARCA = "lida na API oficial do portal, conferida por código"
FAQ = SITE + "/duvidas-frequentes"
FRASE_GRATUITO = "Os cursos da FGV em parceria com o OEG são inteiramente gratuitos."
FRASE_DISPONIVEL = "O curso ficará disponível enquanto estiver ativo no portfólio de cursos gratuitos da FGV"
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe cursos \
gratuitos e autoinstrucionais da FGV (curtos, de 1 a 30 horas). Escolha os que servem a qualquer pessoa que quer \
aprender, voltar a estudar ou trabalhar (deixe de fora os pensados só para professores, gestores públicos ou de \
empresas, profissionais de saúde ou de direito, ou conteúdos universitários muito especializados). Para cada \
escolhido, indique as necessidades (ids da lista dada). Responda só com JSON entre <json></json>: \
[{"n": número do curso na lista, "necessidades": ["id", ...]}]."""


def obter_json(url):
    return json.loads(baixar(url, timeout=40).decode("utf-8", "replace"))


def catalogo():
    itens, pulo = [], 0
    while True:
        r = obter_json(f"{API}/OfertaGratuita/GetList?Ordenacao=5&SkipCount={pulo}&MaxResultCount=100")["result"]
        itens += r["items"]
        pulo += 100
        if pulo >= r["totalCount"] or not r["items"]:
            return itens


def frases_faq():
    """Devolve (gratuito, disponível): as duas frases das perguntas frequentes oficiais, conferidas no texto."""
    texto = " ".join(texto_de_html(p["resposta"].encode()) for g in obter_json(f"{API}/Faq/GetAtivas")["result"]
                     for p in g.get("perguntas", []))
    return citacao_valida(FRASE_GRATUITO, texto), citacao_valida(FRASE_DISPONIVEL, texto)


_ES = {"el", "los", "las", "del", "una", "usted", "sus", "y", "según", "también", "pueden", "conocer", "aprenderá", "le"}
_EN = {"the", "and", "of", "you", "your", "will", "this", "with", "learn"}
_PT = {"o", "os", "do", "da", "dos", "das", "uma", "você", "e", "não", "são", "também", "seus", "suas", "aprender"}


def em_portugues(texto):
    """27/11/2026 (revisão T15): o portfólio da FGV tem versões em espanhol e inglês com o mesmo título
    (ex.: «Fundamentos de Marketing» e «fundamentos-de-marketing-2», em espanhol). O público do site lê português."""
    palavras = re.findall(r"[a-záéíóúâêôãõçñ]+", (texto or "").lower())
    pt = sum(w in _PT for w in palavras)
    return pt >= max(sum(w in _ES for w in palavras), sum(w in _EN for w in palavras))


def detalhe(slug):
    d = obter_json(f"{API}/OfertaGratuita/GetDetalhe?codigoCurso={slug}")["result"]
    objetivo = texto_de_html((d.get("objetivoHtml") or "").encode())
    publico = texto_de_html((d.get("publicoAlvoHtml") or "").encode())
    frases = [f for f in re.split(r"(?<=[.!?])\s+", objetivo) if len(f) > 20 and not re.search(r"^Autor", f)]
    return {"slug": slug, "url": f"{SITE}/curso/{slug}", "titulo": (d.get("nomeCurso") or "").strip(),
            "horas": d.get("cargaHoraria") or 0, "area": d.get("areaConhecimentoCurso") or "",
            "descricao": " ".join(frases[:2])[:500], "publico": publico[:600],
            "prova": exige_prova(objetivo + " " + publico), "portugues": em_portugues(objetivo)}


def provas(d, faq_ok, disp_ok):
    ev, comp = [], []
    if faq_ok:
        ev.append(f"gratuito: «{FRASE_GRATUITO}» ({FAQ}; {MARCA}; perguntas frequentes oficiais)")
        comp.append("gratuito")
    if disp_ok:
        ev.append(f"situação: «{FRASE_DISPONIVEL}» ({FAQ}; {MARCA}; curso autoinstrucional sob demanda)")
        comp.append("situação")
    ev.append(f"certificado: «{FRASE_CERTIFICADO}» ({d['url']}, aba «Certificado»; lida no navegador por Claude a 24/11/2026, "
              f"texto igual em todos os cursos)")
    comp.append("certificado")
    return " | ".join(ev)[:1500], comp


# Frase da aba «Certificado» de cada curso (igual em todos, conferida em 24/11/2026)
FRASE_CERTIFICADO = "Os cursos gratuitos da FGV não geram certificado."


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    try:
        faq_ok, disp_ok = frases_faq()
        itens = catalogo()
    except Exception as e:  # noqa: BLE001
        print(f"  ! API da FGV: {e}")
        registar_pendencia(base, "FGV (cursos gratuitos): a API oficial não abriu.",
                           "Se o portal abre no seu navegador e se mudou de endereço.", SITE, origem="fgv.py")
        base.guardar()
        return 0
    print(f"FGV: {len(itens)} cursos no portfólio; gratuidade nas perguntas frequentes: "
          f"{'conferida' if faq_ok else 'NÃO conferida'}; disponibilidade: {'conferida' if disp_ok else 'NÃO conferida'}.")
    if not (faq_ok and disp_ok and certificado_da_frase("sem certificado", FRASE_CERTIFICADO)):
        registar_pendencia(base, "FGV (cursos gratuitos): as frases das perguntas frequentes mudaram; nada publicado.",
                           "Se os cursos continuam gratuitos e sob demanda.", FAQ, origem="fgv.py")
        base.guardar()
        return 0
    slugs = {i["slug"]: i for i in itens if i.get("modalidadeCurso") == "Online"}
    linhas = base.tabela("Cursos")
    por_slug = {}
    for r in linhas:
        m = re.search(r"cursosgratuitos\.fgv\.br/curso/([^/?#]+)", r.get("Link", "") or "")
        if m:
            por_slug[m.group(1)] = r
    alteracoes, historico = [], []
    # 1. cursos já na planilha: continuam no portfólio?
    for slug, r in por_slug.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        situacao = "Aberto" if slug in slugs else "Encerrado"
        if situacao != r.get("Situação das inscrições"):
            alteracoes.append((r["_linha"], {"Situação das inscrições": situacao, "Última verificação": hoje}))
            print(f"  = {r['Título'][:60]} | {situacao}")
    # 2. cursos novos: lê o detalhe e o Claude escolhe os úteis para o público do site
    novos_lidos = []
    for slug in slugs:
        if slug in por_slug:
            continue
        try:
            d = detalhe(slug)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {slug}: {e}")
            continue
        if d["titulo"] and not d["prova"] and d["portugues"]:
            novos_lidos.append(d)
    novos, custo = [], 0.0
    if novos_lidos:
        escolha = {}
        for ini in range(0, len(novos_lidos), 80):
            lote = novos_lidos[ini:ini + 80]
            lista = "\n".join(f"{i} | {d['titulo'][:120]} | {d['area']} | {d['horas']}h | {d['descricao'][:160]} | "
                              f"Público: {d['publico'][:160]}" for i, d in enumerate(lote, 1))
            texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                                f"Necessidades (id = o que é): {necessidades_para_claude()}.\n\nCursos (número | título | área | "
                                f"horas | descrição | público):\n{lista}", max_tokens=6000)
            custo += custo_estimado(uso, cfg["modelo_cursos"])
            for x in (extrair_json(texto) or []):
                if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(lote):
                    escolha[lote[int(x["n"]) - 1]["slug"]] = x
        print(f"Cursos novos da FGV: {len(novos_lidos)}; o Claude escolheu {len(escolha)}.")
        nota = (f"{hoje}: publicado automaticamente: curso do portfólio de cursos gratuitos da FGV; gratuidade e "
                f"disponibilidade sob demanda nas perguntas frequentes oficiais (conferidas por código).")
        for d in novos_lidos:
            x = escolha.get(d["slug"])
            if not x:
                continue
            evid, comp = provas(d, faq_ok, disp_ok)
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            linha = {
                "ID": "C-" + hashlib.sha1(f"fgv|{d['slug']}".encode()).hexdigest()[:8],
                "Estado": "Publicado", "Título": d["titulo"][:200], "Entidade": ENTIDADE, "Link": d["url"],
                "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": d["descricao"], "Origem da descrição": DESCRICAO_PAGINA if d["descricao"] else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "", "Requisitos": "",
                "Certificado": "sem certificado", "Inscrições até": "", "Início": "",
                "Duração": f"{d['horas']} horas" if d["horas"] else "",
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "fgv",
                "Notas": "Sem certificado: dá uma declaração de participação gratuita depois do pós-teste (nota 7 ou mais).",
                "Como me inscrever": ("1. Abra a página do curso no portal de cursos gratuitos da FGV.\n"
                                      "2. Clique em \"Inscreva-se\" e faça o cadastro (CPF e e-mail).\n"
                                      "3. Estude no seu ritmo; ao terminar, faça o pós-teste.\n"
                                      "4. Com nota 7 ou mais, imprima a declaração de participação na área do aluno."),
                **VERIFICACAO_INICIAL, "Nota da verificação": nota,
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": ", ".join(comp), "Página do curso": d["url"]}
            novos.append(linha)
            historico.append(registo_historico(linha, "Catálogo FGV", "Publicado", linha, d["url"]))
            print(f"  + {d['titulo'][:60]} | {d['horas']}h | {', '.join(nec)}")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"FGV: {len(alteracoes)} cursos atualizados, {len(novos)} novos publicados. Custo estimado: {custo:.3f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
