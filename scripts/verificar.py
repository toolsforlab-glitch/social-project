"""Verificação semanal: o Claude relê a página de cada curso visível, confirma se continua aberto e gratuito
e escreve o passo a passo de inscrição em linguagem simples."""
import html
import os
import re
import sys

from base import texto_de_html, COLUNAS_BARREIRAS, ESCOLARIDADES, CAMPOS_PROVA, HISTORICO, SITUACOES, Base, citacao_valida, carregar_config, hoje_iso, perfis_da_frase, registo_historico, sim, visivel
from comum import ErroClaude, baixar, claude, custo_estimado, dominio_permitido, extrair_json
from paginas import e_pagina_do_curso, encontrar_pagina

ABA = "Cursos"
MAX_POR_EXECUCAO = int(os.environ.get("MAX_VERIFICACOES", "60"))
MAX_CARACTERES = 12000

SISTEMA = """Verificas cursos gratuitos para um site público lido por pessoas com pouca escolaridade e \
poucos recursos. Uma informação errada pode fazer alguém perder tempo e dinheiro. Recebes os dados que temos \
sobre um curso e o texto da página oficial.

REGRA PRINCIPAL: usa só o que a página diz explicitamente. Se a página não diz, a resposta é null ou "incerto". \
Nunca deduzas, nunca completes com o que é habitual e nunca uses conhecimento geral. Exemplos do que NÃO fazer: \
transformar "etapas até 22/12" em "inscrições até 22/12"; concluir que é gratuito porque a entidade costuma \
ter cursos gratuitos; usar a data de início das aulas como data limite de inscrição.

Para cada afirmação importante tens de copiar, em "evidencias", a frase EXATA da página que a prova \
(copiada letra a letra, até 25 palavras). Sem frase exata, a afirmação não vale e o campo fica null/"incerto".

Devolve JSON entre <json></json> com:
- "situacao": "aberto" (a página diz que as inscrições estão abertas, que o acesso é livre, ou indica uma turma \
futura com inscrição), "encerrado" (a página diz que as inscrições terminaram ou o curso acabou) ou "incerto" \
(tudo o resto, incluindo quando o curso não aparece na página).
- "gratuito": "sim" ou "não" só se a página o disser para ESTE curso; senão "incerto".
- "inscricoes_ate": data AAAA-MM-DD só se a página indicar a data limite de INSCRIÇÃO; senão null.
- "restricoes": quem pode entrar (idade, renda, escolaridade, morada, já ser estudante…), só se a página o \
disser; senão null.
- "idade_minima": número, só se a página indicar idade mínima; senão null.
- "escolaridade_minima": uma de "Nenhuma", "Saber ler e escrever", "Fundamental incompleto", "Fundamental completo", \
"Médio incompleto", "Médio completo", "Superior", só se a página o disser; senão null.
- "renda_maxima": limite de renda, como está na página (ex.: "Renda familiar por pessoa de até dois salários mínimos"); senão null.
- "prioridade_cadunico": "sim" só se a página disser que há prioridade ou exigência de Cadastro Único; senão null.
- "turnos": lista com "Manhã", "Tarde" e/ou "Noite", tirada dos horários de turmas FUTURAS indicados na página \
(antes das 12h = Manhã, das 12h às 18h = Tarde, a partir das 18h = Noite); senão [].
- "precisa_internet": "sim" se o curso ou a inscrição só puderem ser feitos pela internet, "não" se a página disser \
que há inscrição presencial e o curso é presencial; senão null.
- "ajuda_custo": ajuda em dinheiro, vale-transporte, lanche ou material oferecido, como está na página; senão null. \
"Bolsa de estudo" que só significa curso gratuito NÃO é ajuda de custo.
- "documentos": documentos pedidos para a inscrição, como estão na página; senão null.
- "publico": lista de ids da lista de perfis dada no pedido, SÓ quando a página diz que o curso é feito para esse \
grupo, só aceita esse grupo, ou reserva vagas ou dá prioridade a esse grupo; senão []. Nunca deduzas pelo tema do \
curso: um curso de manicure não é "para mulheres" e um curso sobre migrações não é "para migrantes" se a página não \
o disser. A evidência é a frase que diz para quem é o curso ou para quem são as vagas.
- "evidencias": objeto com as frases exatas para cada um dos campos acima (null quando não houver).

ATENÇÃO a rótulos enganadores: alguns sites mostram "Inscrições abertas" em turmas que já começaram ou terminaram. \
Compara sempre as datas da turma com a data de hoje: uma turma que já começou não prova que as inscrições estão abertas.
- "em_falta": lista curta, em linguagem simples, do que a página não esclarece e a pessoa tem de confirmar \
(ex.: "Não diz até quando são as inscrições").
- "como_me_inscrever": 3 a 5 passos curtos, em linguagem muito simples, só com o que a página explica (onde ir, \
que documentos levar, até quando). Se a página não explicar como se inscrever, devolve um único passo: \
"A página não explica como se inscrever: contacte a entidade." seguido do contacto, se a página o tiver. \
Para cursos no Brasil escreve em português do Brasil; em Portugal, em português de Portugal.
- "nota": uma frase curta a explicar o que verificaste."""


