"""Turmas presenciais do OxeTech Lab (Governo de Alagoas, Secretaria da Ciência, Tecnologia e Inovação), lidas da
lista pública do site oficial, sem Claude.

A página https://oxetech.al.gov.br/oxetechlab mostra as turmas abertas nos laboratórios OxeTech (informática básica,
programação, etc.), com inscrição on-line no próprio site (é preciso criar conta com o CPF). A página carrega as
turmas de https://oxetech.al.gov.br/turma/disponiveis (JSON público) e os laboratórios de /laboratorio/public.
Não há página própria por turma: o botão do site leva à lista, com o nome da turma a procurar.

Regras (as mesmas das outras fontes de turmas):
- só turmas de laboratórios abertos ao público: os laboratórios «Servidores» e «Instrutores» ficam de fora (regra do
  responsável, 23/11/2026: cursos condicionados a emprego não entram);
- situação: Aberta enquanto houver prazo de inscrição (ou, sem prazo, até a véspera do início); depois Encerrada;
  turma que sai da lista fica Encerrada;
- gratuidade: só com a frase do próprio site, conferida por código a cada leitura (FRASE_GRATUIDADE);
- AUDITORIA antes de publicar: título, datas válidas e coerentes, horário com sentido, cidade conhecida.
"""
import datetime
import json
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

SITE = "https://oxetech.al.gov.br"
PAGINA = SITE + "/oxetechlab"
API_TURMAS = SITE + "/turma/disponiveis"
API_LABS = SITE + "/laboratorio/public"
ENTIDADE = "Governo de Alagoas – Secti (OxeTech Lab)"
FRASE_GRATUIDADE = "Cursos gratuitos e presenciais em espaços modernos"
LABS_FECHADOS = re.compile(r"servidor|instrutor", re.I)


def json_de(url):
    return json.loads(baixar(url, timeout=40).decode("utf-8", "replace"))


def texto_do_site():
    """Texto do site oficial (a página é montada por JavaScript: os textos estão nos ficheiros .js do próprio site)."""
    html = baixar(PAGINA, timeout=40).decode("utf-8", "replace")
    textos = [html]
    for js in re.findall(r'src="(/static/js/[^"]+\.js)"', html)[:6]:
        try:
            textos.append(baixar(SITE + js, timeout=40).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            pass
    texto = "\n".join(textos)
    # «\xe7» e «ç» dos ficheiros .js → letras
    texto = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), texto)
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), texto)


