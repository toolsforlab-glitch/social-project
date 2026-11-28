"""Turmas gratuitas do Programa Senac de Gratuidade em Santa Catarina, lidas do portal oficial, sem Claude (28/11/2026).

O portal do Senac SC (portal.sc.senac.br) tem a lista «Programa Senac de Gratuidade» com o filtro «Inscrições abertas»
(cursos/<página>/psg/abertas/todos-tipos/todas-areas/search, 24 cursos por página) e uma página por curso
(curso/<id>/psg/<nome>) com a descrição, os «Requisitos para Matrícula» e as «Turmas Disponíveis» (unidade, código da
turma, cidade, dias e horário, início, término e vagas). Abre a partir do GitHub.

Regras:
- só entram as turmas com a etiqueta «Curso Gratuito» (o próprio portal diz no código da página que a etiqueta aparece
  «quando for só PSG»); as turmas com preço ou com «Investimento PSG» ficam fora;
- inscrições abertas: o curso está na lista com o filtro «Inscrições abertas» e a turma tem vagas disponíveis e ainda
  não começou; turma que já começou ou sai da página fica Encerrada;
- a inscrição no PSG é pelo botão «Registrar Interesse» da turma (nome, e-mail e telefone) ou falando com a unidade
  (perguntas frequentes do PSG do Senac SC: «Entre em contato com o Senac da sua região, verifique a programação em
  oferta, escolha o curso, o turno e o endereço mais convenientes para você.»);
- gratuidade: a etiqueta «Curso Gratuito» da turma e a frase das perguntas frequentes oficiais («…com custo zero à
  população brasileira de baixa renda.»), conferidas por código; renda: «Possuir renda familiar per capita de até 2
  salários mínimos federais» (perguntas frequentes);
- ficam fora os cursos cujos requisitos pedem ser da área (conhecimento específico, curso técnico ou superior na
  área, registro profissional) e os integrados ao ensino médio (são escola regular, com matrícula própria).
"""
import html as _html
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim, texto_de_html
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

PORTAL = "https://portal.sc.senac.br"
LISTA = PORTAL + "/cursos/{p}/psg/abertas/todos-tipos/todas-areas/search"
FAQ = "https://www.sc.senac.br/psg/partials/faq.html"
FAQ_LINK = "https://www.sc.senac.br/psg/#/perguntas-frequentes"
ENTIDADE = "Senac Santa Catarina (Programa Senac de Gratuidade)"
FRASE_GRATUIDADE = ("para garantir a oferta de vagas gratuitas em cursos de educação profissional, da Formação Inicial "
                    "ao Nível Técnico, com custo zero à população brasileira de baixa renda")
FRASE_RENDA = "Possuir renda familiar per capita de até 2 salários mínimos federais"
FRASE_INSCRICAO = ("Entre em contato com o Senac da sua região, verifique a programação em oferta, escolha o curso, o "
                   "turno e o endereço mais convenientes para você.")
