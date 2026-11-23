"""Turmas presenciais do Treinar para Empregar (Prefeitura de Salvador, Semdec/SIMM), lidas da lista pública do site
do programa, sem Claude (23/11/2026).

O site https://treinarparaempregar.salvador.ba.gov.br/cursos é montado a partir de
https://treinarparaempregar.salvador.ba.gov.br/api/cursos (JSON público): uma entrada por turma, com título, modalidade,
início e fim das inscrições, vagas, datas do curso, parceiro (SENAI, Ludovica, Unifel…) e a descrição escrita pela
Semdec (local, turno, requisitos, documentos). Entram só as PRESENCIAIS; as on-line (ex.: Afreektech) ficam de fora.
A inscrição é feita no próprio site, com cadastro e envio de documentos; algumas turmas pedem ainda a entrega dos
documentos num endereço.

Regras (as mesmas das outras fontes de turmas):
- situação: «Por abrir» antes do início das inscrições; Aberta com inscrições abertas, vagas e prazo por vencer;
  senão Encerrada; turma que sai da lista fica Encerrada;
- gratuidade: só com a frase da própria turma («Curso gratuito…» ou «TURMA GRATUITA»), conferida por código;
- turma só para mulheres: o curso leva «(só para mulheres)» no título e essa condição de acesso;
- AUDITORIA antes de publicar: nome, prazo, datas coerentes, horário com sentido e local indicado.
"""
import datetime
import json
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://treinarparaempregar.salvador.ba.gov.br"
PAGINA = SITE + "/cursos"
API = SITE + "/api/cursos"
ENTIDADE = "Prefeitura de Salvador – Treinar para Empregar (Semdec/SIMM)"
GRATUIDADE = re.compile(r"[^\n]*(?:curso gratuito|turma gratuita|cursos? 100% gratuitos?)[^\n]*", re.I)
FUSO = datetime.timedelta(hours=-3)  # Salvador (America/Bahia), sem horário de verão


def dia_local(v):
    """«2026-11-14T21:25:00+00:00» → «2026-11-14» na hora de Salvador; «2026-11-16» fica igual."""
    s = str(v or "").strip()
    if not s:
        return ""
    try:
        if "T" in s:
            d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
            if d.tzinfo:
                d = d.astimezone(datetime.timezone(FUSO))
            return d.date().isoformat()
        return datetime.date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return ""


