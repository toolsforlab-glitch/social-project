"""Cursos on-line abertos de duas plataformas Moodle públicas, com prova por código (desde 28/11/2026).

- **MOOC do Centro Paula Souza** (cursosmooc.cps.sp.gov.br; o endereço antigo mooc.cps.sp.gov.br dá 404 desde a
  mudança para o «novo ambiente virtual», ligado na página da SEAD). A página inicial diz «Qualquer pessoa pode
  participar, sem custo e sem necessidade de matrícula formal.» (conferida por código a cada leitura) e lista os cursos
  disponíveis (cerca de 20). Não há descrição nem carga horária por curso. Certificado: a página diz que, ao concluir,
  «você recebe um certificado com carga horária estimada», mas não diz se tem custo: fica «desconhecido».
- **Plataforma +IFMG** (mais.ifmg.edu.br/maisifmg): a página inicial lista os «Cursos disponíveis» (cerca de 150), cada
  um com campos oficiais («Curso gratuito: Sim», «Oferece Certificado de Conclusão: Sim», «Carga Horária», «Requisitos
  para Ingresso», «Público-alvo»…), e a página «Informações do curso» (course/info.php?id=N, pública) repete
  «Gratuito : sim». Só entram os cursos com «Curso gratuito: Sim» (conferido por código, curso a curso). Sem seleção:
  a carta de serviços do IFMG no gov.br diz «Para a participação em cursos FIC ofertados pela Plataforma +IFMG, não há
  processo seletivo. Os cursos poderão ser realizados de imediato no momento da inscrição ao curso pela própria
  plataforma.» (o gov.br não abre a partir do GitHub: frase lida no navegador por Claude a 28/11/2026). Ficam fora as
  turmas com tutoria e datas («turma 2026», «2026.1»), os cursos com teste de entrada e as áreas ProGestores e
  Formação para EaD (para servidores e professores). O certificado de conclusão existe, mas as páginas oficiais não
  dizem se é gratuito: fica «desconhecido».

Um curso que sai da lista da plataforma (ou deixa de dizer «Curso gratuito: Sim») passa a «Encerrado». O Claude só
escolhe os cursos que servem ao público do site e as necessidades de cada um; os já avaliados ficam em
`estado/moodle_abertos.json` para não voltarem ao Claude todos os dias. Cursos com o mesmo título de um curso on-line
já publicado (ex.: o mesmo curso do IFMG na Aprenda Mais) não entram outra vez. A verificação semanal não toca nestes
cursos. Ensaio: `SECO=1 python3 moodle_abertos.py` (lê e mostra, sem gravar nem chamar o Claude).
"""
import hashlib
import html
import os
import re
import sys
import unicodedata

from base import (NECESSIDADES, necessidades_para_claude, registar_pendencia, DESCRICAO_PAGINA, HISTORICO, VERIFICACAO_INICIAL, Base,
                  carregar_config, citacao_valida, exige_prova, gratuidade_explicita, hoje_iso, registo_historico, texto_de_html)
from comum import baixar, claude, custo_estimado, extrair_json, gravar_json, ler_json

ESTADO = "estado/moodle_abertos.json"
SISTEMA = """Você escolhe cursos on-line gratuitos para um site que ajuda pessoas em situação de vulnerabilidade no \
Brasil a encontrar qualificação, emprego, a organizar o dinheiro ou a conhecer os seus direitos. Recebe cursos \
on-line abertos de uma instituição pública de ensino (gratuitos, no ritmo de cada um). Escolha os que servem a \
qualquer pessoa que quer aprender uma profissão, melhorar no trabalho, voltar a estudar, preparar-se para o ENEM ou \
abrir um negócio. Deixe de fora: os pensados só para quem já tem uma profissão ou um cargo (professores, servidores, \
gestores, profissionais de saúde ou de direito), os que pedem ser estudante ou profissional de uma área (curso \
técnico, superior), os de nível universitário muito especializado e os de programação ou engenharia avançada. Para \
cada escolhido, indique as necessidades (ids da lista dada). Responda só com JSON entre <json></json>: \
[{"n": número do curso na lista, "necessidades": ["id", ...]}]."""


