"""Turmas presenciais do Qualifica Recife (Prefeitura do Recife, Secretaria de Trabalho e Qualificação Profissional),
lidas da lista pública da plataforma GO Recife, sem Claude (23/11/2026).

A plataforma https://gorecife.recife.pe.gov.br/cursos mostra os cursos das escolas profissionalizantes do Recife. A página
carrega-os de https://gorecife.recife.pe.gov.br/api/cursos (JSON público, paginado): nome, vagas, prazo de inscrição
(«registration_deadline»), datas e horário, carga horária, idade mínima e a escola (bairro e morada). Entram só os
PRESENCIAIS com prazo de inscrição. A inscrição é feita na plataforma (conta do Conecta Recife) ou na própria escola.

Regras (as mesmas das outras fontes de turmas):
- situação: Aberta até ao prazo de inscrição; depois Encerrada; turma que sai da lista fica Encerrada;
- gratuidade: só com a frase do próprio portal, conferida por código a cada leitura (FRASE_GRATUIDADE);
- AUDITORIA antes de publicar: nome, datas válidas e coerentes, horário com sentido, escola indicada.
"""
import datetime
import json
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://gorecife.recife.pe.gov.br"
PAGINA = SITE + "/cursos"
API = SITE + "/api/cursos"
ENTIDADE = "Prefeitura do Recife – Qualifica Recife (GO Recife)"
FRASE_GRATUIDADE = "Todo serviço do portal é público e sem custo"


def json_de(url):
    return json.loads(baixar(url, timeout=40).decode("utf-8", "replace"))


def texto_do_site():
    """O portal é montado por JavaScript: os textos (como a frase da gratuidade) estão no ficheiro .js do próprio site."""
    html = baixar(PAGINA, timeout=40).decode("utf-8", "replace")
    textos = [html]
    for js in re.findall(r'src="(/assets/[^"]+\.js)"', html)[:4]:
        try:
            textos.append(baixar(SITE + js, timeout=60).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            pass
    texto = "\n".join(textos)
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), texto)


