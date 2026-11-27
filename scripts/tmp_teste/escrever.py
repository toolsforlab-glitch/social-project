"""Temporário (27/11/2026): aplica a auditoria 4 do ChatGPT. Cria 3 cursos, esconde 5 linhas fechadas e anota 2.
Frases conferidas por código (citacao_valida) quando a página abre a partir do GitHub; a FADEX recusa o GitHub e as
frases de Caxias foram conferidas no navegador (regra T10)."""
import io, re, sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from pypdf import PdfReader
from turmas import hoje_ceara

def txt(u):
    b = baixar(u, timeout=40)
    if b[:4] == b"%PDF":
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages)
    return texto_de_html(b)

hoje = hoje_ceara()
falhas = []
def conf(frases, url):
    try:
        t = txt(url)
    except Exception as e:  # noqa: BLE001
        falhas.append(f"{url} não abriu ({type(e).__name__})"); return {}
    ok = {}
    for k, f in frases.items():
        if citacao_valida(f, t): ok[k] = f
        else: falhas.append(f"{k}: frase não confere em {url}")
    return ok

# --- EJA Goiás (estadual)
GO = "https://portaleduca.educacao.go.gov.br/matricula/matricula-2027-1"
fgo = conf({"data": "09/11 a 30/11/2026 Solicitação de vaga para novos alunos, Renovação de Matrícula e TIP",
            "idade": "EJA – Ensino Fundamental: 15 anos; EJA – Ensino Médio: 18 anos.",
            "como": "pelo site matricula.go.gov.br ou pelo WhatsApp (62) 3201-8700",
            "efetivacao": "14/12 a 18/12/2026 Confirmação e efetivação da matrícula na escola"}, GO)
LDB = "https://legis.senado.gov.br/norma/551270/publicacao/34619663"
fldb = conf({"gratuito": "assegurarão gratuitamente aos jovens e aos adultos"}, LDB)
# --- Jornada da Mulher Trabalhadora (DF)
AB = "https://www.agenciabrasilia.df.gov.br/w/projeto-jornada-da-mulher-trabalhadora-reabre-inscricoes-para-cursos-de-qualificacao"
ED = "https://www.agenciabrasilia.df.gov.br/documents/d/guest/26-11-edital-sedet-1-pdf"
fab = conf({"gratuito": "reabriu as inscrições para 165 vagas em cursos gratuitos de qualificação profissional do projeto Jornada da Mulher Trabalhadora",
            "público": "São 165 vagas destinadas a moradoras do Itapoã e de Sobradinho II"}, AB)
fed = conf({"data": "no período de 26/11/2026 a 30/11/2026",
            "início": "O início das atividades formativas está previsto a partir do dia 08/12/2026."}, ED)
# --- IF Baiano EaD (só anotar)
IFB1 = "https://ingresso.ifbaiano.edu.br/concursos/subsequente-ead-ruy-barbosa-2027/"
IFB2 = "https://ingresso.ifbaiano.edu.br/concursos/subsequente-ead-remanso-2027/"
fi1 = conf({"data": "De 19/11/2026 às 23 horas de 08/01/2027."}, IFB1)
fi2 = conf({"data": "De 17/11/2026 às 23 horas de 08/01/2027."}, IFB2)
fsel = conf({"vagas": "A classificação no processo seletivo será por ordem de inscrição e demonstração de interesse."},
            "https://ingresso.ifbaiano.edu.br/wp-content/uploads/2026/11/Edital-001_PROSEL-EaD-modalidade-Subsequente-Campus-Ruy-Barbosa-ano-letivo-2027.pdf")
print("FALHAS:", falhas)

base = Base(); carregar_config(base)
L = base.tabela("Cursos"); por_id = {r.get("ID"): r for r in L}; por_linha = {r["_linha"]: r for r in L}
novos, alter = [], []

if len(fgo) == 4:
    P = GO; T = "Matrícula 2027/1 na EJA da rede estadual de Goiás"; ident = id_curso(P, T)
    ev = [f"{k}: «{v}» ({GO})" for k, v in fgo.items()] + [f"gratuito: «{v}» ({LDB})" for v in fldb.values()]
    if ident not in por_id:
        novos.append({"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Secretaria de Estado da Educação de Goiás (Seduc-GO)",
            "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-GO", "Modalidade": "presencial", "País": "BR",
            "Região": "Goiás", "Cidade": "",
            "Descrição": ("Para jovens e adultos que querem terminar o ensino fundamental ou o ensino médio na escola pública "
                          "estadual de Goiás, em menos tempo. A vaga para 2027 é pedida pela internet ou pelo WhatsApp, até 30 de novembro."),
            "Origem da descrição": "Resumo", "Necessidades": "escola", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": fgo["idade"], "Certificado": "desconhecido", "Inscrições até": "2026-11-30", "Início": "",
            "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial",
            "Precisa de internet": "Não", "Idade mínima": "15",
            "Notas": f"{hoje}: criado à mão pelo Claude (pista da auditoria 4 do ChatGPT, frases conferidas por código).",
            "Como me inscrever": ("1. Até 30/11/2026, peça a vaga no site matricula.go.gov.br ou pelo WhatsApp (62) 3201-8700 "
                                  "(o pedido é só para quem ainda não estuda na rede estadual).\n2. Consulte depois a escola onde "
                                  "ficou («Consultar Alocação»).\n3. De 14 a 18/12/2026, vá à escola com os documentos para confirmar a matrícula."),
            "Nota da verificação": f"{hoje}: página oficial lida por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "data, idade" + (", gratuito" if fldb else ""),
            "Mudança a rever": "FALSE",
            "O que falta confirmar": "Na EJA, a turma só abre se houver alunos suficientes; a escola pode ser outra, perto da 1.ª opção."})