def _tx(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def normal(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


# ------------------------------------------------------------------ MOOC do Centro Paula Souza
CPS_SITE = "https://cursosmooc.cps.sp.gov.br"
CPS_FRASE = "Qualquer pessoa pode participar, sem custo e sem necessidade de matrícula formal."
CPS_FRASE_CERT = ("Ao concluir todas as etapas e atividades propostas, você recebe um certificado com carga horária "
                  "estimada, válido para fins de formação e aperfeiçoamento.")


def ler_cps():
    """(frases conferidas, [cursos]) da página inicial do MOOC do CPS."""
    pag = baixar(CPS_SITE + "/", timeout=60).decode("utf-8", "replace")
    texto = texto_de_html(pag.encode())
    ok = citacao_valida(CPS_FRASE, texto) and gratuidade_explicita(CPS_FRASE)
    cert = citacao_valida(CPS_FRASE_CERT, texto)
    vistos, cursos = set(), []
    for cid, nome in re.findall(r'<h6><a href=["\']?https://cursosmooc\.cps\.sp\.gov\.br/course/view\.php\?id=(\d+)["\']?>([^<]+)</a>', pag):
        nome = _tx(nome)
        if cid in vistos or len(nome) < 3:
            continue
        vistos.add(cid)
        url = f"{CPS_SITE}/course/view.php?id={cid}"
        cursos.append({"chave": "cps|" + cid, "id": cid, "titulo": nome, "url": url, "area": "", "horas": "", "descricao": "",
                       "requisitos": "", "publico": "", "gratis": ok, "certificado_existe": cert})
    return ok, cursos


# ------------------------------------------------------------------ Plataforma +IFMG
IFMG_SITE = "https://mais.ifmg.edu.br/maisifmg"
IFMG_GOVBR = "https://www.gov.br/pt-br/servicos/participar-de-processo-seletivo-para-curso-de-formacao-inicial-e-continuada-ifmg"
IFMG_FRASE_SEM_SELECAO = ("Para a participação em cursos FIC ofertados pela Plataforma +IFMG, não há processo seletivo. "
                          "Os cursos poderão ser realizados de imediato no momento da inscrição ao curso pela própria plataforma.")
IFMG_AREAS_FORA = {"ProGestores", "Formação para EaD"}
_TURMA = re.compile(r"\bturmas?\b|\b20\d\d(?:\.\d)?\b|com tutores", re.I)


def ler_ifmg():
    pag = baixar(IFMG_SITE + "/", timeout=90).decode("utf-8", "replace")
    cursos = []
    for b in re.split(r'<div class="card dashboard-card " role="listitem"', pag)[1:]:
        cid = re.search(r'data-course-id="(\d+)"', b)
        nome = re.search(r'class="aalink coursename[^"]*">(.*?)</a>', b, re.S)
        if not cid or not nome:
            continue
        cat = re.search(r'class="course-category">(.*?)</div>', b, re.S)
        campos = {_tx(k): _tx(v) for k, v in re.findall(
            r'<span class="customfieldname">(.*?)</span><span class="customfieldseparator">: </span>'
            r'<span class="customfieldvalue">(.*?)</span>\s*</div>', b, re.S)}
        req = campos.get("Requisitos para Ingresso", "")
        cursos.append({
            "chave": "ifmg|" + cid[1], "id": cid[1], "titulo": _tx(nome[1]), "url": f"{IFMG_SITE}/course/info.php?id={cid[1]}",
            "area": _tx(cat[1]) if cat else "", "horas": campos.get("Carga Horária", ""),
            "descricao": campos.get("Ementa", "")[:500], "requisitos": req, "publico": campos.get("Público-alvo", ""),
            "gratis": campos.get("Curso gratuito", "").lower() == "sim",
            "certificado_existe": campos.get("Oferece Certificado de Conclusão", "").lower() == "sim",
            "fora": ("área " + _tx(cat[1]) if cat and _tx(cat[1]) in IFMG_AREAS_FORA else
                     "turma com tutoria e datas" if _TURMA.search(_tx(nome[1])) else
                     "teste de entrada" if (exige_prova(req) or re.search(r"\bteste\b", req, re.I)) else "")})
    return cursos


def confere_info_ifmg(c):
    """Lê a página «Informações do curso» e confere «Gratuito : sim»; devolve a frase ou ""."""
    texto = texto_de_html(baixar(c["url"], timeout=60))
    m = re.search(r"Gratuito\s*:\s*sim", texto, re.I)
    return m.group(0) if m else ""


# ------------------------------------------------------------------ comum
FONTES = {
    "cps": {"entidade": "Centro Paula Souza (Cursos livres MOOC, Governo de SP)", "origem": "mooc_cps",
            "nome": "MOOC do Centro Paula Souza",
            "como": ("1. Abra a página do curso e clique em \"Criar uma conta\" (é gratuito).\n"
                     "2. Depois de entrar, faça a inscrição no curso e estude no seu ritmo, quando quiser.\n"
                     "3. Ao terminar todas as etapas e atividades, emita o certificado na plataforma."),
            "notas": ("Curso livre on-line, sem limite de vagas e sem processo seletivo: comece quando quiser. "
                      "Ao concluir, a plataforma dá um certificado com carga horária estimada; as páginas oficiais não "
                      "dizem se tem custo.")},
    "ifmg": {"entidade": "IFMG (Plataforma +IFMG, Instituto Federal de Minas Gerais)", "origem": "mais_ifmg",
             "nome": "Plataforma +IFMG",
             "como": ("1. Abra a página do curso na Plataforma +IFMG e clique em \"Entrar/Cadastrar\" para criar a sua conta.\n"
                      "2. Faça a matrícula no curso: não há processo seletivo e pode começar logo.\n"
                      "3. Estude no seu ritmo e faça as atividades.\n"
                      "4. Ao concluir, emita o certificado de conclusão na plataforma."),
             "notas": ("Curso FIC on-line do IFMG, sem processo seletivo: começa no momento da inscrição. "
                       "O curso oferece certificado de conclusão; as páginas oficiais não dizem se tem custo.")},
}


def id_linha(chave_curso):
    return "C-" + hashlib.sha1(f"moodle|{chave_curso}".encode()).hexdigest()[:8]


def provas(fonte, c, frase_info=""):
    if fonte == "cps":
        ev = [f"gratuito: «{CPS_FRASE}» ({CPS_SITE}/; lida na página oficial, conferida por código)",
              f"situação: «Cursos disponíveis» — o curso está na lista da página inicial ({CPS_SITE}/; conferida por "
              f"código a cada leitura; curso sob demanda, sem limite de vagas)"]
        if c.get("certificado_existe"):
            ev.append(f"certificado: «{CPS_FRASE_CERT}» ({CPS_SITE}/; não diz se tem custo)")
        return " | ".join(ev)[:1500], "gratuito, situação"
    ev = [f"gratuito: «Curso gratuito: Sim» e «{frase_info}» ({c['url']}; campos oficiais do curso, conferidos por código)",
          f"situação: «{IFMG_FRASE_SEM_SELECAO}» ({IFMG_GOVBR}; carta de serviços do IFMG, lida no navegador por Claude "
          f"a 28/11/2026; o gov.br não abre a partir do GitHub) e o curso está nos «Cursos disponíveis» da plataforma "
          f"(conferido por código a cada leitura)"]
    if c.get("requisitos"):
        ev.append(f"requisitos: «Requisitos para Ingresso: {c['requisitos'][:250]}» ({c['url']})")
    return " | ".join(ev)[:1500], "gratuito, situação" + (", requisitos" if c.get("requisitos") else "")


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    cfg = carregar_config(base) if base else None
    hoje = hoje_iso()
    lidos = {}
    for fonte, ler in (("cps", ler_cps), ("ifmg", ler_ifmg)):
        try:
            if fonte == "cps":
                ok, cursos = ler()
                if not ok:
                    print("  ! MOOC CPS: a frase da gratuidade não foi encontrada; nada muda.")
                    if base:
                        registar_pendencia(base, "MOOC do Centro Paula Souza: a frase «sem custo» saiu da página inicial; nada mudou.",
                                           "Se os cursos continuam gratuitos e se a plataforma mudou de endereço.", CPS_SITE,
                                           origem="moodle_abertos.py")
                    continue
            else:
                cursos = ler()
            if not cursos:
                raise ValueError("lista de cursos vazia")
            lidos[fonte] = cursos
            print(f"{FONTES[fonte]['nome']}: {len(cursos)} cursos na lista; gratuitos: {sum(c['gratis'] for c in cursos)}; "
                  f"fora pelas regras: {sum(bool(c.get('fora')) for c in cursos)}.")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {FONTES[fonte]['nome']}: {e}")
            if base:
                registar_pendencia(base, f"{FONTES[fonte]['nome']}: a plataforma não abriu ou a lista de cursos não foi lida.",
                                   "Se a plataforma abre no seu navegador e se mudou de endereço.",
                                   CPS_SITE if fonte == "cps" else IFMG_SITE, origem="moodle_abertos.py")
    if seco:
        for fonte, cursos in lidos.items():
            for c in cursos[:200]:
                print(f"  · {fonte} {c['id']} | {c['titulo'][:60]} | {c['area']} | {c['horas']} | grátis={c['gratis']} | "
                      f"fora={c.get('fora', '')}")
        return 0
    linhas = base.tabela("Cursos")
    por_id = {r.get("ID"): r for r in linhas}
    titulos_online = {normal(r.get("Título")) for r in linhas
                      if r.get("Modalidade") == "online" and r.get("Estado") == "Publicado"
                      and r.get("Origem") not in ("mooc_cps", "mais_ifmg")}
    estado = ler_json(ESTADO, {"avaliados": {}})
    alteracoes, historico, publicados, custo = [], [], [], 0.0
    for fonte, cursos in lidos.items():
        cfgf = FONTES[fonte]
        atuais = {id_linha(c["chave"]): c for c in cursos if c["gratis"]}
        # 1. cursos já na planilha: continuam na lista (e gratuitos)?
        for r in linhas:
            if r.get("Origem") != cfgf["origem"] or r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
                continue
            situacao = "Aberto" if r.get("ID") in atuais else "Encerrado"
            if situacao != r.get("Situação das inscrições"):
                alteracoes.append((r["_linha"], {"Situação das inscrições": situacao, "Última verificação": hoje}))
                print(f"  = {r.get('Título', '')[:60]} | {situacao}")
        # 2. cursos novos: o Claude escolhe os úteis
        novos = [c for k, c in atuais.items() if k not in por_id and k not in estado["avaliados"]
                 and not c.get("fora") and normal(c["titulo"]) not in titulos_online]
        if not novos:
            continue
        escolha = {}
        for ini in range(0, len(novos), 80):
            lote = novos[ini:ini + 80]
            lista = "\n".join(f"{i} | {c['titulo'][:110]} | {c['area']} | {c['horas']}h | {c['descricao'][:150]} | "
                              f"Público: {c['publico'][:110]} | Requisitos: {c['requisitos'][:110]}"
                              for i, c in enumerate(lote, 1))
            texto, uso = claude(cfg["modelo_cursos"], SISTEMA,
                                f"Instituição: {cfgf['entidade']}.\nNecessidades (id = o que é): {necessidades_para_claude()}.\n\n"
                                f"Cursos (número | título | área | horas | ementa | público | requisitos):\n{lista}", max_tokens=6000)
            custo += custo_estimado(uso, cfg["modelo_cursos"])
            for x in (extrair_json(texto) or []):
                if isinstance(x, dict) and str(x.get("n", "")).isdigit() and 1 <= int(x["n"]) <= len(lote):
                    escolha[ini + int(x["n"]) - 1] = x
        print(f"{cfgf['nome']}: {len(novos)} cursos novos; o Claude escolheu {len(escolha)}.")
        for k, c in enumerate(novos):
            estado["avaliados"][id_linha(c["chave"])] = f"{hoje} {c['titulo'][:80]}"
            x = escolha.get(k)
            if not x:
                continue
            frase_info = ""
            if fonte == "ifmg":
                try:
                    frase_info = confere_info_ifmg(c)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! info {c['id']}: {e}")
                if not frase_info:
                    estado["avaliados"].pop(id_linha(c["chave"]), None)  # volta a tentar amanhã
                    continue
            evid, comp = provas(fonte, c, frase_info)
            nec = [n for n in (x.get("necessidades") or []) if n in NECESSIDADES]
            horas = re.search(r"\d+", c.get("horas") or "")
            linha = {
                "ID": id_linha(c["chave"]), "Estado": "Publicado", "Título": c["titulo"][:200], "Entidade": cfgf["entidade"],
                "Link": c["url"], "Local": "online", "Modalidade": "online", "País": "BR", "Região": "", "Cidade": "",
                "Descrição": c["descricao"], "Origem da descrição": DESCRICAO_PAGINA if c["descricao"] else "",
                "Necessidades": ", ".join(nec), "Perfis": "todos", "Condição de acesso": "",
                "Requisitos": c.get("requisitos", "")[:300], "Certificado": "desconhecido",
                "Inscrições até": "", "Início": "", "Duração": f"{horas.group(0)} horas" if horas else "",
                "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": cfgf["origem"],
                "Notas": cfgf["notas"], "Como me inscrever": cfgf["como"], **VERIFICACAO_INICIAL,
                "Nota da verificação": f"{hoje}: publicado automaticamente: curso da {cfgf['nome']}; gratuidade e lista de "
                                       f"cursos disponíveis conferidas por código.",
                "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid,
                "Campos comprovados": comp, "Página do curso": c["url"]}
            publicados.append(linha)
            historico.append(registo_historico(linha, f"Catálogo {cfgf['nome']}", "Publicado", linha, c["url"]))
            print(f"  + {c['titulo'][:60]} | {c['horas']} | {', '.join(nec)}")
    gravar_json(ESTADO, estado)
    base.atualizar("Cursos", alteracoes)
    if publicados:
        base.acrescentar("Cursos", publicados)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Plataformas Moodle: {len(alteracoes)} cursos atualizados, {len(publicados)} novos publicados. "
          f"Custo estimado: {custo:.3f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