def br(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso else ""


def titulo_legivel(nome):
    nome = re.sub(r"\s+", " ", nome or "").strip()
    if not nome.isupper():
        return nome
    pequenas = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o"}
    siglas = {"WMS", "TI", "IA", "NR10", "NR35", "SENAI", "II", "III", "IV"}
    return " ".join(p if p in siglas else (p.lower() if i and p.lower() in pequenas else p[:1] + p[1:].lower())
                    for i, p in enumerate(nome.split(" ")))


def horario(desc):
    m = re.search(r"(\d{1,2})[:h](\d{2})\s*(?:H|HRS?|HORAS)?\s*(?:AS|ÀS|A|ATÉ|-)\s*(\d{1,2})[:h](\d{2})", desc, re.I)
    if not m:
        return "", ""
    return f"{int(m.group(1)):02d}:{m.group(2)}", f"{int(m.group(3)):02d}:{m.group(4)}"


def local_das_aulas(t, desc):
    for padrao in (r"Local das aulas:\s*([^\n]+)", r"aulas irão ocorrer[^:\n]*na:\s*([^\n]+)", r"Instituição(?: parceira)?:\s*([^\n]+)"):
        m = re.search(padrao, desc, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" .-")[:200]
    return re.sub(r"\s+", " ", str(t.get("location") or "")).strip()


def requisitos(desc):
    partes = []
    m = re.search(r"Idade m[ií]nima\s*:?\s*(\d{2})", desc, re.I)
    if m:
        partes.append(f"Ter {m.group(1)} anos ou mais")
    m = re.search(r"Ensino\s+(FUNDAMENTAL|M[ÉE]DIO)\s+(COMPLETO|INCOMPLETO)", desc, re.I)
    if m:
        partes.append(f"Ensino {m.group(1).capitalize()} {m.group(2).lower()}".replace("Medio", "Médio"))
    if re.search(r"CARTEIRA DE HABILITA[ÇC][ÃA]O\s*([A-E])?", desc, re.I):
        cat = re.search(r"CARTEIRA DE HABILITA[ÇC][ÃA]O\s*([A-E])\b", desc, re.I)
        partes.append("Carteira de habilitação" + (f" {cat.group(1).upper()}" if cat else ""))
    return "; ".join(partes), (m.group(1) if (m := re.search(r"Idade m[ií]nima\s*:?\s*(\d{2})", desc, re.I)) else "")


def so_mulheres(t, desc):
    return bool(t.get("women_only")) or bool(re.search(r"somente para mulheres|exclusivamente para mulheres|mulher salvador", desc, re.I))


def auditar(nome, prazo, ini, fim, h_ini, h_fim, local):
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
        p.append(f"o horário ({h_ini or '?'} - {h_fim or '?'}) não está claro na descrição")
    if not local:
        p.append("a turma não indica onde são as aulas")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        lista = json.loads(baixar(API, timeout=40).decode("utf-8", "replace"))
        if isinstance(lista, dict):
            lista = lista.get("data") or lista.get("results") or []
    except Exception as e:  # noqa: BLE001
        print(f"Treinar para Empregar: a lista de cursos não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Treinar para Empregar (Salvador): a lista de cursos não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador e mostra cursos.", PAGINA, origem="salvador_tpe.py")
        return 0
    presenciais = [t for t in lista if isinstance(t, dict) and (t.get("modality") or "").lower() == "presencial"]
    print(f"Treinar para Empregar: {len(lista)} turmas na lista pública; {len(presenciais)} presenciais.")

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
    gratis_por_curso = {}
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for t in presenciais:
        desc = str(t.get("description") or "")
        mulheres = so_mulheres(t, desc)
        nome = titulo_legivel(t.get("title")) + (" (só para mulheres)" if mulheres else "")
        k = chave(nome)
        if not t.get("title") or k in ocultos or not t.get("slug"):
            continue
        link = f"{PAGINA}/{t['slug']}"
        if link in vistos:
            continue
        vistos.add(link)
        insc_ini, prazo = dia_local(t.get("enrollment_start")), dia_local(t.get("enrollment_end"))
        ini, fim = dia_local(t.get("course_start_date")), dia_local(t.get("course_end_date"))
        h_ini, h_fim = horario(desc)
        local = local_das_aulas(t, desc)
        parceiro = (t.get("partner") or {}).get("name", "") if isinstance(t.get("partner"), dict) else str(t.get("partner") or "")
        m_gratis = GRATUIDADE.search(desc)
        frase_gratis = m_gratis.group(0).strip(" ✅") if m_gratis and citacao_valida(m_gratis.group(0).strip(" ✅"), desc) else ""
        reqs, idade = requisitos(desc)
        transporte = bool(re.search(r"(?:com|e)\s+transporte", desc, re.I)) and not re.search(r"sem transporte", desc, re.I)
        problemas = auditar(nome, prazo, ini, fim, h_ini, h_fim, local)
        status = (t.get("enrollment_status") or "").lower()
        vagas = t.get("available_vacancies")
        tem_vagas = t.get("has_vacancies") is not False and (vagas is None or int(vagas or 0) > 0)
        if prazo and hoje > prazo or status == "encerrada":
            situacao = "Encerrada"
        elif insc_ini and hoje < insc_ini:
            situacao = "Por abrir"
        elif t.get("enrollment_open") and tem_vagas and prazo:
            situacao = "Aberta"
        else:
            situacao = "Encerrada"
        campos = {
            "Título na fonte": str(t.get("title") or ""), "Unidade na fonte": local, "Unidade": "", "Cidade": "Salvador",
            "Link de matrícula": link, "Início": ini, "Fim": fim, "Horário": f"{h_ini} - {h_fim}" if h_ini and h_fim else "",
            "Dias": "", "Carga horária": re.sub(r"(?i)\s*h(oras)?$", "", str(t.get("workload") or "")).strip() + " horas" if t.get("workload") else "",
            "Vagas": str(t.get("total_vacancies") or ""), "Prazo de inscrição": prazo,
            "Idade mínima": idade, "Escolaridade": "", "Documentos": "",
            "Mais informações": (f"Inscrições de {br(insc_ini)} a {br(prazo)} no site do Treinar para Empregar, com cadastro e envio de "
                                 "documentos" + (f". Parceiro: {parceiro}" if parceiro else "") + (". Com transporte" if transporte else "") + "."),
            "Local na fonte": local, "Modo de inscrição": "online", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"lista pública {API}: «{t.get('title')}», inscrições de {insc_ini} a {prazo}, curso de {ini} a {fim or '?'}, "
                          f"{h_ini}-{h_fim}, local «{local}»" + (f", gratuito: «{frase_gratis}»" if frase_gratis else ""))[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (prazo, datas, horário e local da lista oficial do Treinar para Empregar).",
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
        elif situacao in ("Aberta", "Por abrir"):
            curso = cursos.get(k)
            if not curso:
                novo = {
                    "ID": id_curso(PAGINA, nome), "Estado": "Novo", "Título": nome[:200], "Entidade": ENTIDADE,
                    "Link": PAGINA, "Local": "BR-BA", "Modalidade": "presencial", "País": "BR", "Região": "Bahia",
                    "Cidade": "Salvador", "Descrição": re.sub(r"\s+", " ", desc)[:400],
                    "Origem da descrição": "", "Necessidades": necessidades("", nome),
                    "Perfis": "mulheres" if mulheres else "todos", "Condição de acesso": "Só para mulheres" if mulheres else "",
                    "Requisitos": reqs, "Certificado": "gratuito" if frase_gratis and "certifica" in frase_gratis.lower() else "desconhecido",
                    "Inscrições até": "", "Início": "",
                    "Duração": campos["Carga horária"], "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", "Nota da verificação": f"{hoje}: curso criado a partir de uma turma na lista oficial do Treinar para Empregar.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto" if situacao == "Aberta" else "Encerrado",
                    "Verificar automaticamente": "FALSE",
                    "Evidência": (f"gratuito: «{frase_gratis}» ({link})" if frase_gratis else ""),
                    "Campos comprovados": "gratuito, internet" if frase_gratis else "internet",
                    "Precisa de internet": "Sim",
                    "Ajuda de custo ou transporte": "Transporte (segundo a página da turma)" if transporte else "",
                    "O que falta confirmar": "" if frase_gratis else "A página da turma não diz que o curso é gratuito.",
                    "Antes de começar": "cpf",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        if frase_gratis:
            gratis_por_curso[cursos.get(k, "")] = True
        print(f"  {'·' if ex else '+'} {nome[:45]} | {local[:30]} | inscrições {insc_ini} a {prazo or '?'} | {situacao}"
              + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else "") + ("" if frase_gratis else " | SEM FRASE DE GRATUIDADE"))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da lista oficial do Treinar para Empregar."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade escrita na página da turma."
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
    print(f"\nTreinar para Empregar: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