if len(fab) == 2 and len(fed) == 2:
    P = AB; T = "Jornada da Mulher Trabalhadora – alongamento de unhas, extensão de cílios e trancista (Itapoã e Sobradinho II, DF)"
    ident = id_curso(P, T)
    ev = [f"{k}: «{v}» ({AB})" for k, v in fab.items()] + [f"{k}: «{v}» ({ED})" for k, v in fed.items()]
    if ident not in por_id:
        novos.append({"ID": ident, "Estado": "Publicado", "Título": T,
            "Entidade": "Governo do Distrito Federal – Secretaria de Desenvolvimento Econômico, Trabalho e Renda (Sedet-DF)",
            "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-DF", "Modalidade": "presencial", "País": "BR",
            "Região": "Distrito Federal", "Cidade": "Itapoã e Sobradinho II",
            "Descrição": ("Cursos gratuitos de qualificação profissional para mulheres que moram no Itapoã ou em Sobradinho II: "
                          "alongamento de unhas, extensão de cílios e trancista, de manhã ou à tarde. São 165 vagas; as aulas "
                          "começam a 8 de dezembro."),
            "Origem da descrição": "Resumo", "Necessidades": "profissao, renda", "Perfis": "mulheres",
            "Condição de acesso": "Só para mulheres que moram no Itapoã ou em Sobradinho II", "Requisitos": "",
            "Certificado": "desconhecido", "Inscrições até": "2026-11-30", "Início": "2026-12-08", "Link verificado": "SIM",
            "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (Agência Brasília e Edital de Chamamento Público nº 52/2026 – SEDET/DF; frases conferidas por código).",
            "Como me inscrever": ("1. Até 30/11/2026, preencha o «Formulário de inscrição – Projeto Jornada da Mulher Trabalhadora» "
                                  "no portal da Sedet-DF (www.sedet.df.gov.br; o link está na notícia).\n2. A partir de 1/12, veja "
                                  "se foi convocada no site da Sedet-DF.\n3. Se for, confirme a matrícula de 2 a 7/12 (9h–12h e "
                                  "14h–17h) numa Agência do Trabalhador ou no local do curso, com identidade com foto, CPF e "
                                  "comprovante de residência no DF (ou declaração de próprio punho)."),
            "Nota da verificação": f"{hoje}: notícia oficial e edital lidos por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data", "Mudança a rever": "FALSE",
            "O que falta confirmar": ("O edital de reabertura não diz como as vagas são preenchidas nem os outros requisitos; "
                                      "remete para o Edital de Chamamento Público nº 36/2026.")})

# --- Caxias (FADEX; conferido no navegador)
P = "https://www.fadex.org.br/editais/30-2026-selecao-de-participantes-do-programa-acredita-no-primeiro-passo-em-caxias-ma"
E = "https://www.fadex.org.br/api/arquivos/publico/editais/1795468368207-7epzqg27-edital-30.2026-participantes-escola-duque-de-caxias.pdf"
T = "Acredita no Primeiro Passo – Eletricista Instalador Predial e Instalador de Sistemas Fotovoltaicos (Caxias, MA)"
ident = id_curso(P, T)
FC = {"data": "As inscrições são gratuitas e estarão abertas no período de 19 a 30 de novembro de 2026",
      "pagina": "Inscrições Em andamento 23/11/2026 a 30/11/2026 às 23:59",
      "vagas": "A seleção dos(as) participantes dos cursos será realizada com base em critérios técnicos e objetivos, que assegurem a priorização do público-alvo definido neste Edital",
      "idade": "ter entre 18 e 65 anos completos até a data da inscrição", "público": "estar inscrito(a) no CadÚnico, com cadastro ativo",
      "mulheres": "reserva, no mínimo, 60% (sessenta por cento) das vagas de cada curso para mulheres",
      "horário": "Os cursos serão ofertados na modalidade presencial, no período noturno (das 18h às 22h), de segunda a quinta-feira, no CE Duque de Caxias"}
