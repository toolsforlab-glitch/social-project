"""Cursos FIC, de extensão e ProEJA do IFRN, lidos do portal oficial de processos seletivos, sem Claude (25/11/2026).

O portal do IFRN (portal.ifrn.edu.br/processos-seletivos/buscar/) tem filtros por subtipo: «Qualificação Profissional
(FIC)», «Curso de Extensão» e «Técnico Integrado - ProEJA». Cada processo tem uma página com o texto oficial, a lista
de documentos (edital, retificações, resultados) e as etapas com datas («13/07 às 0h a 20/07 às 23:59 Inscrições»).
Em 2026 houve cerca de 60 processos destes (Mulheres Mil, Cuidadora de Pessoa Idosa, Energife, Meninas de Luta,
canto coral, ProEJA FIC…), muitos com inscrição de uma semana; antes só o vigia do outro portal os apanhava, e mal.

Este leitor cria o curso quando encontra, por código:
- inscrições abertas hoje, pela etapa «Inscrições» da página (o ano é o da publicação do processo; uma data de fim
  anterior à publicação passa para o ano seguinte);
- um edital (PDF da lista de documentos, sem «resultado», «chamada» ou «convocação» no nome) com a forma de seleção
  SEM prova: sorteio ou ordem de inscrição/chegada — edital com prova, entrevista, redação ou análise de currículo
  fica fora; processo que já tem «Resultado Final» publicado acabou;
- nada que restrinja a estudantes ou servidores do IFRN.
Gratuidade: IFRN «Tudo gratuito» em Sites de confiança. Público só de mulheres (Mulheres Mil) vai no título.
O texto do curso é o texto oficial da página, copiado. Um curso já na base com o mesmo prazo não é criado de novo.
"""
import datetime
import html as _html
import os
import re
import sys
import urllib.parse

from base import (DESCRICAO_PAGINA, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, exige_prova,
                  texto_de_html)
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara, necessidades

P = "https://portal.ifrn.edu.br"
SUBTIPOS = {"10": "Qualificação Profissional (FIC)", "50": "Curso de Extensão", "3": "Técnico Integrado - ProEJA"}
GRATUITO = "gratuito: «entidade marcada como “Tudo gratuito” em Sites de confiança, por uma pessoa» (IFRN: escola pública)"
SELECAO = re.compile(r"sorteio|ordem (cronol[óo]gica )?de (inscri[çc][ãa]o|chegada)|ordem de envio", re.I)
SEM_ACESSO = re.compile(r"(exclusiv\w+|apenas|somente) (para |a |aos? |às? )?(estudantes|discentes|alunos|servidor)\w*[^.]{0,40}"
                        r"(do|da|no|na) (IFRN|Instituto|campus)|regularmente matriculad[oa]s? (em cursos )?(no|do) IFRN", re.I)
SEM_PROVA_EXTRA = re.compile(r"\bentrevistas?\b|\breda[çc][ãa]o\b|an[áa]lise (de |do )?(curr[íi]culo|curricular)|"
                             r"carta de inten[çc][ãa]o|\bprova (objetiva|escrita|pr[áa]tica)|(avalia[çc][ãa]o|an[áa]lise|prova) de t[íi]tulos", re.I)
IDADE = re.compile(r"idade m[íi]nima de \d+ anos|\d+ (\([a-zç]+\) )?anos (completos|ou mais)|a partir de \d+ (\([a-zç]+\) )?anos", re.I)
MULHERES = re.compile(r"mulheres mil|exclusiv\w+ (para |a )?mulheres|p[úu]blico feminino", re.I)


def frase(texto, regex):
    """A primeira frase inteira do texto que tem o padrão e não o nega («não confere», «não será»…)."""
    for m in regex.finditer(texto or ""):
        ini = max(texto.rfind(". ", 0, m.start()), texto.rfind("; ", 0, m.start()), m.start() - 350) + 1
        fim_p = [x for x in (texto.find(". ", m.end()), texto.find("; ", m.end())) if x != -1]
        fim = min(fim_p + [m.end() + 250]) + 1
        f = texto[ini:fim].strip(" .;") + "."
        if not re.search(r"\bnão (confere|garante|ser[áa]|haver[áa]|implica)", f, re.I):
            return f
    return ""


def limpo(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s or ""))).strip()


def baixar_txt(u, n=60):
    return baixar(u, timeout=n).decode("utf-8", "replace")