REQUISITO_RENDA = "Renda familiar de até 2 salários mínimos por pessoa"
_AREA = re.compile(r"conhecimento espec[íi]fico|registro (?:profissional|no conselho|no coren)|\bcoren\b|diploma de (?:t[ée]cnico|gradua)"
                   r"|(?:cursando|conclu[íi]do|formad[oa]|forma[çc][ãa]o)\s+(?:em\s+)?(?:curso\s+)?(?:t[ée]cnico|superior|gradua)", re.I)


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def iso(dmy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dmy or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def cursos_abertos():
    links, p, total = [], 1, None
    while True:
        b = baixar(LISTA.format(p=p), timeout=60).decode("utf-8", "replace")
        achados = re.findall(r'href="(https://portal\.sc\.senac\.br/curso/\d+/psg/[^"#?]+)"', b)
        novos = [l for l in dict.fromkeys(achados) if l not in links]
        links += novos
        m = re.search(r"Mostrando \d+ até \d+ de (\d+) registros", limpo(b))
        total = int(m.group(1)) if m else total
        if not novos or (total and len(links) >= total) or p > 40:
            return links, total
        p += 1


def ler_curso(url, tentativas=4):
    """A página às vezes vem incompleta (sem o título nem as turmas) quando se leem muitas seguidas: tenta-se de novo,
    com uma pausa, até 4 vezes (28/11/2026)."""
    import time
    for n in range(tentativas):
        b = baixar(url, timeout=60).decode("utf-8", "replace")
        if "<h1" in b and "Turmas Dispon" in b:
            break
        time.sleep(2 + 3 * n)
    t = limpo(re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S))
    titulo = limpo((re.search(r"<h1[^>]*>(.*?)</h1>", b, re.S) or [None, ""])[1]) or url.rsplit("/", 1)[-1].replace("-", " ").title()
    desc = re.search(r"O que [ée] (?:o curso|este curso)\??\s*(.+?)(?=\s+O que vou aprender\?)", t)
    if not desc:
        desc = re.search(r"Sobre o curso\s*(.+?)(?=\s+O que vou aprender\?)", t)
    # cada requisito é um elemento HTML próprio: lêem-se os textos entre etiquetas, não o texto corrido
    i_req = b.find("Requisitos para Matr")
    f_req = min([x for x in (b.find("Como serei avaliado", i_req), b.find("Turmas Dispon", i_req)) if x > 0] or [i_req + 3000])
    itens_req = [limpo(x) for x in re.findall(r">([^<>]{2,})<", b[i_req:f_req]) if limpo(x)] if i_req >= 0 else []
    horas = sum(int(h) for h in re.findall(r"(\d+) horas", t.split("Posso fazer este curso?")[0].split("O que vou aprender?")[-1]))
    turmas = []
    seg = b[b.find("Turmas Disponíveis"):] if "Turmas Disponíveis" in b else ""
    pos = [m.start() for m in re.finditer(r"Turma \d{4}\.\d+\.\d+", seg)]
    for i, ini in enumerate(pos):
        bloco_html = seg[ini:pos[i + 1] if i + 1 < len(pos) else ini + 12000]
        bt = limpo(bloco_html)
        antes = limpo(seg[:ini])
        uni = re.findall(r"((?:FACULDADE\s+)?SENAC\b[^0-9]{3,60}?)\s+\d+\s+turmas?\b", antes)
        m = re.match(r"Turma (\d{4}\.\d+\.\d+)\s+(.+?)\s+((?:Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo).+?)\s+Início (\d\d/\d\d/\d{4})\s+Término (\d\d/\d\d/\d{4})", bt)
        vagas = re.search(r"Vagas dispon[íi]veis\s+(\d+)", bt)
        turmas.append({
            "codigo": m.group(1) if m else bt[6:20], "cidade": m.group(2).strip() if m else "", "dias": m.group(3).strip()[:200] if m else "",
            "ini": iso(m.group(4)) if m else "", "fim": iso(m.group(5)) if m else "", "vagas": vagas.group(1) if vagas else "",
            "unidade": uni[-1].strip() if uni else "", "gratis": "Curso Gratuito" in bt and not re.search(r"R\$|Investimento", bt.split("Registrar Interesse")[0]),
            "interesse": "Registrar Interesse" in bt, "texto": bt[:500]})
    for i, t_ in enumerate(turmas):  # a unidade só aparece antes da 1.ª turma de cada unidade
        if not t_["unidade"] and i:
            t_["unidade"] = turmas[i - 1]["unidade"]
    return {"url": url, "titulo": titulo, "descricao": (desc.group(1).strip() if desc else "")[:500],
            "requisitos": "; ".join(itens_req)[:600], "itens_req": itens_req, "horas": horas, "turmas": turmas}


