"""Trilhas gratuitas on-line da Escola do Trabalhador 4.0 (Ministério do Trabalho e Emprego e Microsoft), com prova
por código.

A plataforma (ead.escoladotrabalhador40.com.br) mostra na página inicial, sem login, todas as trilhas e os cursos de
cada uma; uma API pública da própria plataforma dá a descrição de cada curso. Não há página própria por curso nem
carga horária publicada: o link de cada trilha é a página inicial da plataforma, onde a trilha aparece pelo nome.
Cada trilha é um curso no site (cerca de 40 trilhas, mais de 200 cursos curtos).

O código confere em cada leitura:
- a gratuidade, na própria página inicial: «oferece cursos gratuitos em temas de tecnologia e produtividade»;
- o certificado gratuito, nas perguntas frequentes oficiais da plataforma: «O certificado é reconhecido e
  chancelado pela Microsoft e pelo Ministério do Trabalho, sendo gratuito e emitido automaticamente pela plataforma»
  (regra do responsável de 24/11/2026: curso com certificado pago não entra). Se uma das frases faltar, nada muda e
  fica uma pendência.

O Claude só escolhe quais trilhas servem ao público do site e as necessidades de cada uma. As escolhidas são
publicadas sozinhas; uma trilha que sai da página inicial passa a «Encerrado». A verificação semanal não toca nelas.
"""
import hashlib
import html
import json
import re
import sys

from base import (registar_pendencia, DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config,
                  certificado_da_frase, citacao_valida, exige_prova, hoje_iso, registo_historico, texto_de_html)
from comum import baixar, claude, custo_estimado, extrair_json

SITE = "https://ead.escoladotrabalhador40.com.br/"
CADASTRO = "https://cadastro.escoladotrabalhador40.com.br/"
FAQ_CERTIFICADO = ("https://escoladotrabalhador40.tawk.help/article/"
                   "certificado-como-emitir-posso-utilizar-para-horas-complementares-posso-utilizar-como-curso-t%C3%A9cnico")
ENTIDADE = "Escola do Trabalhador 4.0 (Ministério do Trabalho e Emprego e Microsoft)"
MARCA = "lida na página oficial da plataforma, conferida por código"
FRASE_GRATUITO = "oferece cursos gratuitos em temas de tecnologia e produtividade"
FRASE_CERTIFICADO = ("O certificado é reconhecido e chancelado pela Microsoft e pelo Ministério do Trabalho, sendo "
                     "gratuito e emitido automaticamente pela plataforma.")