def data_iso(v):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(v or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def hora(v):
    m = re.match(r"(\d{1,2}):(\d{2})", str(v or ""))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def laboratorio_de(t, labs):
    lab = t.get("laboratorio")
    if isinstance(lab, dict):
        return lab.get("nome", ""), lab.get("municipio", "") or t.get("municipio", "")
    lid = t.get("laboratorio_id") or t.get("laboratorioId") or (lab if isinstance(lab, int) else None)
    if lid in labs:
        return labs[lid]
    return "", t.get("municipio", "") or ""


def auditar(titulo, ini, fim, prazo, h_ini, h_fim, cidade):
    p = []
    if not titulo:
        p.append("a turma não tem título")
    if not ini:
        p.append("sem data de início")
    elif fim and fim < ini:
        p.append(f"a data final ({fim}) é anterior ao início ({ini})")
    if prazo and ini and prazo > ini:
        p.append(f"o fim das inscrições ({prazo}) é depois do início ({ini})")
    if not (h_ini and h_fim) or h_ini >= h_fim or int(h_ini[:2]) < 5:
        p.append(f"o horário ({h_ini or '?'} - {h_fim or '?'}) não faz sentido")
    if not cidade:
        p.append("a turma não indica a cidade")
    return p


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        turmas = json_de(API_TURMAS)
        labs = {l.get("id"): (l.get("nome", ""), l.get("municipio", "")) for l in json_de(API_LABS) if isinstance(l, dict)}
    except Exception as e:  # noqa: BLE001
        print(f"OxeTech: a lista de turmas não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"OxeTech Lab (Alagoas): a lista de turmas não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador e mostra turmas.", PAGINA, origem="oxetech.py")
        return 0
    if not isinstance(turmas, list):
        print("OxeTech: resposta inesperada da lista de turmas. Nada alterado.")
        registar_pendencia(base, "OxeTech Lab (Alagoas): a lista de turmas mudou de formato.",
                           "Se a página mostra turmas no seu navegador (o leitor precisa de ajuste).", PAGINA,
                           origem="oxetech.py")
        return 0
    print(f"OxeTech: {len(turmas)} turmas na lista pública; {len(labs)} laboratórios.")

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
    for t in turmas:
        if not isinstance(t, dict):
            continue
        titulo = re.sub(r"\s+", " ", str(t.get("titulo") or "")).strip()
        lab_nome, cidade = laboratorio_de(t, labs)
        if LABS_FECHADOS.search(lab_nome or ""):
            continue  # turmas só para servidores ou instrutores
        k = chave(titulo)
        if not titulo or k in ocultos:
            continue
        ini, fim = data_iso(t.get("data_inicio")), data_iso(t.get("data_encerramento"))
        prazo = data_iso(t.get("data_encerramento_inscricoes"))
        h_ini, h_fim = hora(t.get("horario_inicio")), hora(t.get("horario_fim"))
        ident = f"{titulo} {cidade} {t.get('id', '')}"
        link = f"{PAGINA}#{re.sub(r'[^a-z0-9]+', '-', chave(ident)).strip('-')}"
        if link in vistos:
            continue
        vistos.add(link)
        problemas = auditar(titulo, ini, fim, prazo, h_ini, h_fim, cidade)
        limite = prazo or ((datetime.date.fromisoformat(ini) - datetime.timedelta(days=1)).isoformat() if ini else "")
        situacao = "Aberta" if limite and hoje <= limite else "Encerrada"
        dias = t.get("dias_semana")
        dias = ", ".join(map(str, dias)) if isinstance(dias, list) else str(dias or "")
        campos = {
            "Título na fonte": titulo, "Unidade na fonte": f"Laboratório OxeTech {lab_nome}".strip(), "Unidade": "",
            "Cidade": cidade, "Link de matrícula": PAGINA, "Início": ini, "Fim": fim,
            "Horário": f"{h_ini} - {h_fim}" if h_ini and h_fim else "", "Dias": dias,
            "Carga horária": str(t.get("carga_horaria") or ""), "Vagas": str(t.get("vagas") or t.get("qtd_vagas") or ""),
            "Prazo de inscrição": prazo, "Idade mínima": "", "Escolaridade": "", "Documentos": "",
            "Mais informações": "Inscrição pela internet, no site do OxeTech (é preciso criar conta com o CPF).",
            "Local na fonte": "", "Modo de inscrição": "online", "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"lista pública {API_TURMAS}: título «{titulo}», início {ini}, fim {fim}, "
                          f"inscrições até {prazo or '?'}, horário {h_ini}-{h_fim}, laboratório «{lab_nome}» ({cidade})")[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (datas, horário e cidade da lista oficial do OxeTech).",
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
                    "ID": id_curso(PAGINA, titulo), "Estado": "Novo", "Título": titulo[:200], "Entidade": ENTIDADE,
                    "Link": PAGINA, "Local": "BR-AL", "Modalidade": "presencial", "País": "BR", "Região": "Alagoas",
                    "Cidade": "", "Descrição": "", "Origem da descrição": "", "Necessidades": necessidades("", titulo),
                    "Perfis": "todos", "Condição de acesso": "", "Requisitos": "", "Certificado": "desconhecido",
                    "Inscrições até": "", "Início": "", "Duração": str(t.get("carga_horaria") or ""), "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", "Nota da verificação": f"{hoje}: curso criado a partir de uma turma na lista oficial do OxeTech Lab.",
                    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": (f"gratuito: «{FRASE_GRATUIDADE}» ({SITE})" if gratuito else ""),
                    "Campos comprovados": "gratuito, internet" if gratuito else "internet",
                    "Precisa de internet": "Não",
                    "O que falta confirmar": "" if gratuito else "O site do OxeTech não confirmou que os cursos são gratuitos.",
                    "Antes de começar": "cpf",
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if ex else '+'} {titulo[:40]} | {cidade} | {ini} | inscrições até {prazo or '?'} | {situacao}"
              + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da lista oficial do OxeTech."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade confirmada no site."
    for n in cursos_novos:
        if pode_publicar(n):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        abertas = por_curso.get(r["ID"].strip(), []).count("Aberta")
        nova = "Aberto" if abertas else "Encerrado"
        campos = {}
        if pode_publicar(r):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
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
    print(f"\nOxeTech: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados); gratuidade no site: "
          f"{'confirmada' if gratuito else 'NÃO confirmada'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
