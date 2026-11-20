"""Turmas da Rede CVT (Instituto Centec), lidas da página oficial, sem Claude.

A página "Cursos de formação inicial e continuada" do Centec mostra duas listas, carregadas por pedido ao
próprio site: cursos com inscrições on-line (aulas ao vivo no Centec Academy, com link de inscrição) e cursos
com inscrições presenciais (inscrição no local indicado, com telefone). Não há página por curso nem prazo de
inscrição. Este script segue as mesmas regras de turmas.py:

- cada turma é copiada do cartão da página (curso, unidade, horário, datas, vagas, requisito, local, telefone);
- situação: Aberta enquanto a turma estiver na lista oficial e ainda não tiver começado; depois Encerrada;
- AUDITORIA antes de publicar: o cartão diz as datas e o horário duas vezes (no título ou na legenda da imagem
  e nos campos próprios) e as duas têm de coincidir; as datas e o horário têm de fazer sentido; a unidade tem
  de estar na folha. Quem falha fica em Rever, com o motivo na coluna Auditoria;
- o cartão não diz o ano: usa-se o ano escrito no título, ou, se não houver, o ano em que a data fica mais
  perto de hoje (fica dito na Evidência);
- cursos novos entram em Cursos (um por título e modalidade) e são publicados quando têm turma aprovada e a
  página confirma, letra a letra, que os cursos são gratuitos.
"""
import datetime
import html
import re
import sys
import time
import urllib.parse
import urllib.request

from base import DESCRICAO_PAGINA, DESCRICAO_RESUMO, HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, sim, texto_de_html
from comum import AGENTE, baixar
from turmas import (ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, limpo, mapa_unidades,
                    necessidades, registo)

PAGINA = "https://www.centec.org.br/cursos-formacao-inicial-continuada/"
AJAX = "https://www.centec.org.br/wp-admin/admin-ajax.php"
ENTIDADE = "Instituto Centec (Rede CVT)"
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "ao", "à", "às", "no", "na", "nos", "nas", "para", "com"}
SIGLAS = {"IA": "IA", "TI": "TI", "RH": "RH", "NR": "NR", "CHATGPT": "ChatGPT", "EAD": "EAD"}
REGRAS = [  # (frase exata da página, coluna, valor, nome em Campos comprovados)
    ("Estes cursos são ofertados gratuitamente", None, None, "gratuito"),
    ("basta ter idade a partir de 16 anos", "Idade mínima", "16", "idade"),
    ("Cópia do RG e CPF Comprovante de residência", "Documentos pedidos",
     "Cópia do RG e CPF; comprovante de residência; declaração de escolaridade (se necessário)", "documentos"),
]
FRASE_DESCRICAO = "destinados à qualificação profissional"