FRASE_APROVACAO = "é necessário concluir o curso e atingir pelo menos 50% de aproveitamento no teste de conhecimentos"
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe as trilhas \
da Escola do Trabalhador 4.0 (Ministério do Trabalho e Microsoft; on-line, gratuitas, com certificado gratuito), cada \
uma com os seus cursos. Escolha as que servem a qualquer pessoa que quer aprender, melhorar no trabalho, procurar \
emprego ou abrir um negócio. Deixe de fora: a trilha de boas-vindas; as pensadas só para uma profissão ou um cargo \
(juízes, advogados, servidores públicos, professores, gestores de ONGs); e as preparatórias para certificações \
técnicas de nuvem ou de ERP (Azure, Dynamics 365) que pressupõem experiência em TI. Para cada escolhida, indique as \
necessidades (ids da lista dada). Responda só com JSON entre <json></json>: \
[{"n": número da trilha na lista, "necessidades": ["id", ...]}]."""


def limpar(nome):
    """Tira a numeração do início («01. », «1. », «01 - »)."""
    return re.sub(r"^\s*\d+\s*[.\-–]\s*", "", html.unescape(nome)).strip()


def trilhas(pagina):
    """[{titulo, cursos: [(id, nome)]}] da página inicial (cada trilha é um <h2 class="category-wrapper__heading">)."""
    partes = re.split(r'<h2 class="category-wrapper__heading"[^>]*>', pagina)[1:]
    saida = []
    for parte in partes:
        titulo = limpar(parte.split("</h2>", 1)[0])
        cursos = [(cid, limpar(nome)) for cid, nome in re.findall(
            r'data-course-id="(\d+)"[\s\S]*?course-card-container__course-name">([^<]+)<', parte.split("</h2>", 1)[1])]
        if titulo and cursos:
            saida.append({"titulo": titulo, "cursos": cursos})
    return saida


def descricao_curso(cid):
    d = json.loads(baixar(f"{SITE}api/v1/Courses/{cid}/Metadata", timeout=60).decode("utf-8", "replace"))
    texto = re.sub(r"\s+", " ", d.get("CourseDescription") or "").strip()
    return re.sub(r"\s*Acesse o curso e saiba mais\.?$", "", texto)


def descricao(t):
    if len(t["cursos"]) == 1:
        return (t.get("detalhe") or "")[:500]
    return ("Trilha com " + str(len(t["cursos"])) + " cursos: " + "; ".join(n for _, n in t["cursos"]) + ".")[:500]


def provas():
    ev = [f"gratuito: «{FRASE_GRATUITO}» ({SITE}; {MARCA})",
          f"certificado: «{FRASE_CERTIFICADO}» ({FAQ_CERTIFICADO}; perguntas frequentes oficiais, conferida por código)",
          f"situação: trilha listada na página inicial da plataforma ({SITE}; {MARCA}; cursos sob demanda)"]
    return " | ".join(ev)[:1500], ["gratuito", "certificado", "situação"]


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    try:
        bruto = baixar(SITE, timeout=60).decode("utf-8", "replace")
        texto_site = texto_de_html(bruto.encode())
        texto_faq = texto_de_html(baixar(FAQ_CERTIFICADO, timeout=120))
    except Exception as e:  # noqa: BLE001
        print(f"  ! Escola do Trabalhador 4.0: {e}")
        registar_pendencia(base, "Escola do Trabalhador 4.0: a plataforma ou as perguntas frequentes não abriram.",
                           "Se a plataforma abre no seu navegador e se mudou de endereço.", SITE,
                           origem="escola_trabalhador.py")
        base.guardar()
        return 0
    lidas = trilhas(bruto)
    frases_ok = (citacao_valida(FRASE_GRATUITO, texto_site) and citacao_valida(FRASE_CERTIFICADO, texto_faq)
                 and citacao_valida(FRASE_APROVACAO, texto_faq)
                 and certificado_da_frase("gratuito", FRASE_CERTIFICADO) == "gratuito")
    print(f"Escola do Trabalhador 4.0: {len(lidas)} trilhas, {sum(len(t['cursos']) for t in lidas)} cursos; frases da "
          f"gratuidade e do certificado gratuito {'conferidas' if frases_ok else 'NÃO conferidas'}.")
    if not frases_ok or not lidas:
        registar_pendencia(base, "Escola do Trabalhador 4.0: a frase da gratuidade ou do certificado gratuito mudou "
                                 "(ou a lista de trilhas não foi lida); nada mudou no site.",
                           "Se os cursos e o certificado continuam gratuitos.", FAQ_CERTIFICADO,
                           origem="escola_trabalhador.py")
        base.guardar()
        return 0
    def chave(titulo):
        return "C-" + hashlib.sha1(f"escola_trabalhador|{titulo.lower()}".encode()).hexdigest()[:8]
    por_id = {chave(t["titulo"]): t for t in lidas}
    linhas = base.tabela("Cursos")
    na_folha = {r["ID"]: r for r in linhas if r.get("Origem") == "escola_trabalhador"}
    alteracoes, historico = [], []
    # 1. trilhas já na planilha: continuam na página inicial?
    for cid, r in na_folha.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        situacao = "Aberto" if cid in por_id else "Encerrado"
        if situacao != r.get("Situação das inscrições"):
            alteracoes.append((r["_linha"], {"Situação das inscrições": situacao, "Última verificação": hoje}))
            print(f"  = {r['Título'][:60]} | {situacao}")
    # 2. trilhas novas: o Claude escolhe as úteis para o público do site
    novas = [t for cid, t in por_id.items() if cid not in na_folha]
    for t in novas:
        try:
            t["detalhe"] = descricao_curso(t["cursos"][0][0])
        except Exception as e:  # noqa: BLE001
            print(f"  ! descrição de {t['titulo'][:40]}: {e}")
            t["detalhe"] = ""
    novas = [t for t in novas if not exige_prova(t["titulo"] + " " + t["detalhe"])]
    publicadas, custo = [], 0.0
    if novas:
        lista = "\n".join(f"{i} | {t['titulo'][:120]} | cursos: {'; '.join(n for _, n in t['cursos'])[:300]} | "
                          f"{t['detalhe'][:160]}" for i, t in enumerate(novas, 1))
        texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                            f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nTrilhas (número | título | cursos | "
                            f"descrição do primeiro curso):\n{lista}", max_tokens=4000)
        custo += custo_estimado(uso, cfg["modelo_cursos"])
        escolha = {}
        for x in (extrair_json(texto) or []):
            if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(novas):
                escolha[int(x["n"]) - 1] = x
        print(f"Trilhas novas: {len(novas)}; o Claude escolheu {len(escolha)}.")
        evid, comp = provas()
        nota = (f"{hoje}: publicado automaticamente: trilha da Escola do Trabalhador 4.0 (on-line; gratuidade na página "
                f"da plataforma e certificado gratuito nas perguntas frequentes oficiais, conferidos por código).")
        for i, t in enumerate(novas):
            x = escolha.get(i)
            if not x:
                continue
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            desc = descricao(t)
            linha = {
                "ID": chave(t["titulo"]), "Estado": "Publicado", "Título": t["titulo"][:200], "Entidade": ENTIDADE,
                "Link": SITE, "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": desc, "Origem da descrição": DESCRICAO_PAGINA if desc else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "", "Requisitos": "",
                "Certificado": "gratuito", "Inscrições até": "", "Início": "", "Duração": "",
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
                "Origem": "escola_trabalhador",
                "Notas": "Trilha da Escola do Trabalhador 4.0; certificado gratuito por curso concluído.",
                "Como me inscrever": (f"1. Faça o cadastro gratuito em {CADASTRO}\n"
                                      "2. Entre na plataforma da Escola do Trabalhador 4.0 e procure a trilha "
                                      f"\"{t['titulo']}\".\n"
                                      "3. Estude cada curso da trilha no seu ritmo.\n"
                                      "4. No fim de cada curso, faça o teste: com 50% de acertos ou mais, baixe o "
                                      "certificado gratuito."),
                **VERIFICACAO_INICIAL, "Nota da verificação": nota,
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": ", ".join(comp), "Página do curso": ""}
            publicadas.append(linha)
            historico.append(registo_historico(linha, "Catálogo Escola do Trabalhador 4.0", "Publicado", linha, SITE))
            print(f"  + {t['titulo'][:60]} | {len(t['cursos'])} cursos | {', '.join(nec)}")
    base.atualizar("Cursos", alteracoes)
    if publicadas:
        base.acrescentar("Cursos", publicadas)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Escola do Trabalhador 4.0: {len(alteracoes)} trilhas atualizadas, {len(publicadas)} novas publicadas. "
          f"Custo estimado: {custo:.3f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
