"""Turmas presenciais do «Caminhos Digitais» (Governo da Paraíba, Secties/Fapesq), lidas da página oficial de
inscrição, sem Claude.

A carreta do projeto percorre 22 cidades da Paraíba. A página https://caminhosdigitais.com.br/inscricao/ mostra, para a
cidade onde a carreta está e para a seguinte, as turmas (curso, horário, «Esgotada» ou «N vagas»). A inscrição é feita
nessa página (nome, CPF, data de nascimento, telefone). Não há página por turma.

Regras:
- só turmas com vagas e cuja parada ainda não acabou; «Esgotada» ou parada passada = Encerrada;
- o «Tour de Realidade Virtual» não é curso: fica de fora;
- gratuidade: só com a frase da própria página, conferida por código a cada leitura (FRASE_GRATUIDADE);
- carga horária: NÃO é publicada (a página das trilhas diz 16 a 40 horas, mas cada turma da carreta aparece com 1 hora;
  pendência de 23/11/2026). Enquanto PUBLICAR_SOZINHO for False, as turmas novas entram em Rever com uma nota.
"""
import datetime
import html as _html
import re
import sys

from base import HISTORICO, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, registar_pendencia, sim
from comum import baixar
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

PAGINA = "https://caminhosdigitais.com.br/inscricao/"
ENTIDADE = "Governo da Paraíba – Secties (Caminhos Digitais)"
FRASE_GRATUIDADE = "A formação é gratuita e as aulas acontecem na carreta"
FORA = re.compile(r"\btour\b|realidade virtual", re.I)
PUBLICAR_SOZINHO = False  # 23/11/2026: à espera da confirmação da carga horária (ver pendência)
NOTA_ESPERA = "À espera da confirmação da carga horária das turmas da carreta (pendência de 23/11/2026)."