AUDITOR = """És um auditor independente. Um site público, lido por pessoas com poucos recursos, vai publicar um \
curso. Recebes o texto da página oficial e uma lista numerada de afirmações que o site vai fazer. Não foste tu \
que as escreveste e o teu trabalho é procurar erros.

Para cada afirmação responde "confirmada" só se a página o disser explicitamente, e copia a frase EXATA da \
página que o prova (letra a letra, até 25 palavras). Em todos os outros casos responde "não confirmada": se a \
página não diz, se diz outra coisa, se é preciso deduzir, ou se tens dúvida. Uma turma que já começou não prova \
inscrições abertas. Não uses conhecimento geral.

Uma afirmação que começa por "A página não fala em" é confirmada quando a página realmente não fala nisso \
(frase: null); se falar, é "não confirmada" e copias a frase.

Devolve só JSON entre <json></json>: {"afirmacoes": [{"n": 1, "veredicto": "confirmada" ou "não confirmada", \
"frase": "..." ou null, "motivo": "..."}]}"""


def auditar(cfg, r, pagina, data, hoje_txt, gratuito_por_entidade=False):
    """Segunda opinião, por outro modelo, antes de publicar sozinho. Devolve (passou, falhas, custo)."""
    modelo = cfg.get("modelo_auditoria") or "claude-sonnet-5-5"
    afirmacoes = [f"Esta página é sobre o curso «{r['Título']}».",
                  f"Hoje ({hoje_txt}) é possível inscrever-se ou começar este curso: inscrições abertas, "
                  "acesso livre a qualquer momento, ou turma futura com inscrição."]
    # a gratuidade só é auditada na página quando não vem de uma entidade marcada como "Tudo gratuito"
    afirmacoes.append("A página não fala em pagamento, mensalidade ou taxa para fazer este curso." if gratuito_por_entidade
                      else "Este curso é gratuito para quem o frequenta.")
    if data:
        afirmacoes.append(f"O prazo para se inscrever termina a {data}.")
    if (r.get("Descrição") or "").strip():
        afirmacoes.append(f"O curso ensina isto: {r['Descrição']}")
    if (r.get("Requisitos") or "").strip():
        afirmacoes.append(f"Para entrar é preciso: {r['Requisitos']}")
    pedido = ("Afirmações:\n" + "\n".join(f"{i}. {a}" for i, a in enumerate(afirmacoes, 1))
              + f"\n\nTexto da página oficial:\n{pagina}")
    lista, custo = None, 0.0
    for _ in range(2):  # resposta ilegível: tenta outra vez
        try:
            texto, uso = claude(modelo, AUDITOR, pedido, max_tokens=4000)
        except ErroClaude as e:
            return False, [f"a auditoria não correu ({e})"], custo
        custo += custo_estimado(uso, modelo)
        res = extrair_json(texto)
        lista = res.get("afirmacoes") if isinstance(res, dict) else None
        if isinstance(lista, list):
            break
    if not isinstance(lista, list):
        return False, ["a auditoria não devolveu uma resposta legível (volta a tentar na próxima semana)"], custo
    falhas = []
    for i, a in enumerate(afirmacoes, 1):
        v = next((x for x in lista if isinstance(x, dict) and str(x.get("n")) == str(i)), {})
        negativa = a.startswith("A página não fala em pagamento")  # não há frase para copiar numa ausência
        if v.get("veredicto") != "confirmada" or not (negativa or citacao_valida(str(v.get("frase") or ""), pagina)):
            falhas.append(a[:90])
    return not falhas, falhas, custo