def processos(hoje):
    """Páginas dos processos «Em andamento» dos subtipos acima (ano do edital: este e, a partir de outubro, o próximo)."""
    anos = [hoje.year] + ([hoje.year + 1] if hoje.month >= 10 else [])
    vistos, out = set(), []
    for st, nome in SUBTIPOS.items():
        for ano in anos:
            for pg in range(1, 6):
                try:
                    a = baixar_txt(f"{P}/processos-seletivos/buscar/?tipo=3&subtipo={st}&ano_edital={ano}&page={pg}")
                except Exception as e:  # noqa: BLE001
                    print(f"  ! lista {nome} {ano} p{pg}: {type(e).__name__}")
                    break
                novos = 0
                for m in re.finditer(r'href="([^"]*/processo-seletivos-estude-no-ifrn/[^"]+)"', a):
                    u = urllib.parse.urljoin(P, m.group(1))
                    if u in vistos:
                        continue
                    vistos.add(u)
                    novos += 1
                    bruto = a[max(0, m.start() - 2500):m.start()]
                    antes = limpo(bruto)
                    estados = re.findall(r"\b(Finalizado|Em andamento|Encerrado|Suspenso|Cancelado|Previsto)\b", antes)
                    tits = re.findall(r"<h[2-4][^>]*>(.*?)</h[2-4]>", bruto, re.S)
                    out.append({"url": u, "subtipo": nome, "estado": estados[-1] if estados else "",
                                "titulo": limpo(tits[-1]) if tits else ""})
                if not novos:
                    break
    return out


def data_iso(dm, ano):
    d, m = dm.split("/")[:2]
    return datetime.date(ano, int(m), int(d))


def ler_pagina(u):
    a = baixar_txt(u)
    m = re.search(r"(?s)<main.*?</main>", a)
    texto = limpo(m.group(0) if m else a)
    t = re.search(r"<title>(.*?)</title>", a, re.S)
    titulo = limpo(t.group(1)).split(" — ")[0] if t else ""
    pub = re.search(r"Publicada há [^(]*\(em (\d{2})/(\d{2})/(\d{4})", texto)
    ins = re.search(r"(?:(\d{2}/\d{2})(?:/\d{4})?(?: às [\dh:]+)? a |Até )(\d{2}/\d{2})(?:/\d{4})?(?: às [\dh:]+)? Inscriç\w+", texto)
    docs = []
    for h, nome in re.findall(r'<a[^>]+href="([^"]*/documents/[^"]+)"[^>]*>(.*?)</a>', a, re.S):
        docs.append((urllib.parse.urljoin(P, _html.unescape(h)), limpo(nome) or urllib.parse.unquote(h.rsplit("/", 1)[-1])))
    conteudo = re.search(r"Conteúdo Etapas (.*?)(?: Documentos| Campus \w| \d+ EDITAL| Processo seletivo atualizado)", texto)
    campus = re.search(r"/campus/([^/]+)/", u)
    return {"titulo": titulo, "texto": texto, "docs": docs, "conteudo": conteudo.group(1).strip() if conteudo else "",
            "pub": datetime.date(int(pub.group(3)), int(pub.group(2)), int(pub.group(1))) if pub else None,
            "ins": ins, "frase_ins": ins.group(0) if ins else "", "campus": campus.group(1) if campus else ""}


def periodo(pg):
    if not pg["ins"] or not pg["pub"]:
        return None, None
    ano = pg["pub"].year
    fim = data_iso(pg["ins"].group(2), ano)
    if fim < pg["pub"] - datetime.timedelta(days=60):
        fim = data_iso(pg["ins"].group(2), ano + 1)
    ini = data_iso(pg["ins"].group(1), ano) if pg["ins"].group(1) else pg["pub"]
    if ini > fim:
        ini = data_iso(pg["ins"].group(1), fim.year - 1)
    return ini, fim


def edital(pg):
    """(url, texto) do edital mais recente (retificado ou de abertura), e se já há resultado final."""
    resultado = any(re.search(r"resultado final", n, re.I) for _, n in pg["docs"])
    candidatos = [(u, n) for u, n in pg["docs"] if u.lower().endswith(".pdf") and
                  not re.search(r"resultado|chamada|convoca|homologa|recurso|lista|gabarito|ata\b", n, re.I)]
    for u, n in candidatos:  # a lista vem do mais recente para o mais antigo
        if re.search(r"retifica[çc][ãa]o \d", n, re.I) and not re.search(r"retificad", n, re.I):
            continue  # o documento só com as mudanças; preferir o edital completo
        try:
            dados = baixar(u, timeout=60)
        except Exception:  # noqa: BLE001
            continue
        if dados[:4] == b"%PDF":
            return u, texto_de_html(dados), resultado
    return "", "", resultado


