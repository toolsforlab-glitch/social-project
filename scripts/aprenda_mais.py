"""Cursos on-line abertos (MOOCs) dos institutos federais na plataforma Aprenda Mais, do MEC, com prova por código.

A Aprenda Mais (aprendamais.mec.gov.br) reúne os cursos on-line abertos da Rede Federal (IFRS, IFSC, IFMG e outros).
É um Moodle: as listas por área e a página «Course information» de cada curso (course/info.php?id=N) são públicas e
abrem a partir do GitHub. Cada curso sai por semestre («Turma 2026B»), com uma data para terminar («Conclusão do
curso: até 31/01/2027»); quando a turma acaba, sai da lista e entra uma turma nova do mesmo curso (outro id).

O código confere em cada leitura:
- a gratuidade, na página inicial: «oferece cursos on-line, abertos e gratuitos em diversas áreas do conhecimento»;
- que o curso continua na lista da sua área (senão passa a «Encerrado»), e a data de conclusão na página do curso.

Certificado gratuito (24/11/2026, frase encontrada pela auditoria do ChatGPT e conferida por código): as perguntas
frequentes oficiais (mod/page/view.php?id=100) dizem «Totalmente gratuitos, inclusive o certificado.»; o código
confere a frase a cada leitura. Se a frase sair, os cursos novos ficam com o certificado «desconhecido».

Cada curso é identificado pelo nome sem a turma (ex.: «Contabilidade Básica»); quando entra uma turma nova, o link
e a data de conclusão são atualizados na mesma linha. Turmas «extra» do mesmo curso contam como o mesmo curso (fica a
que termina mais tarde). O Claude só escolhe os cursos que servem ao público do site.
"""
import hashlib
import os
import re
import sys
import unicodedata

from base import (registar_pendencia, certificado_da_frase, DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config,
                  citacao_valida, exige_prova, hoje_iso, registo_historico, texto_de_html)
from comum import baixar, claude, custo_estimado, extrair_json, gravar_json, ler_json

SITE = "https://aprendamais.mec.gov.br"
ENTIDADE = "Aprenda Mais (MEC, Rede Federal)"
MARCA = "lida na plataforma oficial Aprenda Mais, conferida por código"
ESTADO = "estado/aprenda_mais.json"  # cursos já avaliados pelo Claude (escolhidos ou não), para não os reler todos os dias
FAQ = SITE + "/mod/page/view.php?id=100"
FRASE_CERTIFICADO = "Totalmente gratuitos, inclusive o certificado."
FRASE_GRATUITO = "oferece cursos on-line, abertos e gratuitos em diversas áreas do conhecimento"
NECESSIDADES = ["digital", "tecnologia", "portugues", "linguas", "profissao", "mudar", "escola", "emprego", "negocio",
                "dinheiro", "direitos"]