def pedir(dados):
    corpo = urllib.parse.urlencode(dados).encode()
    req = urllib.request.Request(AJAX, data=corpo, headers={
        "User-Agent": AGENTE, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest", "Referer": PAGINA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def titulo_legivel(t):
    palavras = []
    for i, p in enumerate(limpo(t).split()):
        if p.upper() in SIGLAS:
            palavras.append(SIGLAS[p.upper()])
        elif i and p.lower() in MINUSCULAS:
            palavras.append(p.lower())
        else:
            palavras.append(p[:1].upper() + p[1:].lower())
    return " ".join(palavras)


def campo(bloco, classe):
    m = re.search(r'(?s)<div class="%s">(.*?)</div>' % classe, bloco)
    return limpo(re.sub(r"(?s)<svg.*?</svg>", " ", m.group(1))) if m else ""


def ler_cartoes(bloco_html, online):
    cartoes = []
    for b in re.split(r'<div class="card-curso">', bloco_html)[1:]:
        h3 = re.search(r"(?s)<h3>(.*?)</h3>", b)
        if not h3:
            continue
        nome = limpo(h3.group(1))
        alt = re.search(r'alt="([^"]*)"', b)
        botao = re.search(r"(?s)<a\s([^>]*)>\s*Inscreva-se", b)
        atributos = dict(re.findall(r'([\w-]+)="([^"]*)"', botao.group(1))) if botao else {}
        partes = [p.strip() for p in re.split(r"\s+-\s+", nome)]
        i_un = next((i for i, p in enumerate(partes) if re.match(r"(CVT|CVTEC|FATEC)\b", p, re.I)), None)
        carga = re.search(r'(?s)<div class="title-card">.*?<p>(.*?)</p>', b)
        cartoes.append({
            "online": online, "nome": nome, "legenda": html.unescape(alt.group(1)) if alt else "",
            "curso": " - ".join(partes[:i_un]) if i_un else partes[0],
            "unidade": partes[i_un] if i_un is not None else "",
            "carga": limpo(carga.group(1)) if carga else "", "horario_texto": campo(b, "horario"),
            "datas": campo(b, "data"), "vagas": campo(b, "vagas"), "requisito": campo(b, "requisito"),
            "local": html.unescape(atributos.get("data-localidade", "")).strip(),
            "telefone": html.unescape(atributos.get("data-telefone", "")).strip(),
            "link": html.unescape(atributos.get("href", "")).strip(),
        })
    return cartoes


def dia_mes(t):
    return [(int(d), int(m)) for d, m in re.findall(r"(\d{1,2})/(\d{1,2})", t or "")]


def resolver_datas(c, hoje):
    """Datas ISO do cartão. O ano vem do título/legenda; sem ano, o mais perto de hoje."""
    dm = dia_mes(c["datas"])
    if len(dm) < 2:
        return "", "", ""
    hoje_d = datetime.date.fromisoformat(hoje)
    m = re.search(r"\d{1,2}/\d{1,2}/(\d{4}|\d{2})\b", c["nome"] + " " + c["legenda"])
    if m:
        ano, origem = int(m.group(1)) + (2000 if len(m.group(1)) == 2 else 0), "ano escrito no título"
    else:
        ano = min((hoje_d.year - 1, hoje_d.year, hoje_d.year + 1),
                  key=lambda a: abs((datetime.date(a, dm[0][1], min(dm[0][0], 28)) - hoje_d).days))
        origem = "ano não indicado: usado o mais perto de hoje"
    try:
        ini = datetime.date(ano if not m or dm[0][1] <= dm[1][1] else ano - 1, dm[0][1], dm[0][0])
        fim = datetime.date(ini.year + (1 if dm[1][1] < dm[0][1] else 0), dm[1][1], dm[1][0])
    except ValueError:
        return "", "", ""
    return ini.isoformat(), fim.isoformat(), origem


def horas(t):
    m = re.search(r"(\d{1,2}):(\d{2})\s*às\s*(\d{1,2}):(\d{2})", t or "")
    return (f"{int(m.group(1)):02d}:{m.group(2)} - {int(m.group(3)):02d}:{m.group(4)}") if m else ""


def auditar(c, ini, fim, unidade_id):
    problemas = []
    outra = c["nome"] + " | " + c["legenda"]  # segunda vez em que o cartão diz datas e horas
    dm2 = dia_mes(re.sub(r"^.*?(?=\d{1,2}/\d{1,2})", "", outra, count=1))
    if len(dm2) >= 2 and dm2[:2] != dia_mes(c["datas"])[:2]:
        problemas.append(f"as datas do título ({dm2[0][0]:02d}/{dm2[0][1]:02d} a {dm2[1][0]:02d}/{dm2[1][1]:02d}) "
                         f"não coincidem com as do campo próprio ({c['datas']})")
    h2 = re.search(r"(\d{1,2})h(?:\d{2})?\s*às\s*(\d{1,2})h", outra)
    h1 = re.search(r"(\d{1,2}):\d{2}\s*às\s*(\d{1,2}):\d{2}", c["horario_texto"])
    if h1 and h2 and (int(h1.group(1)), int(h1.group(2))) != (int(h2.group(1)), int(h2.group(2))):
        problemas.append(f"o horário do título ({h2.group(0)}) não coincide com o do campo próprio ({c['horario_texto']})")
    if not ini:
        problemas.append("o cartão não tem datas legíveis")
    elif fim < ini:
        problemas.append(f"a data final ({fim}) é anterior ao início ({ini})")
    if not h1 or int(h1.group(1)) < 5 or int(h1.group(1)) >= int(h1.group(2)):
        problemas.append(f"o horário ({c['horario_texto'] or 'vazio'}) não faz sentido")
    if not c["unidade"]:
        problemas.append("o cartão não indica a unidade")
    elif not unidade_id:
        problemas.append(f"a unidade {c['unidade']} não está no separador Organizações")
    if c["online"] and not c["link"].startswith("https://academy.centec.org.br/"):
        problemas.append("o botão de inscrição não leva ao Centec Academy")
    if not c["online"] and not c["local"]:
        problemas.append("o cartão não indica o local de inscrição")
    return problemas


def regras_da_pagina(texto):
    campos, provados, frases = {}, [], []
    for frase, coluna, valor, nome in REGRAS:
        if citacao_valida(frase, texto):
            provados.append(nome)
            frases.append(f"«{frase}»")
            if coluna:
                campos[coluna] = valor
    return campos, provados, frases


def curso_novo(c, link_curso, hoje, regras, descricao_ok):
    campos, provados, frases = regras
    titulo = titulo_legivel(c["curso"])
    return {
        "ID": id_curso(link_curso, titulo), "Estado": "Novo", "Título": titulo[:200], "Entidade": ENTIDADE,
        "Link": link_curso, "Local": "BR-CE", "Modalidade": "online" if c["online"] else "presencial", "País": "BR",
        "Região": "Ceará", "Cidade": "",
        "Descrição": (f"Curso de qualificação profissional da Rede CVT, com {c['carga']}." if descricao_ok and c["carga"] else ""),
        "Origem da descrição": DESCRICAO_RESUMO if descricao_ok and c["carga"] else "",
        "Necessidades": necessidades("", titulo), "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter 16 anos ou mais" if "idade" in provados else "", "Certificado": "desconhecido",
        "Inscrições até": "", "Início": "", "Duração": c["carga"], "Link verificado": "SIM", "Primeiro visto": hoje,
        "Última verificação": hoje, "Origem": "turmas", "Notas": "", "Como me inscrever": "",
        "Nota da verificação": f"{hoje}: curso criado a partir de uma turma na lista oficial do Centec.",
        **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(frases)[:1500], "Campos comprovados": ", ".join(provados + ["internet"]),
        "Precisa de internet": "Sim" if c["online"] else "Não",
        "O que falta confirmar": "" if "gratuito" in provados else "A página do Centec não confirmou que os cursos são gratuitos.",
        "Antes de começar": "cpf" if "documentos" in provados else "", **campos,
    }


def main(pedir_pagina=pedir, ler_pagina=None):
    ler_pagina = ler_pagina or (lambda u: baixar(u, timeout=40).decode("utf-8", "replace"))
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        texto_pagina = texto_de_html(ler_pagina(PAGINA))
        cartoes = ler_cartoes(pedir_pagina({"action": "filtrar_cursos_online", "unidade": "", "turno": "", "busca": ""}), True)
        n_online, pagina = len(cartoes), 1
        while pagina <= 40:
            bloco = pedir_pagina({"action": "carregar_cursos_presenciais", "pagina": pagina})
            novos = ler_cartoes(bloco, False)
            if not novos:
                break
            cartoes += novos
            pagina += 1
            time.sleep(0.5)
    except Exception as e:  # noqa: BLE001
        print(f"Centec: a página não abriu ({type(e).__name__}: {e}). Nada foi alterado.")
        return 0
    print(f"Centec: {n_online} turmas on-line e {len(cartoes) - n_online} presenciais na lista oficial.")
    if not cartoes:
        print("Lista vazia: nada foi alterado (pode ser uma falha da página).")
        return 0

    regras = regras_da_pagina(texto_pagina)
    descricao_ok = citacao_valida(FRASE_DESCRICAO, texto_pagina)
    unidades = mapa_unidades(base)
    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(PAGINA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        k = (chave(r.get("Título", "")), r.get("Modalidade") == "online")
        if r.get("Estado") == "Oculto":
            ocultos.add(k)
        else:
            cursos.setdefault(k, r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(("https://academy.centec.org.br/", PAGINA))}

    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for c in cartoes:
        k = (chave(titulo_legivel(c["curso"])), c["online"])
        if k in ocultos:
            continue
        ini, fim, origem_ano = resolver_datas(c, hoje)
        link = c["link"] if c["online"] and c["link"] else PAGINA + "#" + re.sub(
            r"[^a-z0-9]+", "-", chave(f"{c['curso']} {c['unidade']} {ini} {horas(c['horario_texto'])}")).strip("-")
        if link in vistos:
            continue
        vistos.add(link)
        unidade_id = unidades.get(chave(c["unidade"]), "")
        problemas = auditar(c, ini, fim, unidade_id)
        situacao = "Aberta" if ini and hoje < ini else "Encerrada"
        campos = {
            "Título na fonte": c["nome"], "Unidade na fonte": c["unidade"], "Unidade": unidade_id, "Cidade": "",
            "Link de matrícula": c["link"], "Início": ini, "Fim": fim, "Horário": horas(c["horario_texto"]),
            "Dias": "", "Carga horária": c["carga"], "Vagas": c["vagas"], "Prazo de inscrição": "",
            "Idade mínima": regras[0].get("Idade mínima", ""), "Escolaridade": c["requisito"], "Documentos": "",
            "Mais informações": c["telefone"], "Local na fonte": c["local"], "Situação": situacao,
            "Última verificação": hoje, "Falhas seguidas": 0,
            "Evidência": (f"«{c['nome']}» | «{c['horario_texto']}» | «{c['datas']}» ({origem_ano}) | «{c['requisito']}»"
                          + (f" | local: «{c['local']}»" if c["local"] else ""))[:900],
            "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
            f"{hoje}: ok (datas e horário ditos duas vezes no cartão e iguais; unidade conhecida).",
        }
        t = existentes.get(link)
        if t:
            if problemas and t.get("Estado") == "Publicado":
                campos["Estado"] = "Rever"
                historico.append(registo(t, "Auditoria", "Rever", campos["Auditoria"]))
            elif not problemas and t.get("Estado") == "Rever" and "não passou" in (t.get("Auditoria") or ""):
                campos["Estado"] = "Publicado"
            alteracoes.append((t["_linha"], campos))
            estado_final[link] = (t.get("Curso", ""), situacao, campos.get("Estado", t.get("Estado")) == "Publicado")
        elif situacao == "Aberta":
            curso = cursos.get(k)
            if not curso:
                novo = curso_novo(c, PAGINA + ("#online" if c["online"] else ""), hoje, regras, descricao_ok)
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if problemas else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            estado_final[link] = (curso, situacao, not problemas)
        print(f"  {'·' if t else '+'} {c['curso'][:40]} | {c['unidade']} | {ini} | {situacao}"
              + (f" | AUDITORIA: {'; '.join(problemas)}" if problemas else ""))

    # turmas que saíram da lista oficial: encerradas
    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da lista oficial do Centec."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for curso, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(curso, []).append(sit)

    def pode_publicar(r):
        return (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and not sim(r.get("Mudança a rever"))
                and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e gratuidade confirmada na página."
    alteracoes_cursos = []
    for n in cursos_novos:
        if pode_publicar(n):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
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
            historico.append(registo({"Curso": r["ID"], "Título na fonte": r.get("Título", ""),
                                      "Situação": r.get("Situação das inscrições", "")}, "Turmas", nova,
                                     f"{abertas} turmas abertas na lista do Centec."))
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
    print(f"\nCentec: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
