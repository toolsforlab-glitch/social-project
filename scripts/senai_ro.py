"""SENAI Rondônia, Programa de Gratuidade Regimental (aprendizagem industrial), lido por código, sem Claude (27/11/2026).

A página «Gratuidade» do SENAI RO (portal.fiero.org.br/senai/paginas/aprendizagem-…/101, abre a partir do GitHub) liga aos
editais de cada ciclo (ex.: «SENAI GRATUIDADE 2027.1»): Aprendizagem Industrial Básica (14 a 23 anos) e Técnica (16 a 23
anos). As vagas são primeiro das indústrias (cota de aprendizes); as que sobram são abertas à comunidade, «obedecendo a
ordem cronológica de inscrição», num período do cronograma («Período de 03 a 30/11/2026 – Chamada – Comunidade …»).
Ciclos semestrais (2027.1, 2027.2…).

Regras (REGRAS.md): gratuidade, seleção e idades com frases da página («Dúvidas Frequentes»), conferidas por código a cada
leitura; datas da chamada da comunidade e do início das aulas copiadas do edital; um curso por edital (Básica, Técnica)
e por ciclo; Aberto durante a chamada, Por abrir até 60 dias antes, Encerrado depois; as vagas da comunidade são as que
sobram das indústrias (I4: fica em «O que falta confirmar»). Linhas «Revisto por pessoa» ou Oculto não mudam.
SECO=1 só mostra o diagnóstico.
"""
import datetime
import html as _html
import os
import re
import sys
import urllib.parse

from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara

PAGINA = "https://portal.fiero.org.br/senai/paginas/aprendizagem-b%EF%BF%BDsica-e-tcnica/101"
ENTIDADE = "SENAI Rondônia (Gratuidade Regimental)"
DIAS_POR_ABRIR = 60
F_GRATIS = "Sim, todos os cursos ofertados pelo Programa de Gratuidade Regimental do SENAI Rondônia são 100% gratuitos."
F_VAGAS = ("As vagas remanescentes não reservadas pelas indústrias são abertas diretamente para os candidatos da "
           "comunidade no Portal SENAI, obedecendo a ordem cronológica de inscrição.")
F_IDADE = ("Podem participar jovens com idade entre 14 e 23 anos e 11 meses (para cursos de Aprendizagem Industrial "
           "Básica) ou entre 16 e 23 anos e 11 meses (para cursos de Aprendizagem Industrial Técnica)")
F_DOCS = ("Os candidatos classificados deverão enviar cópias legíveis de: RG ou Certidão de Nascimento, CPF do aprendiz, "
          "Comprovante de Escolaridade atualizado (Declaração de Matrícula ou Histórico), Comprovante de Residência, 1 foto "
          "3x4 recente e cópia de RG e CPF do responsável legal para candidatos menores de 18 anos.")
CIDADES = ["Porto Velho", "Ariquemes", "Ji-Paraná", "Vilhena", "Cacoal", "Jaru", "Rolim de Moura"]
TIPOS = {"Básica": ("14 anos", "Jovens de 14 a 23 anos e 11 meses (sem idade máxima para pessoas com deficiência)",
                    "Ensino Fundamental a partir do 9º ano"),
         "Técnica": ("16 anos", "Jovens de 16 a 23 anos e 11 meses (sem idade máxima para pessoas com deficiência)",
                     "a partir da 2ª série do Ensino Médio")}


def iso(d, m, a):
    return f"{a}-{int(m):02d}-{int(d):02d}"


def br(d):
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d else ""


def editais(pagina_html):
    """[(url, tipo, número, ciclo)] dos editais de aprendizagem ligados na página."""
    out = []
    for href in re.findall(r'href="([^"]+\.pdf)"', pagina_html, re.I):
        nome = urllib.parse.unquote(_html.unescape(href))
        m = re.search(r"Aprendizagem Industrial (B[áa]sica|T[ée]cnica) n[ºo°]\s*(\d+)\.(\d{4}\.\d)", nome, re.I)
        if m:
            tipo = "Básica" if m.group(1).lower().startswith("b") else "Técnica"
            url = urllib.parse.quote(urllib.parse.urljoin(PAGINA, _html.unescape(href)), safe=":/%?=&~+")
            if (tipo, m.group(2), m.group(3)) not in [o[1:] for o in out]:
                out.append((url, tipo, m.group(2), m.group(3)))
    return out


