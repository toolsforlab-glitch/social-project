"""Cursos on-line gratuitos do Sebrae (loja.sebrae.com.br), lidos do catálogo oficial, com prova por código.

O catálogo inteiro está no mapa do site (loja.sebrae.com.br/sitemap.xml, cerca de 500 páginas de produtos). A lista
de cursos do site só mostra 12 por vez e o resto vem por JavaScript, e o robots.txt pede para não ler endereços com
"?", por isso o mapa do site é o caminho certo. Em cada página o código lê, sem modelo pelo meio:

- o preço e a etiqueta de gratuidade («R$ 0,00 Gratuito»), que provam a gratuidade com frase da própria página;
- a forma de execução, na tabela «Mais Informações» da página («Forma de Execução: Curso autoinstrucional»). Só estes
  cursos são CLARAMENTE sob demanda pela própria página (regra do responsável, 21/11/2026);
- os cursos que a página chama só de «Curso online» (não «Ao vivo») entram pela regra que o responsável marcou em
  Sites de confiança a 22/11/2026 (loja.sebrae.com.br, «Curso online»): com «R$ 0,00 Gratuito», «Em estoque» e
  sem datas de turma na página, são autoinstrucionais com inscrições abertas. A base escrita são os Termos de Uso da
  Loja, item 7.3 «CURSOS ONLINE (autoinstrucionais)»: o código confere essa frase a cada rodada e, se ela sair dos
  termos (ou a regra sair de Sites de confiança), estes cursos deixam de estar provados e voltam para Novo;
- o título, a duração («Duração 10h»), o perfil (público) e o começo da descrição.

O Sebrae tem muitos cursos em duas páginas iguais (a versão antiga “… - chatbot” e a nova, com o mesmo texto): o
código junta-as pela descrição (ou pelo título sem “chatbot”) e fica só com a página nova; a outra passa a Oculto,
com a nota “duplicado”.

O Claude só escolhe quais cursos servem ao público do site (não os pensados para professores, escolas, gestores
públicos ou profissões muito específicas) e as necessidades de cada um. Os escolhidos são publicados sozinhos; cursos já
na planilha com «Mudança a rever» marcada ou «Revisto por pessoa» não mudam de Estado. A verificação semanal não toca
nestes cursos; este leitor relê-os a cada rodada e, se um deixar de ser gratuito ou autoinstrucional, deixa de
estar provado (Situação «Por confirmar») e volta para Novo.
"""
import datetime
import hashlib
import json
import os
from html import unescape
import re
import sys
import urllib.parse
import urllib.request

from base import (DESCRICAO_PAGINA, ENCERRADO, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida,
                  hoje_iso, registo_historico, sim, texto_de_html)
from comum import claude, custo_estimado, extrair_json

SITE = "https://loja.sebrae.com.br"
ESTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "estado", "sebrae.json")
LOTE = 80  # cursos por pergunta ao Claude
DIAS_RECUSA = 90  # um curso que o Claude deixou de fora só volta a ser perguntado depois deste tempo
MAPA = SITE + "/sitemap.xml"
TERMOS = SITE + "/termo-de-uso-loja-sebrae"
FRASES_TERMOS = ["CURSOS ONLINE (autoinstrucionais)",
                 "Os cursos online da modalidade autoinstrucional (por interfaces conversacionais automatizadas ou por "
                 "ambiente educacional) são oferecidos pelo Sebrae Nacional."]
DATAS = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2} de (janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|"
                   r"setembro|outubro|novembro|dezembro)\b", re.I)
