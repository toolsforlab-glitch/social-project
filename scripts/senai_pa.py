"""Cursos gratuitos do SENAI Pará (Gratuidade Regimental), lidos das páginas oficiais das unidades, sem Claude
(24/11/2026).

O SENAI Pará publica um «Edital Unificado» do ano (em novembro de 2026, o GEEP nº 06-2026, aberto desde 26/08) com
inscrições contínuas («durante todo o período de matrículas») e sem datas por turma. A página
https://www.senaipa.org.br/cursos-gratuitos («Cursos Gratuitos») liga às páginas das unidades (Altamira, Belém –
CEDAM, Belém – Getúlio Vargas, Bragança, Canaã dos Carajás, Castanhal, Juruti, Marabá, Paragominas, Santarém e a
Escola Digital); cada página de unidade tem o título «Cursos Gratuitos» e um botão por curso com vagas («Pintor de
Obras ( Manhã)»), que leva à inscrição. Abre a partir do GitHub.

Por isso estes cursos são tratados como cursos sob demanda (como a FGV): um curso fica «Aberto» enquanto aparecer
na página da sua unidade e passa a «Encerrado» quando sair. Provas, conferidas por código a cada leitura:
- gratuidade: o título «Cursos Gratuitos» da página oficial da unidade, que lista o curso;
- vagas por ordem de inscrição e renda (até 1,5 salário mínimo por pessoa): frases do edital unificado;
- documentos pedidos: frase do edital unificado.
"""
import hashlib
import os
import html as _html
import re
import sys
import urllib.parse

from base import (HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, hoje_iso,
                  registar_pendencia, registo_historico, texto_de_html)
from comum import baixar
from turmas import necessidades

SITE = "https://www.senaipa.org.br"
LISTA = SITE + "/cursos-gratuitos"
ENTIDADE = "SENAI Pará (Gratuidade Regimental)"
FRASE_ORDEM = "A seleção será feita por ordem de inscrição"
FRASE_RENDA = "declara-se integrante de família com renda mensal per capita de no máximo 1,5 salários-mínimos federal"
RENDA = "Renda familiar de até 1,5 salário mínimo por pessoa"
CIDADES = {"altamira": "Altamira", "belem": "Belém", "braganca": "Bragança", "canaa": "Canaã dos Carajás",
           "castanhal": "Castanhal", "juruti": "Juruti", "maraba": "Marabá", "paragominas": "Paragominas",
           "santarem": "Santarém"}