def texto_da_pagina(url):
    return texto_de_html(baixar(url, timeout=30))[:MAX_CARACTERES]


def pagina_do_curso(r, dominios):
    """Página própria do curso (regras em paginas.py) e o texto a dar ao Claude.

    Devolve (página do curso ou "", nota, texto). Se a página do curso não for encontrada, o texto é o do link.
    """
    atual = (r.get("Página do curso") or "").strip()
    if atual:
        try:
            bruto = baixar(atual, timeout=30).decode("utf-8", "replace")
            if e_pagina_do_curso(bruto, r["Título"]):
                return atual, "", texto_de_html(bruto)[:MAX_CARACTERES]
        except Exception:  # noqa: BLE001
            pass
    bruto = baixar(r["Link"], timeout=30).decode("utf-8", "replace")
    pagina, nota = encontrar_pagina(r["Link"], bruto, r["Título"], dominios)
    if pagina and pagina != r["Link"]:
        try:
            return pagina, nota, texto_de_html(baixar(pagina, timeout=30))[:MAX_CARACTERES]
        except Exception:  # noqa: BLE001
            return "", "a página do curso deixou de abrir", texto_de_html(bruto)[:MAX_CARACTERES]
    return pagina, nota, texto_de_html(bruto)[:MAX_CARACTERES]