def iso(v):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(v or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def hora(v):
    m = re.match(r"(\d{1,2}):(\d{2})", str(v or ""))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def titulo_legivel(nome):
    nome = re.sub(r"\s+", " ", nome or "").strip()
    if not nome.isupper():
        return nome
    pequenas = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o"}
    siglas = {"NR10", "NR35", "NR", "EPI", "TI", "PDV", "IV", "III", "II", "I", "V"}
    return " ".join(p if p in siglas else (p.lower() if i and p.lower() in pequenas else p[:1] + p[1:].lower())
                    for i, p in enumerate(nome.split(" ")))


def auditar(nome, ini, fim, prazo, h_ini, h_fim, escola):
    p = []
    if not nome:
        p.append("a turma não tem nome")
    if not prazo:
        p.append("sem prazo de inscrição")
    if not ini:
        p.append("sem data de início")
    elif fim and fim < ini:
        p.append(f"a data final ({fim}) é anterior ao início ({ini})")
    if prazo and ini and prazo > ini:
        p.append(f"o fim das inscrições ({prazo}) é depois do início ({ini})")
    if not (h_ini and h_fim) or h_ini >= h_fim or int(h_ini[:2]) < 5:
        p.append(f"o horário ({h_ini or '?'} - {h_fim or '?'}) não faz sentido")
    if not escola:
        p.append("a turma não indica a escola")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        d = json_de(API + "?page=1")
        turmas = list(d.get("results") or [])
        prox, n = d.get("next"), 1
        while prox and n < 30:
            d = json_de(prox)
            turmas += d.get("results") or []
            prox, n = d.get("next"), n + 1
    except Exception as e:  # noqa: BLE001
        print(f"GO Recife: a lista de cursos não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"GO Recife (Qualifica Recife): a lista de cursos não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador e mostra cursos.", PAGINA, origem="gorecife.py")
        return 0
    presenciais = [t for t in turmas if isinstance(t, dict) and (t.get("modality") or "").upper() == "PRESENCIAL"]
    print(f"GO Recife: {len(turmas)} cursos na lista pública; {len(presenciais)} presenciais.")

    gratuito = False
    try:
        gratuito = citacao_valida(FRASE_GRATUIDADE, texto_do_site())
    except Exception:  # noqa: BLE001
        pass
    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(PAGINA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(PAGINA)}

    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for t in presenciais:
        nome = titulo_legivel(t.get("name"))
        k = chave(nome)
        if not nome or k in ocultos:
            continue
        loc = t.get("location") or {}
        escola = re.sub(r"\s+", " ", str(loc.get("name") or "")).strip()
        morada = ", ".join(x for x in [" ".join(str(loc.get(c) or "").strip() for c in ("street", "number")).strip(),
                                       str(loc.get("neighborhood") or "").strip()] if x)
        ini, fim, prazo = iso(t.get("start_date")), iso(t.get("end_date")), iso(t.get("registration_deadline"))
        h_ini, h_fim = hora(t.get("start_time")), hora(t.get("end_time"))
        link = f"{PAGINA}#curso-{t.get('id')}"
        if link in vistos:
            continue
        vistos.add(link)
        problemas = auditar(nome, ini, fim, prazo, h_ini, h_fim, escola)
        aberto = (t.get("course_status") or "").lower() == "aberto" and t.get("is_active") is not False
        situacao = "Aberta" if aberto and prazo and hoje <= prazo else "Encerrada"
        campos = {
            "Título na fonte": str(t.get("name") or ""), "Unidade na fonte": escola, "Unidade": "", "Cidade": "Recife",
            "Link de matrícula": PAGINA, "Início": ini, "Fim": fim, "Horário": f"{h_ini} - {h_fim}" if h_ini and h_fim else "",
            "Dias": "", "Carga horária": f"{t.get('workload')} horas" if t.get("workload") else "",
            "Vagas": str(t.get("vacancies") or ""), "Prazo de inscrição": prazo,
            "Idade mínima": str(t.get("minimum_age") or ""), "Escolaridade": "", "Documentos": "",
            "Mais informações": ("Inscrição na plataforma GO Recife (com a conta do Conecta Recife) ou diretamente na escola"
                                 + (f": {escola}, {morada}." if morada else ".")),
            "Local na fonte": f"{escola} – {morada}" if morada else escola, "Modo de inscrição": "ambos", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"lista pública {API}: «{t.get('name')}», inscrições até {prazo or '?'}, aulas de {ini} a {fim}, "
                          f"{h_ini}-{h_fim}, {t.get('vacancies')} vagas, escola «{escola}»")[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (prazo, datas, horário e escola da lista oficial do GO Recife).",
        }
        ex = existentes.get(link)
        if ex:
            if problemas and ex.get("Estado") == "Publicado":
                campos["Estado"] = "Rever"
                historico.append(registo(ex, "Auditoria", "Rever", campos["Auditoria"]))
            elif not problemas and ex.get("Estado") == "Rever" and not (ex.get("Notas") or "").strip():
                campos["Estado"] = "Publicado"
            alteracoes.append((ex["_linha"], campos))
            estado_final[link] = (ex.get("Curso", ""), situacao, campos.get("Estado", ex.get("Estado")) == "Publicado")
        elif situacao == "Aberta":
            curso = cursos.get(k)
            if not curso:
                novo = {
                    "ID": id_curso(PAGINA, nome), "Estado": "Novo", "Título": nome[:200], "Entidade": ENTIDADE,
                    "Link": PAGINA, "Local": "BR-PE", "Modalidade": "presencial", "País": "BR", "Região": "Pernambuco",
                    "Cidade": "Recife", "Descrição": re.sub(r"\s+", " ", str(t.get("description") or ""))[:400],
                    "Origem da descrição": "", "Necessidades": necessidades("", nome),
                    "Perfis": "todos", "Condição de acesso": "",
                    "Requisitos": f"Ter {t.get('minimum_age')} anos ou mais" if t.get("minimum_age") else "",
                    "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
                    "Duração": f"{t.get('workload')} horas" if t.get("workload") else "", "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", "Nota da verificação": f"{hoje}: curso criado a partir de uma turma na lista oficial do GO Recife.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": (f"gratuito: «{FRASE_GRATUIDADE}» ({SITE})" if gratuito else ""),
                    "Campos comprovados": "gratuito, internet" if gratuito else "internet",
                    "Precisa de internet": "Não",
                    "O que falta confirmar": "" if gratuito else "O portal GO Recife não confirmou que os cursos são gratuitos.",
                    "Antes de começar": "cpf",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {nome[:40]} | {escola[:30]} | inscrições até {prazo or '?'} | {situacao}"
              + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da lista oficial do GO Recife."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade confirmada no portal."
    for n in cursos_novos:
        if pode_publicar(n):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        abertas = por_curso.get(r["ID"].strip(), []).count("Aberta")
        campos = {}
        if pode_publicar(r):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
        nova = "Aberto" if abertas else "Encerrado"
        if nova != (r.get("Situação das inscrições") or ""):
            campos["Situação das inscrições"] = nova
        if abertas:
            campos["Última verificação"] = hoje
        if campos:
            alteracoes_cursos.append((r["_linha"], campos))

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nGO Recife: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados); gratuidade no portal: "
          f"{'confirmada' if gratuito else 'NÃO confirmada'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