def limpo(t):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def ler(html):
    """[(cidade, ini, fim, local, [(id, curso, horario, vagas_texto)])] de cada bloco section.cidade-grupo."""
    cidades = []
    for b in re.split(r'<section class="cidade-grupo"', html)[1:]:
        cidade = limpo((re.search(r"<h3[^>]*>(.*?)</h3>", b, re.S) or [None, ""])[1])
        sub = limpo((re.search(r"<p>(.*?)</p>", b, re.S) or [None, ""])[1])
        m = re.match(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s*a\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*·?\s*(.*)", sub)
        if not m:
            continue
        ano_fim = int(m.group(6))
        fim = datetime.date(ano_fim, int(m.group(5)), int(m.group(4)))
        ano_ini = int(m.group(3)) if m.group(3) else (ano_fim - 1 if int(m.group(2)) > fim.month else ano_fim)
        ini = datetime.date(ano_ini, int(m.group(2)), int(m.group(1)))
        turmas = []
        for t in re.findall(r'<label class="turma-op">(.*?)</label>', b, re.S):
            tid = (re.search(r'value="(\d+)"', t) or [None, ""])[1]
            curso = limpo((re.search(r"<b>(.*?)</b>", t, re.S) or [None, ""])[1])
            hora = limpo((re.search(r"<small>(.*?)</small>", t, re.S) or [None, ""])[1]).split("·")[0].strip()
            vagas = limpo((re.search(r'<span class="turma-vagas[^"]*">(.*?)</span>', t, re.S) or [None, ""])[1])
            turmas.append((tid, curso, hora, vagas))
        cidades.append((cidade, ini.isoformat(), fim.isoformat(), m.group(7).strip(), turmas, sub))
    return cidades


def horario(h):
    m = re.match(r"(\d{1,2})h(\d{2})?\s*às\s*(\d{1,2})h(\d{2})?", h or "")
    return f"{int(m.group(1)):02d}:{m.group(2) or '00'} - {int(m.group(3)):02d}:{m.group(4) or '00'}" if m else ""


def main():
    base = Base()
    carregar_config(base)
    garantir_aba(base)
    hoje = hoje_ceara()
    try:
        html = baixar(PAGINA, timeout=40).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"Caminhos Digitais: a página não abriu ({type(e).__name__}: {e}). Nada alterado.")
        registar_pendencia(base, f"Caminhos Digitais (Paraíba): a página de inscrição não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador.", PAGINA, origem="caminhos_digitais.py")
        return 0
    cidades = ler(html)
    texto = limpo(html)
    gratuito = citacao_valida(FRASE_GRATUIDADE, texto)
    print(f"Caminhos Digitais: {len(cidades)} cidades na página; gratuidade {'confirmada' if gratuito else 'NÃO confirmada'}.")
    if not cidades and "cidade-grupo" not in html:
        registar_pendencia(base, "Caminhos Digitais (Paraíba): a página de inscrição mudou de formato.",
                           "Se a página ainda mostra as turmas por cidade (o leitor precisa de ajuste).", PAGINA,
                           origem="caminhos_digitais.py")
        return 0

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(PAGINA)]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        (ocultos.add(chave(r.get("Título", ""))) if r.get("Estado") == "Oculto"
         else cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip()))
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA) if (t.get("Link da turma") or "").startswith(PAGINA)}

    novas, alteracoes, historico, cursos_novos, vistos = [], [], [], [], set()
    estado_final = {l: (t.get("Curso", ""), t.get("Situação", ""), t.get("Estado") == "Publicado") for l, t in existentes.items()}
    for cidade, ini, fim, local, turmas, sub in cidades:
        for tid, curso, hora, vagas in turmas:
            if not curso or FORA.search(curso) or chave(curso) in ocultos:
                continue
            link = f"{PAGINA}#{re.sub(r'[^a-z0-9]+', '-', chave(f'{cidade} {curso} {hora} {tid}')).strip('-')}"
            if link in vistos:
                continue
            vistos.add(link)
            com_vagas = bool(re.match(r"\d+\s+vagas?", vagas, re.I)) and not re.match(r"0\s+vagas", vagas)
            situacao = "Aberta" if com_vagas and hoje <= fim else "Encerrada"
            problemas = []
            if not horario(hora):
                problemas.append(f"o horário ({hora}) não foi lido")
            if fim < ini:
                problemas.append(f"a parada acaba ({fim}) antes de começar ({ini})")
            campos = {
                "Título na fonte": curso, "Unidade na fonte": f"Carreta Caminhos Digitais – {local}".strip(" –"),
                "Unidade": "", "Cidade": cidade, "Link de matrícula": PAGINA, "Início": ini, "Fim": fim,
                "Horário": horario(hora), "Dias": "", "Carga horária": "", "Vagas": vagas,
                "Prazo de inscrição": fim, "Idade mínima": "", "Escolaridade": "", "Documentos": "",
                "Mais informações": "Inscrição na página do projeto, enquanto houver vagas (pede nome, CPF, data de nascimento e telefone).",
                "Local na fonte": local, "Modo de inscrição": "online", "Situação": situacao,
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": f"página oficial: «{cidade}» «{sub}» | «{curso}» «{hora}» «{vagas}»"[:900],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(problemas) + ".") if problemas else
                f"{hoje}: ok (cidade, datas, horário e vagas da página oficial de inscrição).",
            }
            ex = existentes.get(link)
            if ex:
                if problemas and ex.get("Estado") == "Publicado":
                    campos["Estado"] = "Rever"
                    historico.append(registo(ex, "Auditoria", "Rever", campos["Auditoria"]))
                alteracoes.append((ex["_linha"], campos))
                estado_final[link] = (ex.get("Curso", ""), situacao, campos.get("Estado", ex.get("Estado")) == "Publicado")
            elif situacao == "Aberta":
                k = chave(curso)
                cid = cursos.get(k)
                if not cid:
                    novo = {
                        "ID": id_curso(PAGINA, curso), "Estado": "Novo", "Título": curso[:200], "Entidade": ENTIDADE,
                        "Link": PAGINA, "Local": "BR-PB", "Modalidade": "presencial", "País": "BR", "Região": "Paraíba",
                        "Cidade": "", "Descrição": "", "Origem da descrição": "", "Necessidades": necessidades("", curso),
                        "Perfis": "todos", "Condição de acesso": "", "Requisitos": "", "Certificado": "desconhecido",
                        "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM",
                        "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas",
                        "Notas": "" if PUBLICAR_SOZINHO else NOTA_ESPERA, "Como me inscrever": "",
                        "Nota da verificação": f"{hoje}: curso criado a partir de uma turma na página oficial do Caminhos Digitais.",
                        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                        "Evidência": (f"gratuito: «{FRASE_GRATUIDADE}» ({PAGINA})" if gratuito else ""),
                        "Campos comprovados": "gratuito, internet" if gratuito else "internet",
                        "Precisa de internet": "Não", "Antes de começar": "cpf",
                        "O que falta confirmar": "" if gratuito else "A página não confirmou que os cursos são gratuitos.",
                    }
                    cursos_novos.append(novo)
                    cid = cursos[k] = novo["ID"]
                estado = "Publicado" if PUBLICAR_SOZINHO and not problemas else "Rever"
                novas.append({"ID": id_turma(link), "Curso": cid, "Estado": estado, "Link da turma": link,
                              "Primeiro visto": hoje, **campos, **({} if PUBLICAR_SOZINHO else {"Notas": NOTA_ESPERA})})
                estado_final[link] = (cid, situacao, estado == "Publicado")
            print(f"  {'·' if ex else '+'} {cidade} | {curso[:40]} | {hora} | {vagas} | {situacao}")

    for link, t in existentes.items():
        if link not in vistos and t.get("Situação") != "Encerrada":
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje,
                                             "Notas": "Saiu da página oficial de inscrição."}))
            estado_final[link] = (t.get("Curso", ""), "Encerrada", False)

    por_curso = {}
    for c, sit, visivel in estado_final.values():
        if visivel:
            por_curso.setdefault(c, []).append(sit)

    def pode_publicar(r):
        return (PUBLICAR_SOZINHO and r.get("Estado") == "Novo" and r.get("Origem") == "turmas"
                and not sim(r.get("Mudança a rever")) and "Aberta" in por_curso.get(str(r.get("ID", "")).strip(), [])
                and "gratuito" in (r.get("Campos comprovados") or ""))
    nota = f"{hoje}: publicado automaticamente: turma aberta na página oficial e gratuidade confirmada."
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
        if campos:
            alteracoes_cursos.append((r["_linha"], campos))

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nCaminhos Digitais: {len(novas)} turmas novas, {len(alteracoes)} atualizadas; {len(cursos_novos)} cursos novos "
          f"({'publica sozinho' if PUBLICAR_SOZINHO else 'tudo em Rever, à espera da carga horária'}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