def sem_acentos(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def cidade_da_unidade(slug):
    s = sem_acentos(urllib.parse.unquote(slug))
    return next((nome for chave, nome in CIDADES.items() if chave in s), "")


def nome_e_turno(rotulo):
    """«Pintor de Obras ( Manhã) » -> («Pintor de Obras», «manhã»); «Excel ( EAD)» -> («Excel», «EAD»)."""
    r = re.sub(r"\s+", " ", _html.unescape(rotulo)).strip()
    m = re.match(r"(.+?)\s*\(\s*([^)]*?)\s*\)\s*$", r)
    return (m.group(1).strip(" -–"), m.group(2).strip()) if m else (r, "")


def chave_curso(titulo, cidade):
    return "C-" + hashlib.sha1(f"senaipa|{sem_acentos(titulo)}|{sem_acentos(cidade)}".encode()).hexdigest()[:8]


def main():
    seco = bool(os.environ.get("SECO"))  # teste a seco: só lê e mostra, sem a folha
    base = None if seco else Base()
    if base:
        carregar_config(base)
    hoje = hoje_iso()
    try:
        inicial = baixar(LISTA, timeout=90).decode("utf-8", "replace")
        unidades = list(dict.fromkeys(re.findall(r'href="(https://www\.senaipa\.org\.br/escolas-1/[^"]+)"', inicial)))
        rotulos = {}
        for href, rot in re.findall(r'href="(https://www\.senaipa\.org\.br/escolas-1/[^"]+)"[^>]*>(.*?)</a>', inicial, re.S):
            r = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", rot))).strip()
            if r:
                rotulos.setdefault(href, r)
        edital = (re.search(r'href="(https://www\.senaipa\.org\.br/_files/ugd/[^"]+\.pdf)"', inicial) or [None, ""])[1]
        texto_edital = re.sub(r"\s+", " ", texto_de_html(baixar(edital, timeout=90))) if edital else ""
    except Exception as e:  # noqa: BLE001
        print(f"SENAI Pará: a página dos cursos gratuitos não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"SENAI Pará: a página dos cursos gratuitos não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador.", LISTA, origem="senai_pa.py")
        base.guardar()
        return 0
    ordem = FRASE_ORDEM if citacao_valida(FRASE_ORDEM, texto_edital) else ""
    renda = FRASE_RENDA if citacao_valida(FRASE_RENDA, texto_edital) else ""
    docs = re.search(r"1\.1 DOCUMENTOS NECESSÁRIOS: (.+?) Caso o curso exija", texto_edital)
    documentos = docs.group(1).strip(" ;") if docs else ""
    print(f"SENAI Pará: {len(unidades)} unidades; edital {'lido' if texto_edital else 'NÃO lido'}; ordem de inscrição "
          f"{'conferida' if ordem else 'não'}; renda {'conferida' if renda else 'não'}.")

    lidos = {}  # chave -> dados do curso
    for u in unidades:
        try:
            ph = baixar(u, timeout=90).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {u}: {e}")
            continue
        texto = texto_de_html(ph.encode())
        if not citacao_valida("Cursos Gratuitos", texto):
            print(f"  ! {u}: sem o título «Cursos Gratuitos»; ignorada")
            continue
        slug = u.rsplit("/", 1)[-1]
        digital = "digital" in slug
        cidade = "" if digital else cidade_da_unidade(slug)
        unidade = rotulos.get(u, "")
        # cada curso: «Nome ( Turno) Inscrição: Online|Presencial|Online e presencial … Edital Matricule-se aqui»
        corpo = texto.split("Voltar", 1)[-1]
        for seg in corpo.split("Matricule-se aqui")[:-1]:
            m = re.search(r"(.+)\(\s*([^()]{1,40}?)\s*\)\s*Inscrição:\s*(Online e presencial|Online|Presencial)", seg, re.I | re.S)
            if not m:
                continue
            nome = re.sub(r"\s+", " ", m.group(1)).strip(" -–")
            if unidade and nome.upper().startswith(unidade.upper()):
                nome = nome[len(unidade):].strip(" -–")
            nome = re.sub(r"^(?:Edital|Acesse a comunidade)\s+", "", nome).strip()
            turno, modo = m.group(2).strip(), m.group(3).lower()
            if not nome or len(nome) > 150:
                continue
            online = digital or turno.upper() == "EAD"
            k = chave_curso(nome, "online" if online else cidade)
            d = lidos.setdefault(k, {"nome": nome, "cidade": "" if online else cidade, "online": online,
                                     "turnos": [], "unidades": [], "paginas": [], "modos": []})
            if turno and turno.upper() != "EAD" and turno.lower() not in d["turnos"]:
                d["turnos"].append(turno.lower())
            if modo not in d["modos"]:
                d["modos"].append(modo)
            if unidade and unidade not in d["unidades"]:
                d["unidades"].append(unidade)
            if u not in d["paginas"]:
                d["paginas"].append(u)
    print(f"SENAI Pará: {len(lidos)} cursos diferentes nas páginas das unidades.")
    if seco:
        for d in list(lidos.values())[:60]:
            print("  ·", d["nome"], "|", d["cidade"] or "online", "|", d["turnos"], "|", d["modos"], "|", d["unidades"])
        print("  documentos:", documentos)
        return 0

    linhas = base.tabela("Cursos")
    na_folha = {r["ID"]: r for r in linhas if r.get("Origem") == "senai_pa"}
    alteracoes, novos, historico = [], [], []
    for cid, r in na_folha.items():
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        situacao = "Aberto" if cid in lidos else "Encerrado"
        if situacao != r.get("Situação das inscrições"):
            alteracoes.append((r["_linha"], {"Situação das inscrições": situacao, "Última verificação": hoje}))
            print(f"  = {r['Título'][:60]} | {situacao}")
    nota = (f"{hoje}: publicado automaticamente: curso listado na página oficial da unidade do SENAI Pará com o título "
            f"«Cursos Gratuitos» (Gratuidade Regimental; edital unificado com inscrições contínuas).")
    for cid, d in lidos.items():
        if cid in na_folha:
            continue
        pagina = d["paginas"][0]
        evid = " | ".join(x for x in [
            f"gratuito: «Cursos Gratuitos» (título da página oficial da unidade, que lista o curso: {pagina})",
            f"vagas: «{ordem}» ({edital})" if ordem else "",
            f"renda: «{renda}» ({edital})" if renda else "",
            f"situação: curso listado na página da unidade, edital com inscrições contínuas ({pagina}; curso sob demanda)",
        ] if x)
        turnos = ", ".join(d["turnos"])
        linha = {
            "ID": cid, "Estado": "Publicado", "Título": d["nome"][:200], "Entidade": ENTIDADE, "Link": pagina,
            "Local": "BR-PA", "Modalidade": "online" if d["online"] else "presencial", "País": "BR", "Região": "Pará",
            "Cidade": d["cidade"], "Descrição": "", "Origem da descrição": "",
            "Necessidades": necessidades("", d["nome"]), "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": RENDA if renda else "", "Certificado": "desconhecido", "Inscrições até": "", "Início": "",
            "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
            "Origem": "senai_pa",
            "Notas": "; ".join(x for x in [f"Unidade: {', '.join(d['unidades'])}" if d["unidades"] else "",
                                           f"turnos: {turnos}" if turnos else "",
                                           f"documentos (edital): {documentos}" if documentos else ""] if x)[:500],
            "Como me inscrever": ("1. Abra a página da unidade no site do SENAI Pará.\n"
                                  + (f"2. Clique em \"{d['nome']}\" (\"Matricule-se aqui\") e faça a inscrição pela internet.\n"
                                     if d["modos"] == ["online"] else
                                     "2. A inscrição é presencial na unidade (o endereço está na página da unidade).\n"
                                     if d["modos"] == ["presencial"] else
                                     f"2. Inscreva-se pela internet (\"Matricule-se aqui\") ou na unidade.\n")
                                  + (f"3. Tenha à mão: {documentos}.\n" if documentos else "")
                                  + ("4. As vagas são preenchidas por ordem de inscrição: inscreva-se cedo." if ordem else "")).strip(),
            **VERIFICACAO_INICIAL, "Nota da verificação": nota,
            "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE", "Evidência": evid[:1500],
            "Campos comprovados": ", ".join(x for x in ["gratuito", "situação", "renda" if renda else ""] if x),
            "Página do curso": pagina, "Renda máxima": RENDA if renda else "",
        }
        novos.append(linha)
        historico.append(registo_historico(linha, "Catálogo SENAI Pará", "Publicado", linha, pagina))
        print(f"  + {d['nome'][:50]} | {d['cidade'] or 'online'} | {turnos}")
    base.atualizar("Cursos", alteracoes)
    if novos:
        base.acrescentar("Cursos", novos)
    if historico:
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"SENAI Pará: {len(alteracoes)} cursos atualizados, {len(novos)} novos publicados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