def requisitos_de(texto):
    """«Requisitos para Matrícula» vêm como lista sem separadores: parte-se nas maiúsculas que começam um item."""
    partes = re.split(r"(?<=[a-zà-ú.)])\s+(?=[A-ZÀ-Ý])", texto or "")
    return [p.strip(" .") for p in partes if p.strip(" .")]


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        links, total = cursos_abertos()
        texto_faq = texto_de_html(baixar(FAQ, timeout=60))
    except Exception as e:  # noqa: BLE001
        print(f"Senac SC: o portal não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Senac SC (PSG): o portal não abriu ({type(e).__name__}).",
                           "Se a lista de cursos do PSG abre no seu navegador.", LISTA.format(p=1), origem="senac_sc.py")
        return 0
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto_faq)
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_faq) else ""
    insc = FRASE_INSCRICAO if citacao_valida(FRASE_INSCRICAO, texto_faq) else ""
    with ThreadPoolExecutor(2) as ex:
        lidos = [r for r in ex.map(lambda u: _seguro(ler_curso, u), links) if r]
    # 28/11/2026: na 1.ª leitura algumas páginas vieram sem a lista de turmas (resposta incompleta com 6 leituras em
    # paralelo); as páginas sem turmas são lidas outra vez, uma a uma
    vazios = [i for i, r in enumerate(lidos) if not r["turmas"]]
    for i in vazios:
        r = _seguro(ler_curso, lidos[i]["url"])
        if r and r["turmas"]:
            lidos[i] = r
    print(f"  (páginas sem turmas: {len(vazios)} na 1.ª leitura, {sum(1 for r in lidos if not r['turmas'])} depois de reler)")
    print(f"Senac SC: {len(links)} cursos do PSG com «Inscrições abertas» (o portal diz {total}); {len(lidos)} lidos; "
          f"gratuidade {'conferida' if gratuito else 'NÃO conferida'}; renda {'conferida' if renda else 'não'}; "
          f"inscrição {'conferida' if insc else 'não'}.")
    if not gratuito:
        registar_pendencia(base, "Senac SC (PSG): a frase de gratuidade saiu das perguntas frequentes; as turmas novas não são publicadas.",
                           "Se o PSG continua gratuito.", FAQ_LINK, origem="senac_sc.py")
    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and "portal.sc.senac.br/curso/" in (r.get("Link") or "")]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(r.get("Link", "").strip())
        else:
            cursos.setdefault(r.get("Link", "").strip(), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if "portal.sc.senac.br/curso/" in (t.get("Link da turma") or "")}
    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    fora = []
    for c in lidos:
        if c["url"] in ocultos:
            continue
        gratis = [t for t in c["turmas"] if t["gratis"]]
        if not gratis:
            continue
        area = _AREA.search(c["requisitos"])
        if area or re.search(r"integrado ao ensino m[ée]dio", c["titulo"] + c["url"], re.I):
            fora.append(f"{c['titulo'][:50]} ({area.group(0) if area else 'integrado ao ensino médio'})")
            continue
        reqs = c["itens_req"] or requisitos_de(c["requisitos"])
        idade = next((re.search(r"(\d{2}) anos", r).group(1) for r in reqs if re.search(r"[Ii]dade.*?\d{2} anos", r)), "")
        esc = next((r for r in reqs if re.search(r"Ensino (Fundamental|M[ée]dio)|escolaridade", r, re.I) and "Histórico" not in r), "")
        docs = [r for r in reqs if r not in (esc,) and not re.search(r"[Ii]dade", r)]
        for t in gratis:
            link = f"{c['url']}#turma-{t['codigo']}"
            if link in vistos:
                continue
            vistos.add(link)
            problemas = []
            if not t["ini"]:
                problemas.append("a turma não tem data de início")
            if not t["cidade"]:
                problemas.append("a turma não diz a cidade")
            if t["fim"] and t["ini"] and t["fim"] < t["ini"]:
                problemas.append("o término é antes do início")
            if t["ini"] and t["ini"] <= hoje:
                situacao = "Encerrada"  # a turma já começou
            elif t["vagas"] and int(t["vagas"]) > 0:
                situacao = "Aberta"
            else:
                situacao = "Encerrada"
            campos = {
                "Título na fonte": c["titulo"], "Unidade na fonte": t["unidade"][:200], "Unidade": "", "Cidade": t["cidade"],
                "Link de matrícula": c["url"], "Início": t["ini"], "Fim": t["fim"], "Horário": "", "Dias": t["dias"],
                "Carga horária": f"{c['horas']} horas" if c["horas"] else "", "Vagas": t["vagas"], "Prazo de inscrição": "",
                "Idade mínima": idade, "Escolaridade": esc[:400], "Documentos": "; ".join(docs)[:400],
                "Mais informações": (f"Turma {t['codigo']} ({t['unidade'].title()}): {t['dias']}. Inscrição pelo botão «Registrar "
                                     f"Interesse» da turma, na página do curso, ou falando com a unidade."),
                "Local na fonte": t["unidade"][:200], "Modo de inscrição": "online", "Situação": situacao,
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": (f"página do curso ({c['url']}): «{t['texto'][:350]}» | lista do PSG com o filtro «Inscrições abertas» "
                              f"({LISTA.format(p=1)})")[:1500],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
                f"{hoje}: ok (turma com a etiqueta «Curso Gratuito», datas e vagas da página oficial do Senac SC).",
            }
            ex_t = existentes.get(link)
            if ex_t:
                if problemas and ex_t.get("Estado") == "Publicado":
                    campos["Estado"] = "Rever"
                    historico.append(registo(ex_t, "Auditoria", "Rever", campos["Auditoria"]))
                elif not problemas and ex_t.get("Estado") == "Rever" and not (ex_t.get("Notas") or "").strip():
                    campos["Estado"] = "Publicado"
                alteracoes.append((ex_t["_linha"], campos))
                estado_final[link] = (ex_t.get("Curso", ""), situacao, campos.get("Estado", ex_t.get("Estado")) == "Publicado")
            elif situacao == "Aberta":
                curso = cursos.get(c["url"])
                if not curso:
                    ev = [f"gratuito: «Curso Gratuito» (etiqueta da turma {t['codigo']}, {c['url']}) e «{FRASE_GRATUIDADE}» ({FAQ_LINK})" if gratuito else "",
                          f"renda: «{renda}» ({FAQ_LINK})" if renda else "",
                          f"inscrição: «{insc}» ({FAQ_LINK}); botão «Registrar Interesse» da turma" if insc else ""]
                    novo = {
                        "ID": id_curso(c["url"], c["titulo"]), "Estado": "Novo", "Título": c["titulo"][:200], "Entidade": ENTIDADE,
                        "Link": c["url"], "Local": "BR-SC", "Modalidade": "online" if re.search(r"\bEAD\b|dist[âa]ncia", c["titulo"] + t["unidade"], re.I) else "presencial",
                        "País": "BR", "Região": "Santa Catarina", "Cidade": "", "Descrição": c["descricao"],
                        "Origem da descrição": "página oficial do curso" if c["descricao"] else "",
                        "Necessidades": necessidades("", c["titulo"]), "Perfis": "todos", "Condição de acesso": "",
                        "Requisitos": "\n".join([REQUISITO_RENDA] if renda else []), "Certificado": "desconhecido",
                        "Inscrições até": "", "Início": "", "Duração": f"{c['horas']} horas" if c["horas"] else "",
                        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                        "Como me inscrever": ("1. Abra a página do curso no portal do Senac SC e desça até «Turmas Disponíveis».\n"
                                              "2. Escolha uma turma com a etiqueta «Curso Gratuito».\n"
                                              "3. Clique em \"Registrar Interesse\" e deixe o seu nome, e-mail e telefone (ou fale com a unidade).\n"
                                              "4. A unidade entra em contacto: leve os documentos pedidos e a comprovação de renda para a matrícula."),
                        "Nota da verificação": f"{hoje}: curso criado a partir de uma turma gratuita do portal do Senac SC.",
                        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                        "Evidência": " | ".join(x for x in ev if x)[:1500],
                        "Campos comprovados": ", ".join(x for x in ["gratuito" if gratuito else "", "renda" if renda else ""] if x),
                        "Renda máxima": REQUISITO_RENDA if renda else "",
                        "O que falta confirmar": "" if gratuito else "A página oficial não diz que o curso é gratuito.",
                    }
                    cursos_novos.append(novo)
                    curso = cursos[c["url"]] = novo["ID"]
                novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                              "Link da turma": link, "Primeiro visto": hoje, **campos})
                estado_final[link] = (curso, situacao, not problemas)
            print(f"  {'·' if ex_t else '+'} {c['titulo'][:45]} | {t['cidade']} | início {t['ini']} | {t['vagas']} vagas | {situacao}"
                  + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))
    for f in fora:
        print("  - fora:", f)
    if any("onhecimento espec" in f for f in fora):
        registar_pendencia(base, "Senac SC (PSG): cursos gratuitos que pedem «Comprovante de Conhecimento Específico» ficam fora do site "
                                 "até se saber o que vale como comprovante (se basta uma autodeclaração ou um certificado de qualquer curso, como no Senac-RS, podem entrar).",
                           "O que o Senac SC aceita como «Comprovante de Conhecimento Específico» (perguntar à unidade ou ver o regulamento do PSG).",
                           LISTA.format(p=1), origem="senac_sc.py")
    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu das turmas gratuitas com inscrições abertas do portal do Senac SC."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)
    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), []) and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma gratuita aberta aprovada na auditoria (portal oficial do Senac SC)."
    for n in cursos_novos:
        if pode_publicar(n):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        n_abertas = por_curso.get(r["ID"].strip(), []).count("Aberta")
        campos = {}
        if pode_publicar(r):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
        nova = "Aberto" if n_abertas else "Encerrado"
        if nova != (r.get("Situação das inscrições") or ""):
            campos["Situação das inscrições"] = nova
        if n_abertas:
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
    print(f"\nSenac SC: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados); {len(fora)} cursos fora pelas regras.")
    return 0


def _seguro(f, u):
    try:
        return f(u)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {u}: {e}")
        return None


if __name__ == "__main__":
    sys.exit(main())