def ler_edital(texto):
    m = re.search(r"Período de (\d{2}) a (\d{2})/(\d{2})/(\d{4}) [–-] Chamada [–-] Comunidade[^.:]{0,90}", texto)
    a = re.search(r"Dia: (\d{2})/(\d{2})/(\d{4}): Início das aulas", texto)
    mat = re.search(r"Período de (\d{2} a \d{2}/\d{2}/\d{4})(?: e de a? ?\d{2} a \d{2}/\d{2}/\d{4})?: Período para efetivação "
                    r"das matrículas dos candidatos classificados comunidade", texto)
    if not m:
        return None
    return {"ini": iso(m.group(1), m.group(3), m.group(4)), "fim": iso(m.group(2), m.group(3), m.group(4)),
            "frase": m.group(0).strip(), "aulas": iso(*a.groups()) if a else "",
            "matricula": mat.group(0) if mat else "",
            "cidades": [c for c in CIDADES if c in texto]}


def main():
    seco = bool(os.environ.get("SECO"))
    base = None if seco else Base()
    if base:
        carregar_config(base)
    hoje = hoje_ceara()
    limite = (datetime.date.fromisoformat(hoje) + datetime.timedelta(days=DIAS_POR_ABRIR)).isoformat()
    try:
        bruto = baixar(PAGINA, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"SENAI RO: a página da Gratuidade não abriu ({type(e).__name__}: {e}). Nada alterado.")
        if base:
            registar_pendencia(base, f"SENAI RO: a página da Gratuidade não abriu a partir do GitHub ({type(e).__name__}).",
                               "A tarefa diária do navegador tenta ler esta página no Chrome (regra T10).", PAGINA,
                               origem="senai_ro.py")
            base.guardar()
        return 0
    pagina_html = bruto.decode("utf-8", "replace")
    pagina = texto_de_html(bruto)
    provas = {k: citacao_valida(f, pagina) for k, f in
              (("gratuito", F_GRATIS), ("vagas", F_VAGAS), ("idade", F_IDADE), ("documentos", F_DOCS))}
    lista = editais(pagina_html)
    print(f"SENAI RO: {len(lista)} editais de aprendizagem na página; frases da página: "
          + ", ".join(f"{k} {'ok' if v else 'NÃO'}" for k, v in provas.items()))
    existentes = {} if seco else {r["ID"].strip(): r for r in base.tabela("Cursos")
                                  if r.get("ID") and (r.get("Link") or "").startswith(PAGINA)}
    novos, alteracoes, vistos = [], [], set()
    for url, tipo, numero, ciclo in lista:
        try:
            e = ler_edital(texto_de_html(baixar(url, timeout=90)))
        except Exception as ex:  # noqa: BLE001
            print(f"  ! edital {numero}/{ciclo}: {type(ex).__name__}")
            continue
        if not e:
            print(f"  - edital {tipo} {numero}/{ciclo}: sem período da chamada da comunidade (modelo mudou?)")
            continue
        titulo = f"Aprendizagem Industrial {tipo} – SENAI Rondônia (Gratuidade {ciclo})"
        ident = id_curso(PAGINA, titulo)
        vistos.add(ident)
        situacao = ("Encerrado" if e["fim"] < hoje else "Aberto" if e["ini"] <= hoje else
                    "Por abrir" if e["ini"] <= limite else "")
        problemas = [f"frase da página não encontrada: {k}" for k in ("gratuito", "vagas") if not provas[k]]
        print(f"  {'·' if ident in existentes else '+'} {titulo} | comunidade {e['ini']} a {e['fim']} | aulas {e['aulas']} "
              f"| {situacao or 'longe da abertura'} | {len(e['cidades'])} cidades" + (f" | {'; '.join(problemas)}" if problemas else ""))
        if seco or not situacao:
            continue
        if ident in existentes:
            r = existentes[ident]
            if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
                continue
            campos = {"Última verificação": hoje}
            if (r.get("Situação das inscrições") or "") != situacao:
                campos["Situação das inscrições"] = situacao
            if (r.get("Inscrições até") or "") != e["fim"]:
                campos["Inscrições até"] = e["fim"]
            alteracoes.append((r["_linha"], campos))
            continue
        if situacao == "Encerrado":
            continue
        imin, cond, esc = TIPOS[tipo]
        ev = [f"data: «{e['frase']}» ({url})"]
        comp = ["data"]
        for k, f in (("gratuito", F_GRATIS), ("vagas", F_VAGAS), ("idade", F_IDADE), ("documentos", F_DOCS)):
            if provas[k]:
                ev.append(f"{k}: «{f}» ({PAGINA})")
                comp.append(k)
        if situacao == "Por abrir":
            ev.append(f"abertura: «{e['frase']}» ({url})")
            comp.append("abertura")
        cidades = ", ".join(e["cidades"][:-1]) + (" e " + e["cidades"][-1] if len(e["cidades"]) > 1 else "".join(e["cidades"]))
        novos.append({
            "ID": ident, "Estado": "Rever" if problemas else "Publicado", "Título": titulo, "Entidade": ENTIDADE,
            "Link": PAGINA, "Página do curso": PAGINA, "Destino do link": "curso", "Local": "BR-RO", "Modalidade": "presencial",
            "País": "BR", "Região": "Rondônia", "Cidade": "",
            "Descrição": (f"Cursos de aprendizagem industrial, presenciais e gratuitos, do SENAI Rondônia (Edital {numero}/{ciclo})."
                          + (f" Turmas em {cidades}." if cidades else "")
                          + (f" As aulas começam a {br(e['aulas'])}." if e["aulas"] else "")
                          + " As vagas são primeiro para jovens indicados pelas indústrias; as que sobram ficam para a "
                            "comunidade, por ordem de inscrição."),
            "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego", "Perfis": "todos", "Condição de acesso": cond,
            "Requisitos": F_IDADE + ", que estejam cursando ou tenham concluído o nível de escolaridade exigido no edital.",
            "Certificado": "desconhecido", "Inscrições até": e["fim"], "Inscrições abrem em": e["ini"] if situacao == "Por abrir" else "",
            "Início": e["aulas"], "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
            "Origem": "edital", "Notas": f"{hoje}: criado por senai_ro.py a partir da página da Gratuidade e do edital {url}.",
            "Como me inscrever": (f"1. Entre na página «Gratuidade» do SENAI Rondônia (portal.fiero.org.br/senai), escolha a sua "
                                  f"cidade e clique em «Faça sua inscrição aqui», de {br(e['ini'])} a {br(e['fim'])}.\n"
                                  "2. Escolha só um curso: inscrições em mais de um curso podem ser canceladas.\n"
                                  "3. Acompanhe o resultado no portal do SENAI. Se for classificado, envie os documentos "
                                  "pedidos e faça a matrícula no prazo do edital."),
            "Nota da verificação": f"{hoje}: página e edital lidos por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": situacao, "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": ", ".join(comp), "Mudança a rever": "FALSE",
            "O que falta confirmar": "; ".join(problemas + ["As vagas da comunidade são as que as indústrias não reservarem; "
                                                            "a página não diz quantas sobram em cada turma."]),
            "Idade mínima": imin, "Idade máxima": "23 anos", "Escolaridade mínima": esc, "Precisa de internet": "Sim",
        })
    if not seco:
        for ident, r in existentes.items():
            if ident in vistos or r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
                continue
            if (r.get("Inscrições até") or "9999") < hoje and r.get("Situação das inscrições") != "Encerrado":
                alteracoes.append((r["_linha"], {"Situação das inscrições": "Encerrado", "Última verificação": hoje}))
        base.atualizar("Cursos", alteracoes)
        base.acrescentar("Cursos", novos)
        base.guardar()
    print(f"\nSENAI RO: {len(novos)} cursos novos, {len(alteracoes)} atualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