ROTULOS = ["Conteúdo", "Conclusão do curso", "Carga horária", "Prazo mínimo para obtenção do certificado",
           "Público-alvo", "Requisitos", "Módulos", "Metodologia", "Instituição", "Área", "Nível", "Idioma"]
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe cursos \
abertos dos institutos federais (plataforma Aprenda Mais, do MEC; on-line, gratuitos, sem tutoria). Escolha os que \
servem a qualquer pessoa que quer aprender uma profissão, melhorar no trabalho, voltar a estudar ou abrir um \
negócio. Deixe de fora: os pensados só para quem já tem uma profissão ou um cargo (servidores públicos, \
professores, profissionais de saúde, de direito ou de contabilidade, gestores) ou cujos requisitos pedem ser \
estudante ou profissional de uma área, os de nível universitário muito \
especializado e os de programação ou engenharia avançada. Para cada escolhido, indique as necessidades (ids da \
lista dada). Responda só com JSON entre <json></json>: [{"n": número do curso na lista, "necessidades": ["id", ...]}]."""


def nome_base(titulo):
    """«Administração Estratégica (extra Novembro) - Turma 2026B» -> «Administração Estratégica»."""
    t = re.sub(r"\s*[-–]\s*Turma\s+\S+\s*$", "", titulo.strip())
    t = re.sub(r"\s*\((?:extra|turma)[^)]*\)", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def chave(base_nome):
    n = unicodedata.normalize("NFKD", base_nome.lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return "C-" + hashlib.sha1(f"aprendamais|{n}".encode()).hexdigest()[:8]


def areas(pagina_inicial):
    """{categoryid: nome} das áreas do menu da página inicial (sem «Turmas anteriores»)."""
    achadas = re.findall(r'href="https://aprendamais\.mec\.gov\.br/course/index\.php\?categoryid=(\d+)"[^>]*>\s*([^<]+?)\s*<',
                         pagina_inicial)
    return {cid: nome for cid, nome in achadas if not re.search(r"anteriores|autores", nome, re.I)}


def cursos_da_area(cid):
    b = baixar(f"{SITE}/course/index.php?categoryid={cid}&browse=courses&perpage=500&page=0", timeout=90)
    b = b.decode("utf-8", "replace")
    return [(i, re.sub(r"\s+", " ", t).strip()) for i, t in
            re.findall(r'href="https://aprendamais\.mec\.gov\.br/course/view\.php\?id=(\d+)"[^>]*>([^<]{3,})</a>', b)]


def info(curso_id):
    texto = texto_de_html(baixar(f"{SITE}/course/info.php?id={curso_id}", timeout=60))
    campos = {}
    padrao = "|".join(re.escape(r) for r in ROTULOS)
    for m in re.finditer(rf"({padrao}):\s*(.*?)(?=\s+(?:{padrao}):|$)", texto):
        campos.setdefault(m.group(1), m.group(2).strip())
    conclusao = re.search(r"até\s+(\d{2})/(\d{2})/(\d{4})", campos.get("Conclusão do curso", ""))
    campos["conclusao_iso"] = f"{conclusao.group(3)}-{conclusao.group(2)}-{conclusao.group(1)}" if conclusao else ""
    # «6 0 horas» / «4 0 horas» (espaço no meio do número, tal como está na página) -> «60 horas»
    if campos.get("Carga horária"):
        campos["Carga horária"] = re.sub(r"(\d)\s+(?=\d)", r"\1", campos["Carga horária"])
    campos["texto"] = texto
    return campos


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    cfg = carregar_config(base) if base else None
    hoje = hoje_iso()
    try:
        inicial = baixar(SITE + "/", timeout=60).decode("utf-8", "replace")
        gratuito_ok = citacao_valida(FRASE_GRATUITO, texto_de_html(inicial.encode()))
        try:
            cert_ok = (citacao_valida(FRASE_CERTIFICADO, texto_de_html(baixar(FAQ, timeout=60)))
                       and certificado_da_frase("gratuito", FRASE_CERTIFICADO) == "gratuito")
        except Exception:  # noqa: BLE001
            cert_ok = False
        lista = {}
        for cid, area in areas(inicial).items():
            for i, titulo in cursos_da_area(cid):
                lista.setdefault(i, (titulo, area))
    except Exception as e:  # noqa: BLE001
        print(f"  ! Aprenda Mais: {e}")
        if base:
            registar_pendencia(base, "Aprenda Mais (MEC): a plataforma não abriu.",
                               "Se a plataforma abre no seu navegador.", SITE, origem="aprenda_mais.py")
            base.guardar()
        return 0
    # um curso por nome-base (as turmas «extra» contam como o mesmo curso)
    por_nome = {}
    for i, (titulo, area) in lista.items():
        por_nome.setdefault(nome_base(titulo), []).append((i, titulo, area))
    print(f"Aprenda Mais: {len(lista)} turmas na lista, {len(por_nome)} cursos diferentes; frase da gratuidade "
          f"{'conferida' if gratuito_ok else 'NÃO conferida'}.")
    if seco:
        for n, ts in list(por_nome.items())[:5]:
            print("  ·", n, "|", [t[0] for t in ts], "|", info(ts[0][0]))
        return 0
    if not gratuito_ok or not lista:
        registar_pendencia(base, "Aprenda Mais (MEC): a frase da gratuidade mudou ou a lista de cursos não foi lida; "
                                 "nada mudou no site.", "Se os cursos continuam gratuitos.", SITE, origem="aprenda_mais.py")
        base.guardar()
        return 0
    linhas = base.tabela("Cursos")
    na_folha = {r["ID"]: r for r in linhas if r.get("Origem") == "aprenda_mais"}
    alteracoes, historico = [], []

    def melhor_turma(ts):
        """A turma (id, info) que termina mais tarde."""
        lidas = []
        for i, _titulo, _area in ts:
            try:
                lidas.append((i, info(i)))
            except Exception as e:  # noqa: BLE001
                print(f"  ! info {i}: {e}")
        lidas = [x for x in lidas if x[1].get("conclusao_iso", "") >= hoje] or lidas
        return max(lidas, key=lambda x: x[1].get("conclusao_iso", "")) if lidas else (None, None)

    # 1. cursos já na planilha: continuam na lista? mudou de turma?
    ids_atuais = {chave(n): n for n in por_nome}
    for cid, r in na_folha.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        if cert_ok and "certificado" not in (r.get("Campos comprovados") or ""):
            # certificado gratuito provado depois de o curso entrar (24/11/2026): acrescenta-se a prova
            alteracoes.append((r["_linha"], {
                "Certificado": "gratuito",
                "Evidência": ((r.get("Evidência") or "") + f" | certificado: «{FRASE_CERTIFICADO}» ({FAQ}; perguntas frequentes oficiais)")[:1500],
                "Campos comprovados": ((r.get("Campos comprovados") or "").strip(", ") + ", certificado").strip(", "),
                "Notas": (r.get("Notas") or "").replace("as páginas oficiais não dizem se é gratuito", "o certificado é gratuito (perguntas frequentes oficiais)")}))
        if cid not in ids_atuais:
            if r.get("Situação das inscrições") != "Encerrado":
                alteracoes.append((r["_linha"], {"Situação das inscrições": "Encerrado", "Última verificação": hoje}))
                print(f"  = {r['Título'][:60]} | Encerrado")
            continue
        ts = por_nome[ids_atuais[cid]]
        if any(f"id={i}" in (r.get("Link") or "") for i, _t, _a in ts) and r.get("Situação das inscrições") == "Aberto":
            continue
        i, d = melhor_turma(ts)
        if not i:
            continue
        url = f"{SITE}/course/info.php?id={i}"
        mud = {"Link": url, "Página do curso": url, "Situação das inscrições": "Aberto", "Última verificação": hoje,
               "Notas": nota_conclusao(d)}
        alteracoes.append((r["_linha"], mud))
        print(f"  = {r['Título'][:60]} | turma nova {i}")
    # 2. cursos novos: lê a página de cada um e o Claude escolhe os úteis para o público do site
    estado = ler_json(ESTADO, {"avaliados": {}})
    novos_lidos = []
    for n, ts in por_nome.items():
        if chave(n) in na_folha or chave(n) in estado["avaliados"]:
            continue
        i, d = melhor_turma(ts)
        if not i or not d.get("conclusao_iso") or d["conclusao_iso"] < hoje:
            continue
        if exige_prova(d["texto"]):
            continue
        novos_lidos.append({"nome": n, "id": i, "area": ts[0][2], "d": d})
    publicados, custo = [], 0.0
    if novos_lidos:
        escolha = {}
        for ini in range(0, len(novos_lidos), 80):
            lote = novos_lidos[ini:ini + 80]
            texto_lista = "\n".join(
                f"{k} | {c['nome'][:100]} | {c['area']} | {c['d'].get('Carga horária', '')} | "
                f"{c['d'].get('Conteúdo', '')[:150]} | Público: {c['d'].get('Público-alvo', '')[:120]} | "
                f"Requisitos: {c['d'].get('Requisitos', '')[:120]}"
                for k, c in enumerate(lote, 1))
            texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                                f"Necessidades (ids): {', '.join(NECESSIDADES)}.\n\nCursos (número | nome | área | "
                                f"carga horária | conteúdo | público | requisitos):\n{texto_lista}", max_tokens=6000)
            custo += custo_estimado(uso, cfg["modelo_cursos"])
            for x in (extrair_json(texto) or []):
                if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(lote):
                    escolha[ini + int(x["n"]) - 1] = x
        print(f"Cursos novos da Aprenda Mais: {len(novos_lidos)}; o Claude escolheu {len(escolha)}.")
        for c in novos_lidos:
            estado["avaliados"][chave(c["nome"])] = f"{hoje} {c['nome'][:80]}"
        for k, c in enumerate(novos_lidos):
            x = escolha.get(k)
            if not x:
                continue
            d, url = c["d"], f"{SITE}/course/info.php?id={c['id']}"
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            horas = re.search(r"\d+", d.get("Carga horária", ""))
            conteudo = d.get("Conteúdo", "")
            desc = (f"Conteúdo: {conteudo}" if conteudo else "")[:500]
            inst = d.get("Instituição", "")
            evid = " | ".join([
                f"gratuito: «{FRASE_GRATUITO}» ({SITE}/; {MARCA})",
                *([f"certificado: «{FRASE_CERTIFICADO}» ({FAQ}; perguntas frequentes oficiais)"] if cert_ok else []),
                f"situação: «Conclusão do curso: {d.get('Conclusão do curso', '')}» ({url}; {MARCA}; curso sob demanda)",
            ])[:1500]
            linha = {
                "ID": chave(c["nome"]), "Estado": "Publicado", "Título": c["nome"][:200],
                "Entidade": f"{ENTIDADE} — {inst}" if inst else ENTIDADE, "Link": url,
                "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": desc, "Origem da descrição": DESCRICAO_PAGINA if desc else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "",
                "Requisitos": d.get("Requisitos", "")[:300], "Certificado": "gratuito" if cert_ok else "desconhecido",
                "Inscrições até": "", "Início": "", "Duração": f"{horas.group(0)} horas" if horas else "",
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "aprenda_mais",
                "Notas": nota_conclusao(d),
                "Como me inscrever": ("1. Crie a sua conta na plataforma Aprenda Mais, do MEC (aprendamais.mec.gov.br).\n"
                                      "2. Abra a página do curso e faça a inscrição.\n"
                                      f"3. Estude no seu ritmo e termine até {d.get('Conclusão do curso', '').replace('até ', '')}.\n"
                                      "4. Para o certificado de conclusão (gratuito), é preciso ter 60% ou mais de aproveitamento."
                                      if cert_ok else
                                      "4. Para o certificado de conclusão, é preciso ter 60% ou mais de aproveitamento."),
                **VERIFICACAO_INICIAL,
                "Nota da verificação": (f"{hoje}: publicado automaticamente: curso da plataforma Aprenda Mais (MEC); "
                                        f"gratuidade na página oficial e data de conclusão na página do curso, "
                                        f"conferidas por código."),
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": "gratuito, situação" + (", certificado" if cert_ok else ""), "Página do curso": url}
            publicados.append(linha)
            historico.append(registo_historico(linha, "Catálogo Aprenda Mais", "Publicado", linha, url))
            print(f"  + {c['nome'][:55]} | {inst} | {d.get('Carga horária', '')} | {', '.join(nec)}")
    gravar_json(ESTADO, estado)
    base.atualizar("Cursos", alteracoes)
    if publicados:
        base.acrescentar("Cursos", publicados)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Aprenda Mais: {len(alteracoes)} cursos atualizados, {len(publicados)} novos publicados. "
          f"Custo estimado: {custo:.3f} USD")
    return 0


def nota_conclusao(d):
    return (f"Turma atual: termine o curso {d.get('Conclusão do curso', '').strip()}. O certificado de conclusão, "
            f"gratuito, exige 60% de aproveitamento (termos de uso e perguntas frequentes).")


if __name__ == "__main__":
    sys.exit(main())