PRODUTO = re.compile(r"^https://loja\.sebrae\.com\.br/[a-z0-9-]+-(?:\d{9,}|a0[a-z0-9]{14,})/?$", re.I)
ENTIDADE = "Sebrae (cursos online)"
MARCA = "lida na página oficial, conferida por código"
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro, a abrir ou cuidar de um pequeno negócio (MEI, \
artesão, produtor rural) ou a conhecer os seus direitos. Recebe cursos do Sebrae. Escolha os que servem a qualquer \
pessoa que quer aprender, trabalhar ou empreender (deixe de fora os pensados só para professores, alunos de uma série \
escolar, escolas, gestores públicos, advogados, startups ou profissionais de áreas muito específicas). Para cada \
escolhido, indique as necessidades (ids da lista dada). Responda só com JSON entre <json></json>: \
[{"n": número do curso na lista, "necessidades": ["id", ...]}]."""


def obter(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto social; leitura do catálogo público)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def catalogo():
    mapa = obter(MAPA)
    return [u for u in dict.fromkeys(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", mapa)) if PRODUTO.match(u)]


def chave(url):
    return urllib.parse.urlparse(url).path.rstrip("/").lower()


def _limpo(trecho):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", trecho or ""))).strip()


def ler_curso(url):
    html = obter(url)
    texto = texto_de_html(html.encode())
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S | re.I)
    titulo = _limpo(m.group(1)) if m else ""
    if not titulo:
        m = re.search(r"<title>([^<]{3,300})</title>", html, flags=re.I)
        titulo = re.split(r"\s+-\s+Sebrae\s*$", _limpo(m.group(1)))[0] if m else ""
    rotulo = re.search(r'class="[^"]*short-title[^"]*"[^>]*>(.*?)</span>', html, flags=re.S)
    rotulo = _limpo(rotulo.group(1)) if rotulo else ""
    forma = re.search(r"<th[^>]*>\s*Forma de Execu[çc][ãa]o\s*</th>\s*<td[^>]*>(.*?)</td>", html, flags=re.S | re.I)
    forma = _limpo(forma.group(1)) if forma else ""
    perfil = re.search(r"<th[^>]*>\s*Perfil\s*</th>\s*<td[^>]*>(.*?)</td>", html, flags=re.S | re.I)
    perfil = _limpo(perfil.group(1)) if perfil else ""
    # gratuidade: etiqueta «Gratuito» do bloco de preço, com o preço R$ 0,00
    gratis = bool(re.search(r'class="[^"]*\bfree\b[^"]*"[^>]*>\s*Gratuito\s*<', html)) and \
        bool(re.search(r'class="price"[^>]*>\s*R\$\s*0,00\s*<', html))
    frase_gratis = ""
    if gratis:
        m = re.search(r"R\$\s*0,00\s+Gratuito", texto)
        frase_gratis = m.group(0) if m else ""
    k = html.find('class="pdp-duration"')
    duracao = re.search(r'class="duration"[^>]*>\s*Dura[çc][ãa]o\s*(\d+)\s*h', html[k:k + 5000]) if k >= 0 else None
    # área do produto (do título até «Ainda na dúvida?»), para não ler os outros produtos sugeridos na página
    i = texto.find(titulo) if titulo else -1
    j = texto.find("Ainda na dúvida", max(i, 0))
    area = texto[max(i, 0):j if j > 0 else None]
    em_estoque = "Em estoque" in area
    descricao = ""
    m = re.search(r'class="product attribute description"[^>]*>(.*?)</div>\s*</div>', html, flags=re.S)
    if m:
        seg = _limpo(m.group(1))
    else:
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]{20,600})"', html, flags=re.I)
        seg = unescape(m.group(1)).strip() if m else ""
    frases = [f for f in re.split(r"(?<=[.!?])\s+", seg) if len(f) > 15 and not re.search(r"inscreva|compr", f, re.I)]
    descricao = " ".join(frases[:2])[:500]
    frase_forma = f"Forma de Execução {forma}" if forma else ""
    autoinstrucional = (forma.lower() == "curso autoinstrucional" and citacao_valida(frase_forma, texto)
                        and not ENCERRADO.search(area) and em_estoque)
    rot = rotulo.lower()
    m_data, m_enc = DATAS.search(area), ENCERRADO.search(area)
    motivo_regra = ("não é “Curso online”" if not rot.startswith("curso online /") else "ao vivo" if "ao vivo" in rot
                    else "fora de estoque" if not em_estoque else f"data na página («{m_data.group(0)}»)" if m_data
                    else f"página diz «{m_enc.group(0)}»" if m_enc else "")
    online_regra = not motivo_regra
    return {"url": url, "titulo": titulo, "online_regra": online_regra, "motivo_regra": motivo_regra, "via_regra": False, "rotulo": rotulo, "forma": forma, "perfil": perfil, "texto": texto,
            "gratis": bool(frase_gratis) and citacao_valida(frase_gratis, texto), "frase_gratis": frase_gratis,
            "aberto": autoinstrucional, "frase_forma": frase_forma,
            "duracao": f"{int(duracao.group(1))} horas" if duracao else "", "descricao": descricao}


def _sem_acentos(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "")
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in t if not unicodedata.combining(c)).lower())


VAZIAS = {"a", "o", "as", "os", "de", "do", "da", "dos", "das", "e", "em", "para", "seu", "sua", "um", "uma", "no", "na"}


def chaves_curso(d):
    """O mesmo curso em duas páginas tem a mesma descrição ou o mesmo título (sem “chatbot”, “curso” e palavras vazias)."""
    chaves = []
    desc = " ".join(_sem_acentos(d["descricao"]).split())[:90]
    if len(desc) >= 40:
        chaves.append("d:" + desc)
    tit = re.sub(r"\b(chatbot|curso de gestao|curso)\b", " ", _sem_acentos(d["titulo"]))
    tit = " ".join(p for p in tit.split() if p not in VAZIAS)
    if len(tit) >= 8:
        chaves.append("t:" + tit)
    return chaves


def agrupar(lidos):
    """{url: url da página que fica} para os cursos repetidos; fica a página nova (código a0…) ou a primeira.
    Duas páginas são o mesmo curso se partilham a descrição ou o título (e, por arrasto, os grupos juntam-se)."""
    pai = {}

    def raiz(x):
        while pai.setdefault(x, x) != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for u, d in lidos.items():
        if d["aberto"] and d["gratis"]:
            raiz(u)
            for k in chaves_curso(d):
                pai[raiz(u)] = raiz(k)
    grupos = {}
    for u, d in lidos.items():
        if d["aberto"] and d["gratis"]:
            grupos.setdefault(raiz(u), []).append(u)
    fica = {}
    for us in grupos.values():
        melhor = sorted(us, key=lambda u: (not re.search(r"-a0[a-z0-9]{14,}/?$", u), "chatbot" in u, u))[0]
        for u in us:
            fica[u] = melhor
    return fica


def ler_estado():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_estado(est):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=1, sort_keys=True)


def nota_publicado(d, hoje):
    if d["via_regra"]:
        return (f"{hoje}: publicado automaticamente: a página diz “{d['frase_gratis']}” e “Curso online”, sem datas de "
                f"turma; regra do responsável para a loja do Sebrae (Sites de confiança), com base nos Termos de Uso, "
                f"item 7.3 “CURSOS ONLINE (autoinstrucionais)” (conferido por código).")
    return (f"{hoje}: publicado automaticamente: a página diz “{d['frase_gratis']}” e “{d['frase_forma']}” "
            f"(conferido por código).")


def provas(d):
    ev, comp = [], []
    if d["gratis"]:
        ev.append(f"gratuito: «{d['frase_gratis']}» ({d['url']}; {MARCA})")
        comp.append("gratuito")
    if d["via_regra"]:
        ev.append(f"situação: «Curso online» ({d['url']}; {MARCA}; sem datas de turma; regra marcada por uma pessoa "
                  f"em Sites de confiança)")
        ev.append(f"situação: «{FRASES_TERMOS[1]}» ({TERMOS}; {MARCA}; Termos de Uso da Loja, item 7.3)")
        comp.append("situação")
    elif d["aberto"]:
        ev.append(f"situação: «{d['frase_forma']}» ({d['url']}; {MARCA}; curso claramente sob demanda, sem turma "
                  f"nem prazo de inscrição na página)")
        comp += ["situação", "sob demanda"]
    return " | ".join(ev)[:1500], comp


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    urls = catalogo()
    print(f"Catálogo do Sebrae (mapa do site): {len(urls)} páginas de produtos.")
    linhas = base.tabela("Cursos")
    por_chave = {}
    for r in linhas:
        for l in (r.get("Link", ""), r.get("Página do curso", "")):
            if "loja.sebrae.com.br" in (l or ""):
                por_chave.setdefault(chave(l), r)
    lidos, falhas = {}, 0
    for u in urls:
        try:
            lidos[u] = ler_curso(u)
        except Exception as e:  # noqa: BLE001
            falhas += 1
            print(f"  ! {u}: {e}")
    regra = cfg["cursos"].get("botao_inscricao", {}).get("loja.sebrae.com.br", "").strip().lower() == "curso online"
    termos_ok = False
    if regra:
        try:
            pagina_termos = texto_de_html(obter(TERMOS).encode())
            termos_ok = all(citacao_valida(f, pagina_termos) for f in FRASES_TERMOS)
        except Exception as e:  # noqa: BLE001
            print(f"  ! Termos de Uso: {e}")
    print(f"Regra “Curso online” em Sites de confiança: {'sim' if regra else 'não'}; frase do item 7.3 nos Termos de "
          f"Uso: {'conferida' if termos_ok else 'NÃO conferida'}.")
    for d in lidos.values():
        if not d["aberto"] and regra and termos_ok and d["online_regra"] and d["gratis"]:
            d["aberto"] = d["via_regra"] = True
    motivos = {}
    for d in lidos.values():
        if d["gratis"] and not d["aberto"] and d["rotulo"].lower().startswith("curso online"):
            m = re.sub(r"«.*»", "«…»", d["motivo_regra"])
            motivos.setdefault(m, []).append(d)
    for m, ds in sorted(motivos.items(), key=lambda x: -len(x[1])):
        print(f"  “Curso online” fora da regra: {len(ds)} | {m} | ex.: {ds[0]['url']} {ds[0]['motivo_regra']}")
    contagem = {}
    for d in lidos.values():
        k = (("gratuito" if d["gratis"] else "sem gratuidade provada") + " | " + (d["forma"] or d["rotulo"].split(" / ")[0] or "sem rótulo")
             + (" | aberto pela regra" if d["via_regra"] else " | aberto pela página" if d["aberto"] else " | não provado"))
        contagem[k] = contagem.get(k, 0) + 1
    for k, n in sorted(contagem.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {k}")
    fica = agrupar(lidos)
    print(f"  {sum(1 for u, f in fica.items() if u != f)} páginas repetidas (mesmo curso em outra página).")
    est = ler_estado()
    recusados = est.setdefault("recusados", {})
    corte = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_RECUSA)).isoformat()
    alteracoes, historico = [], []
    # 1. cursos já na planilha: relidos a cada rodada
    for u, d in lidos.items():
        r = por_chave.get(chave(u))
        if not r or r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        if fica.get(u, u) != u:
            campos = {"Estado": "Oculto", "Última verificação": hoje,
                      "Nota da verificação": f"{hoje}: duplicado: o mesmo curso está em {fica[u]} (mesmo texto na página)."}
            historico.append(registo_historico(r, "Catálogo Sebrae", "Oculto (duplicado)", campos, fica[u]))
            alteracoes.append((r["_linha"], campos))
            continue
        evid, comp = provas(d)
        outros = [c.strip() for c in (r.get("Campos comprovados") or "").split(",")
                  if c.strip() and c.strip() not in ("situação", "gratuito", "sob demanda")]
        campos = {"Situação das inscrições": "Aberto" if d["aberto"] and d["gratis"] else "Por confirmar",
                  "Evidência": evid, "Campos comprovados": ", ".join(outros + comp), "Página do curso": u,
                  "Última verificação": hoje, "Verificar automaticamente": "FALSE", "Destino do link": ""}
        if d["duracao"] and (not r.get("Duração") or r.get("Origem") == "sebrae"):
            campos["Duração"] = d["duracao"]
        if not (r.get("Descrição") or "").strip() and d["descricao"]:
            campos["Descrição"], campos["Origem da descrição"] = d["descricao"], DESCRICAO_PAGINA
        provado = d["aberto"] and d["gratis"]
        if r.get("Estado") == "Novo" and provado and not sim(r.get("Mudança a rever")):
            campos["Estado"] = "Publicado"
            campos["Nota da verificação"] = nota_publicado(d, hoje)
            historico.append(registo_historico(r, "Catálogo Sebrae", "Publicado", campos, u))
        elif r.get("Estado") == "Publicado" and not provado:
            campos["Estado"] = "Novo"
            campos["Nota da verificação"] = (f"{hoje}: voltou para Novo: a página já não mostra "
                                             + ("a gratuidade" if not d["gratis"] else "que é autoinstrucional (ou a "
                                                "regra “Curso online” deixou de valer)") + " (conferido por código).")
            historico.append(registo_historico(r, "Catálogo Sebrae", "Despublicado", campos, u))
        alteracoes.append((r["_linha"], campos))
    # 2. cursos novos: só os gratuitos E autoinstrucionais; o Claude escolhe os úteis para o público do site
    ja = {chave(u) for u in por_chave}
    novos_lidos = [d for u, d in lidos.items() if chave(u) not in ja and d["aberto"] and d["gratis"] and d["titulo"]
                   and fica.get(u, u) == u and recusados.get(u, "") < corte]
    novos, custo = [], 0.0
    if novos_lidos:
        escolha, respondidos = {}, set()
        for ini in range(0, len(novos_lidos), LOTE):
            lote = novos_lidos[ini:ini + LOTE]
            lista = "\n".join(f"{i} | {d['titulo'][:150]} | público: {d['perfil'][:120] or '—'} | {d['descricao'][:200]}"
                              for i, d in enumerate(lote, 1))
            try:
                texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                                    f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nCursos (número | título | público | "
                                    f"descrição):\n{lista}", max_tokens=6000)
            except Exception as e:  # noqa: BLE001
                print(f"  ! Claude, lote {ini // LOTE + 1}: {e}")
                continue
            custo += custo_estimado(uso, cfg["modelo_cursos"])
            resposta = extrair_json(texto)
            if not isinstance(resposta, list):
                print(f"  ! lote {ini // LOTE + 1}: resposta sem JSON; estes cursos voltam a ser perguntados na próxima rodada")
                continue
            respondidos.update(d["url"] for d in lote)  # só estes contam como “deixados de fora” se não forem escolhidos
            for x in resposta:
                if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(lote):
                    escolha[lote[int(x["n"]) - 1]["url"]] = x
        print(f"Cursos novos gratuitos com inscrição aberta provada: {len(novos_lidos)}; o Claude escolheu {len(escolha)}.")
        for d in novos_lidos:
            x = escolha.get(d["url"])
            if not x:
                if d["url"] in respondidos:
                    recusados[d["url"]] = hoje
                continue
            recusados.pop(d["url"], None)
            evid, comp = provas(d)
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            novos.append({
                "ID": "C-" + hashlib.sha1(f"sebrae|{chave(d['url'])}".encode()).hexdigest()[:8],
                "Estado": "Publicado", "Título": d["titulo"][:200], "Entidade": ENTIDADE, "Link": d["url"],
                "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": d["descricao"], "Origem da descrição": DESCRICAO_PAGINA if d["descricao"] else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "", "Requisitos": "",
                "Certificado": "desconhecido", "Inscrições até": "", "Início": "", "Duração": d["duracao"],
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "sebrae",
                "Notas": "", "Como me inscrever": "", **VERIFICACAO_INICIAL,
                "Nota da verificação": nota_publicado(d, hoje),
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": ", ".join(comp), "Página do curso": d["url"]})
            print(f"  + {d['titulo'][:60]} | {d['duracao']}")
    print(f"Gratuitos mas sem prova de inscrição aberta: {sum(1 for d in lidos.values() if d['gratis'] and not d['aberto'])}.")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    # linha do Sebrae na aba Catálogos
    try:
        for cat in base.tabela("Catálogos"):
            if (cat.get("Domínio") or "").strip().lower() == "loja.sebrae.com.br":
                base.atualizar("Catálogos", [(cat["_linha"], {"Última leitura": hoje, "Cursos encontrados": str(len(urls))})])
    except Exception as e:  # noqa: BLE001
        print(f"  ! aba Catálogos: {e}")
    base.guardar()
    guardar_estado(est)
    print(f"Sebrae: {len(lidos)} páginas lidas ({falhas} falhas), {len(alteracoes)} cursos atualizados, "
          f"{len(novos)} novos publicados. Custo estimado: {custo:.3f} USD")


if __name__ == "__main__":
    sys.exit(main())