if ident not in por_id:
    ev = [f"data: «{FC['data']}» ({E})", f"data: «{FC['pagina']}» ({P})", f"vagas: «{FC['vagas']}» ({E})", f"idade: «{FC['idade']}» ({E})",
          f"público: «{FC['público']}» ({E})", f"prioridade: «{FC['mulheres']}» ({E})", f"horário: «{FC['horário']}» ({E})"]
    novos.append({"ID": ident, "Estado": "Publicado", "Título": T,
        "Entidade": "FADEX e IFMA – Programa Acredita no Primeiro Passo", "Link": P, "Página do curso": P, "Destino do link": "curso",
        "Local": "BR-MA", "Modalidade": "presencial", "País": "BR", "Região": "Maranhão", "Cidade": "Caxias",
        "Descrição": ("Dois cursos presenciais de 160 horas em Caxias (MA), para quem está no CadÚnico: Eletricista Instalador "
                      "Predial de Baixa Tensão e Instalador de Sistemas Fotovoltaicos (30 vagas cada). Aulas à noite, de segunda a "
                      "quinta, no CE Duque de Caxias, com práticas no IFMA. Pelo menos 60% das vagas são para mulheres."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego, renda", "Perfis": "todos",
        "Condição de acesso": "Estar no CadÚnico e morar em Caxias (MA)",
        "Requisitos": "\n".join(["ter entre 18 e 65 anos completos até a data da inscrição", "estar inscrito(a) no CadÚnico, com cadastro ativo",
                                 "residir no Município de Caxias/MA",
                                 "Curso de Eletricista Instalador Predial de Baixa Tensão: escolaridade mínima de Ensino Fundamental I (1º ao 5º ano) incompleto",
                                 "Curso de Instalador de Sistemas Fotovoltaicos: escolaridade mínima de Ensino Fundamental I (1º ao 5º ano) completo"]),
        "Idade mínima": "18", "Idade máxima": "65", "Prioridade CadÚnico": "Sim", "Turno": "noite",
        "Certificado": "desconhecido", "Inscrições até": "2026-11-30", "Início": "2026-12-09", "Duração": "160 horas",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Não",
        "Notas": f"{hoje}: criado à mão pelo Claude (Edital 30/2026 – FADEX; frases conferidas no navegador, a FADEX recusa o GitHub; regra T10).",
        "Como me inscrever": ("1. Até 30/11/2026, inscreva-se pelo formulário do edital (forms.gle/gak9oA9RjipqPcBG9) ou presencialmente "
                              "na Secretaria Municipal de Direitos Humanos e Políticas para as Mulheres, na Secretaria Municipal da "
                              "Proteção Social ou na Comunidade Batista Missionária (7h30–13h30, de segunda a sexta).\n2. Leve ou anexe "
                              "CPF, RG, comprovante de residência, comprovante de escolaridade e o NIS.\n3. O resultado sai a 4/12 no "
                              "site da FADEX; as aulas começam a partir de 9/12."),
        "Nota da verificação": f"{hoje}: edital lido no navegador (texto do PDF); frases conferidas.",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "data, vagas, idade", "Mudança a rever": "FALSE",
        "O que falta confirmar": ("O edital não diz com estas palavras que o curso é gratuito (diz que as inscrições são gratuitas). "
                                  "A seleção prioriza o perfil do CadÚnico e critérios de diversidade; o edital não diz se, entre "
                                  "candidatos iguais, vale a ordem de inscrição.")})

# --- esconder linhas fechadas (confere o título antes)
ESC = {616: ("Libras", "inscrições de 14 a 23/10/2026 (Edital 195/2026), já fechadas"),
       625: ("Informática Básica", "inscrições até 02/11/2026; turma a decorrer desde 17/11 (psg.se.senac.br)"),
       626: ("Word e Excel", "inscrições até 02/11/2026; turma a decorrer desde 23/11"),
       628: ("Qualidade no atendimento", "turma a decorrer desde 16/11"),
       1131: ("Sine", "notícia da semana de 23 a 27/11, sem inscrição indicada; a semana acabou")}
for ln, (pal, motivo) in ESC.items():
    r = por_linha.get(ln)
    if not r or pal.lower() not in (r.get("Título") or "").lower():
        print("NÃO escondi a linha", ln, (r or {}).get("Título")); continue
    if (r.get("Revisto por pessoa") or "").strip():
        print("revista por pessoa, não mexo:", ln); continue
    alter.append((ln, {"Estado": "Oculto", "Notas": ((r.get("Notas") or "") + f"\n{hoje} (Claude, auditoria 4): Oculto — {motivo}.").strip()}))
# --- anotar IF Baiano EaD (Mudança a rever fica para uma pessoa)
for ln, fi in ((568, fi1), (569, fi2)):
    r = por_linha.get(ln)
    if r and "distância" in (r.get("Título") or "") and fi and fsel:
        nota = (f"\n{hoje} (Claude, auditoria 4, conferido por código): inscrições «{list(fi.values())[0]}»; "
                f"«{fsel['vagas']}». O IF Baiano é «Tudo gratuito» (escolas públicas e IFs, decisão de 23/11): a dúvida de "
                "gratuidade que marcou «Mudança a rever» fica resolvida; só uma pessoa pode desmarcar.")
        alter.append((ln, {"Notas": ((r.get("Notas") or "") + nota).strip()[:3000]}))
base.atualizar("Cursos", alter); base.acrescentar("Cursos", novos); base.guardar()
print("criados:", [n["ID"] + " " + n["Título"][:50] for n in novos]); print("alterados:", [a[0] for a in alter])