def main():
    seco = bool(os.environ.get("SECO"))
    todos = bool(os.environ.get("TESTE_FECHADOS"))  # ensaio: ler também os fechados, para testar o leitor
    base = None if seco else Base()
    if base:
        carregar_config(base)
    hoje_txt = hoje_ceara()
    hoje = datetime.date.fromisoformat(hoje_txt)
    lista = processos(hoje)
    print(f"IFRN: {len(lista)} processos nos subtipos FIC, extensão e ProEJA "
          f"({sum(1 for x in lista if x['estado'] == 'Em andamento')} em andamento).")
    existentes = {} if seco else {r["ID"]: r for r in base.tabela("Cursos") if "IFRN" in (r.get("Entidade") or "")}
    prazos = {(r.get("Inscrições até") or "") for r in existentes.values() if (r.get("Situação das inscrições") or "") != "Encerrado"}
    novos, alteracoes = [], []
    for p in lista:
        if p["estado"] != "Em andamento" and not todos:
            continue
        try:
            pg = ler_pagina(p["url"])
        except Exception as e:  # noqa: BLE001
            print(f"  ! {p['url']}: {type(e).__name__}")
            continue
        ini, fim = periodo(pg)
        nome = p["titulo"] or pg["titulo"] or p["url"].rstrip("/").rsplit("/", 1)[-1]
        if not fim:
            print(f"  - {nome[:60]}: sem etapa de inscrições legível")
            continue
        aberto = ini <= hoje <= fim
        if not aberto and not todos:
            continue
        url_pdf, t, resultado = edital(pg)
        motivo = []
        if resultado:
            motivo.append("já tem resultado final")
        if not t:
            motivo.append("sem PDF do edital legível")
        sel = frase(t, SELECAO) if t else ""
        if t and not sel:
            motivo.append("o edital não diz sorteio nem ordem de inscrição")
        if t and (exige_prova(t) or SEM_PROVA_EXTRA.search(t + " " + pg["texto"])):
            motivo.append("o edital fala de prova, entrevista, redação ou análise de currículo")
        if t and SEM_ACESSO.search(t + " " + pg["conteudo"]):
            motivo.append("só para estudantes ou servidores do IFRN")
        ident = id_curso(p["url"], nome)
        estado = f"{'aberto' if aberto else 'fechado'} {ini} a {fim}"
        if motivo:
            print(f"  - {nome[:60]} | {estado}: fora ({'; '.join(motivo)})")
            continue
        idade = frase(t, IDADE)
        print(f"  + {nome[:70]} | {estado} | seleção: «{sel[:220]}»" + (f" | idade: «{idade[:200]}»" if idade else ""))
        if seco or not aberto:
            continue
        if ident in existentes:
            continue
        if fim.isoformat() in prazos:
            print(f"    (já há um curso do IFRN aberto com o prazo {fim}; não é criado de novo)")
            continue
        mulheres = bool(MULHERES.search(nome + " " + pg["conteudo"] + " " + t[:3000]))
        if not citacao_valida(sel, t) or not citacao_valida(pg["frase_ins"], pg["texto"]):
            print("    frases não conferem; não criado")
            continue
        ev = [GRATUITO, f"data: «{pg['frase_ins']}» ({p['url']})", f"vagas: «{sel}» ({url_pdf})"]
        comp = ["gratuito", "data"]
        if idade:
            ev.append(f"idade: «{idade}» ({url_pdf})")
        campus = pg["campus"].replace("-", " ").title() if pg["campus"] not in ("", "reitoria") else ""
        desc = pg["conteudo"] or ""
        novos.append({
            "ID": ident, "Estado": "Publicado" if desc else "Rever",
            "Título": (nome + (" (só para mulheres)" if mulheres and "mulher" not in nome.lower() else ""))[:200],
            "Entidade": "IFRN – Instituto Federal do Rio Grande do Norte" + (f" (campus {campus})" if campus else ""),
            "Link": p["url"], "Página do curso": p["url"], "Local": "BR-RN", "Modalidade": "presencial", "País": "BR",
            "Região": "Rio Grande do Norte", "Cidade": "", "Descrição": desc[:1500], "Origem da descrição": DESCRICAO_PAGINA,
            "Necessidades": necessidades("", nome), "Perfis": "todos", "Condição de acesso": "só para mulheres" if mulheres else "",
            "Requisitos": idade[:300], "Certificado": "desconhecido",
            "Inscrições até": fim.isoformat(), "Link verificado": "SIM", "Primeiro visto": hoje_txt, "Última verificação": hoje_txt,
            "Origem": "turmas", "Notas": f"{p['subtipo']}; edital: {url_pdf}",
            "Como me inscrever": "As regras e o local de inscrição estão no edital, na página do processo seletivo (botão do curso).",
            "Nota da verificação": f"{hoje_txt}: criado por ifrn_fic.py a partir da página e do edital oficiais (frases conferidas por código).",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": ", ".join(comp),
            "O que falta confirmar": "" if desc else "a página não tem texto do curso",
        })
    # cursos já criados por este leitor: fechar quando o prazo passa
    for r in existentes.values():
        if (r.get("Link") or "").startswith(P + "/campus/") and (r.get("Situação das inscrições") or "") == "Aberto" \
                and (r.get("Inscrições até") or "9999") < hoje_txt:
            alteracoes.append((r["_linha"], {"Situação das inscrições": "Encerrado", "Última verificação": hoje_txt}))
    if seco:
        return 0
    base.atualizar("Cursos", alteracoes)
    base.acrescentar("Cursos", novos)
    base.guardar()
    print(f"\nIFRN: {len(novos)} cursos novos, {len(alteracoes)} encerrados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