def main():
    base = Base()
    cfg = carregar_config(base)
    if not cfg.get("verificar_cursos", True):
        print("Verificação desligada na Configuração.")
        return 0
    modelo = cfg.get("modelo_cursos", "claude-haiku-5-5")
    locais = {l["id"] for l in cfg["cursos"]["locais"]}
    hoje_txt = hoje_iso()

    piloto = cfg.get("territorio_piloto", "")
    pais_piloto = "BR" if piloto.startswith("BR") else "PT" if piloto == "PT" else ""
    candidatos = [r for r in base.tabela(ABA)
                  if (visivel(r.get("Estado"), cfg) or r.get("Estado") in ("Novo", "Rever"))
                  and r.get("Local") in locais and r.get("Link")
                  # os cursos do Senac PSG são acompanhados turma a turma por turmas.py, sem Claude
                  and "psg.ce.senac.br" not in r["Link"]
                  and "centec.org.br/cursos-formacao-inicial-continuada" not in r["Link"]
                  and "ma.senac.br/editais-psg" not in r["Link"]
                  and (r.get("Verificar automaticamente", "") == "" or sim(r.get("Verificar automaticamente")))
                  # durante um piloto, os cursos online de outros países não aparecem no site: não gastar com eles
                  and not (r.get("Local") == "online" and pais_piloto
                           and r.get("País") not in (pais_piloto, "Internacional", ""))]
    # primeiro os que ainda não têm passo a passo, depois os verificados há mais tempo
    candidatos.sort(key=lambda r: (bool(r.get("Como me inscrever")), r.get("Nota da verificação") != "",
                                   r.get("Última verificação") or ""))
    candidatos = candidatos[:MAX_POR_EXECUCAO]
    print(f"A verificar {len(candidatos)} cursos")

    historico = []
    alteracoes, custo_total, contagem = [], 0.0, {"aberto": 0, "encerrado": 0, "incerto": 0, "falhou": 0}
    for r in candidatos:
        dominios = cfg["cursos"]["dominios"].get(r.get("Local"), [])
        try:
            pagina_curso, nota_pagina, pagina = pagina_do_curso(r, dominios)
        except Exception as e:  # noqa: BLE001
            contagem["falhou"] += 1
            alteracoes.append((r["_linha"], {"Nota da verificação": f"{hoje_txt}: não foi possível abrir a página ({type(e).__name__})."}))
            print(f"  ✗ {r['Título']}: página não abriu ({type(e).__name__})")
            continue
        dados = {k: r.get(k, "") for k in ("Título", "Entidade", "Local", "Cidade", "Descrição", "Requisitos",
                                            "Inscrições até", "Início")}
        pedido = (f"Data de hoje: {hoje_txt}.\n\nDados do curso: {dados}\n\nLink: {pagina_curso or r['Link']}\n\n"
                  f"Lista de perfis (ids): {', '.join(p for p in cfg['cursos']['perfis_internos'] if p != 'todos')}.\n\n"
                  f"Texto da página:\n{pagina}")
        try:
            texto, uso = claude(modelo, SISTEMA, pedido, max_tokens=4000)
        except ErroClaude as e:
            print(f"  ERRO no Claude: {e}")
            continue
        custo_total += custo_estimado(uso, modelo)
        res = extrair_json(texto)
        if not isinstance(res, dict):
            print(f"  ? {r['Título']}: resposta sem JSON")
            continue
        ev = res.get("evidencias") if isinstance(res.get("evidencias"), dict) else {}
        provas, rejeitadas = {}, []
        for chave in CAMPOS_PROVA:
            frase = ev.get(chave)
            if frase and citacao_valida(str(frase), pagina):
                provas[chave] = str(frase).strip()
            elif frase:
                rejeitadas.append(CAMPOS_PROVA[chave])
        em_falta = [str(x).strip() for x in (res.get("em_falta") or []) if str(x).strip()]

        # Sem prova não há afirmação
        situacao = res.get("situacao") if res.get("situacao") in ("aberto", "encerrado") else "incerto"
        if situacao != "incerto" and "situacao" not in provas:
            situacao = "incerto"
        gratuito = res.get("gratuito") if "gratuito" in provas else "incerto"
        # Entidades marcadas por uma pessoa como "Tudo gratuito" (Sites de confiança): se a página deste curso
        # não disser nada sobre o preço, vale a decisão da pessoa. Se a página disser que é pago, vale a página.
        gratuito_por_entidade = (gratuito == "incerto" and dominio_permitido(
            pagina_curso or r["Link"], cfg["cursos"].get("dominios_gratuitos", ())))
        if gratuito_por_entidade:
            gratuito = "sim"
            provas["gratuito"] = "entidade marcada como «Tudo gratuito» em Sites de confiança, por uma pessoa"
            em_falta = [x for x in em_falta if "gratuit" not in x.lower()]
        data = str(res.get("inscricoes_ate") or "")[:10] if "inscricoes_ate" in provas else ""
        contagem[situacao] += 1

        # mantém provas registadas à mão (ex.: "unidades") e junta as novas
        outros = [c.strip() for c in (r.get("Campos comprovados") or "").split(",")
                  if c.strip() and c.strip() not in CAMPOS_PROVA.values()]
        campos = {"Página do curso": pagina_curso, "Última verificação": hoje_txt, "Nota da verificação": f"{hoje_txt}: {res.get('nota') or ''}".strip(),
                  "Próxima verificação": "",
                  "Evidência": " | ".join(f"{CAMPOS_PROVA[k]}: «{v}»" for k, v in provas.items())[:1500],
                  "Campos comprovados": ", ".join(outros + [CAMPOS_PROVA[k] for k in provas])}
        # públicos prioritários: só os que a frase da página nomeia; sem frase, o curso é para todos
        if not (r.get("Revisto por pessoa") or "").strip():
            nomeados = perfis_da_frase(provas.get("publico", ""))
            publico = [p for p in (res.get("publico") or []) if p in nomeados and p in cfg["cursos"]["perfis_internos"]]
            novo = ", ".join(publico) or "todos"
            if novo != ((r.get("Perfis") or "").strip() or "todos"):
                campos["Perfis"] = novo
        motivos = []
        if rejeitadas:
            motivos.append("O Claude afirmou " + ", ".join(rejeitadas) + " sem frase da página que o prove (ignorado).")
        revisto = bool((r.get("Revisto por pessoa") or "").strip())
        nova_situacao = SITUACOES[situacao]
        passos = res.get("como_me_inscrever") or []

        if revisto:
            # Curso confirmado por uma pessoa: a rotina não altera os campos importantes, só avisa.
            if nova_situacao != (r.get("Situação das inscrições") or "") and situacao != "incerto":
                motivos.append(f"Revisto por pessoa, mas a página agora indica: {nova_situacao}.")
            if gratuito == "não":
                motivos.append("Revisto por pessoa, mas a página indica que pode não ser gratuito.")
        else:
            campos["Situação das inscrições"] = nova_situacao
            pagina_nova = pagina_curso and pagina_curso != (r.get("Página do curso") or "").strip()
            if passos and (not r.get("Como me inscrever") or pagina_nova):
                campos["Como me inscrever"] = "\n".join(f"{i}. {p.strip()}" for i, p in enumerate(passos[:5], 1))
            if data and not r.get("Inscrições até"):
                campos["Inscrições até"] = data
            elif r.get("Inscrições até") and "inscricoes_ate" not in provas:
                motivos.append(f"A data {r['Inscrições até']} não está confirmada na página.")
            # dados de elegibilidade e barreiras: só com prova, e sem apagar o que já lá está
            for chave, coluna in COLUNAS_BARREIRAS.items():
                if chave not in provas or str(r.get(coluna) or "").strip() not in ("", "Não indicado"):
                    continue
                v = res.get(chave)
                if chave == "turnos":
                    v = ", ".join(t for t in (v or []) if t in ("Manhã", "Tarde", "Noite"))
                elif chave == "escolaridade_minima":
                    v = v if v in ESCOLARIDADES else ""
                elif chave in ("prioridade_cadunico", "precisa_internet"):
                    v = {"sim": "Sim", "não": "Não", "nao": "Não"}.get(str(v or "").lower(), "")
                elif chave == "idade_minima":
                    v = str(int(v)) if isinstance(v, (int, float)) or str(v or "").isdigit() else ""
                if v:
                    campos[coluna] = str(v)[:300]
            if situacao == "encerrado" and r.get("Estado") in ("Novo", "Publicado"):
                campos["Estado"] = "Expirado"
                motivos.append("A página diz que as inscrições terminaram: passou a Expirado.")
            elif gratuito == "não" and r.get("Estado") in ("Novo", "Publicado"):
                campos["Estado"] = "Rever"
                motivos.append("A página indica que pode não ser gratuito: passou a Rever.")
            if r.get("Situação das inscrições") == "Aberto" and situacao == "incerto":
                motivos.append("Estava Aberto e a página já não o confirma.")
        if gratuito == "incerto":
            em_falta.append("A página não diz se este curso é gratuito.")
        if not pagina_curso and "psg.ce.senac.br" not in r["Link"]:
            em_falta.append("Falta a página própria do curso: " + nota_pagina)
        # Publicar sozinho: só com tudo comprovado, sem avisos, e depois de uma auditoria independente
        if (not revisto and r.get("Estado") == "Novo" and "Estado" not in campos and not motivos
                and not sim(r.get("Mudança a rever")) and pagina_curso and situacao == "aberto" and gratuito == "sim"):
            passou, falhas, custo = auditar(cfg, r, pagina, data, hoje_txt, gratuito_por_entidade)
            custo_total += custo
            if passou:
                campos["Estado"] = "Publicado"
                campos["Nota da verificação"] += " Auditoria independente: tudo confirmado; publicado automaticamente."
                print(f"    ↑ publicado depois da auditoria: {r['Título']}")
            else:
                em_falta.append("A auditoria independente não confirmou: " + "; ".join(falhas))
        if motivos:
            campos["Mudança a rever"] = "TRUE"
        frases = [f if f.endswith((".", "!", "?")) else f + "." for f in motivos + em_falta]
        campos["O que falta confirmar"] = " ".join(dict.fromkeys(frases))[:900]
        alteracoes.append((r["_linha"], campos))
        if (campos.get("Situação das inscrições", r.get("Situação das inscrições")) != r.get("Situação das inscrições")
                or "Estado" in campos or motivos):
            historico.append(registo_historico(r, "Claude", situacao, campos, " ".join(motivos) or res.get("nota") or ""))
        marca = {"aberto": "✓", "encerrado": "⨯", "incerto": "?"}[situacao]
        print(f"  {marca} {r['Título']}: {res.get('nota')}")

    base.atualizar(ABA, alteracoes)
    if HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nResumo: {contagem} | custo estimado: {round(custo_total, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
