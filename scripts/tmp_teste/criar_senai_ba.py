"""Temporário (25/11/2026): cursos gratuitos do SENAI Bahia com inscrições abertas (processo Borborema e CIMATEC
Plural). Cada frase é conferida por código na página oficial ou no edital antes de gravar. Apagar depois de correr."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import DESCRICAO_RESUMO, VERIFICACAO_INICIAL, Base, citacao_valida, hoje_iso, texto_de_html
from comum import baixar
from cursos import id_curso

SECO = bool(os.environ.get("SECO"))
hoje = hoje_iso()
textos = {}


def texto(url, bruto=False):
    if url not in textos:
        b = baixar(url, timeout=60)
        textos[url] = (texto_de_html(b), b.decode("utf-8", "replace") if not b[:4] == b"%PDF" else "")
    return textos[url][1] if bruto else textos[url][0]


def prova(frase, url, bruto=False):
    t = texto(url, bruto)
    if bruto:
        import html, re
        t = html.unescape(re.sub(r"\s+", " ", t))  # inclui a descrição da página (meta)
    assert citacao_valida(frase, t), f"frase não encontrada em {url}: {frase}"
    return frase


cursos = []


def curso(**k):
    base_curso = {
        "Estado": "Publicado", "País": "BR", "Local": "BR-BA", "Região": "Bahia", "Modalidade": "presencial",
        "Origem da descrição": DESCRICAO_RESUMO, "Perfis": "todos", "Condição de acesso": "", "Certificado": "desconhecido",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "manual", "Notas": "",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "TRUE",
    }
    base_curso.update(k)
    cursos.append(base_curso)


# ---------------------------------------------------------------- Borborema (Jaguaquara, Jiquiriçá e Ubaíra)
PAG = "https://www.senaibahia.com.br/processo-seletivo-borborema/"
EDI = "https://www.senaibahia.com.br/wp-content/uploads/2026/11/EDITAL-BORBOREMA-chancelado.pdf"
g = prova("no curso gratuito de Aperfeiçoamento Profissional de Empregabilidade", EDI)
d = prova("das 15h do dia 18/11/2026 até as 23h do dia 30/11/2026", EDI)
o = prova("A análise documental será realizada considerando a ordem cronológica de inscrição dos candidatos", EDI)
reqs = [prova(x, EDI) for x in (
    "A partir do Ensino Fundamental I completo",
    "Ter, no mínimo, 16 (dezesseis) anos completos na data da inscrição",
    "Residir em um dos municípios contemplados pelo processo seletivo: Jiquiriçá/BA, Ubaíra/BA ou Jaguaquara/BA",
    "Ter disponibilidade para frequentar o curso presencialmente, no turno noturno, de segunda a sexta-feira")]
ch = prova("terá carga horária total de 30 (trinta) horas, com previsão de início em 09/12/2026, no turno noturno", EDI)
cert = prova("Será concedido certificado às participantes que obtiverem nota final igual ou superior a 7,0", EDI)
docs = prova("Documento oficial de identificação com foto legível (RG, CNH ou Carteira Profissional)", PAG)
TITULO = "Aperfeiçoamento Profissional em Empregabilidade: A Nova Rota da Formação Profissional"
for cidade in ("Jaguaquara", "Jiquiriçá", "Ubaíra"):
    curso(ID=id_curso(PAG + "#" + cidade, TITULO), Título=TITULO,
          Entidade="SENAI Bahia (em parceria com a Borborema Recursos Minerais)", Link=PAG, **{"Página do curso": PAG},
          Cidade=cidade,
          Descrição=(f"Curso curto (30 horas) para quem mora em {cidade} e quer se preparar para procurar emprego. "
                     "As aulas são à noite, de segunda a sexta-feira, a partir de 9 de dezembro de 2026. São 30 vagas "
                     "por município. A inscrição é pela internet, até 30 de novembro, com envio dos documentos; as "
                     "vagas são preenchidas pela ordem de inscrição."),
          Necessidades="emprego, profissao", Requisitos="; ".join(reqs), **{
              "Inscrições até": "2026-11-30", "Início": "2026-12-09", "Duração": "30 horas",
              "Como me inscrever": ("Faça a inscrição na página do processo seletivo, até as 23h de 30 de novembro de "
                                    "2026, e envie os documentos pedidos (foto ou arquivo) no próprio formulário."),
              "Nota da verificação": f"{hoje}: criado a partir da página oficial e do edital do SENAI Bahia (frases conferidas por código).",
              "Evidência": " | ".join([f"gratuito: «{g}» ({EDI})", f"data: «{d}» ({EDI})", f"vagas: «{o}» ({EDI})",
                                        f"duração: «{ch}» ({EDI})", f"certificado: «{cert}» ({EDI})",
                                        f"idade: «{reqs[1]}» ({EDI})", f"turno: «{ch}» ({EDI})",
                                        f"documentos: «{docs}» ({PAG})"]),
              "Campos comprovados": "gratuito, data, duração, idade, turno, documentos",
              "Idade mínima": "16", "Turno": "Noite", "Documentos pedidos": docs,
              "Onde se inscrever": "", "Origem": "manual"})

# ---------------------------------------------------------------- CIMATEC Plural (Salvador, exclusivo PcD)
PAG2 = "https://www.senaibahia.com.br/processo-seletivo-cqpg-cimatec-plural/"
g2 = prova("Curso de Qualificação Profissional Gratuito em Design Gráfico Digital", PAG2)
d2 = prova("As inscrições para o Curso de Qualificação Profissional Gratuito em Design Gráfico Digital (CIMATEC Plural) "
           "terão início no dia 23 de novembro de 2026 e irão até 07 de dezembro de 2026", PAG2)
p2 = prova("Exclusivo para Pessoas com Deficiência (PcD)", PAG2, bruto=True)
reqs2 = [prova(x, PAG2) for x in (
    "Ser pessoa com deficiência (PcD) , mediante comprovação por laudo médico",
    "Ser pessoa de baixa renda , mediante autodeclaração no ato de inscrição",
    "Ter idade mínima de 16 anos completos no ato da matrícula",
    "Ter concluído o Ensino Fundamental (apresentar histórico ou certificado)",
    "Possuir conhecimentos básicos do sistema operacional Windows (manuseio de pastas, arquivos e navegação na internet)")]
ch2 = prova("Com carga horária de 220 horas", PAG2)
lo2 = prova("SENAI CIMATEC • Av. Orlando Gomes, 1845 - Piatã, Salvador - BA, 41650-010", PAG2)
tu2 = prova("Aulas presenciais no SENAI CIMATEC (Turno Matutino: 8h às 12h)", PAG2)
TIT2 = "Design Gráfico Digital (Programa CIMATEC Plural, para pessoas com deficiência)"
curso(ID=id_curso(PAG2, TIT2), Título=TIT2, Entidade="SENAI Bahia (SENAI CIMATEC)", Link=PAG2,
      **{"Página do curso": PAG2}, Cidade="Salvador",
      Descrição=("Curso de 220 horas para pessoas com deficiência: criação de logotipos, cartazes, folders e outras peças "
                 "gráficas no computador, com fotografia básica, ilustração e uso de inteligência artificial. As aulas são "
                 "de manhã (8h às 12h) no SENAI CIMATEC, em Piatã, Salvador, a partir de 14 de dezembro de 2026. São 20 "
                 "vagas. A inscrição é pela internet, de 23 de novembro a 7 de dezembro, com envio do laudo médico."),
      Necessidades="profissao, emprego, tecnologia", Requisitos="; ".join(reqs2), **{
          "Inscrições até": "2026-12-07", "Início": "2026-12-14", "Duração": "220 horas",
          "Como me inscrever": ("Preencha a ficha de inscrição pela internet (o botão está na página do processo seletivo), "
                                "até 7 de dezembro de 2026, e envie os documentos e o laudo médico."),
          "Nota da verificação": f"{hoje}: criado a partir da página oficial do SENAI Bahia (frases conferidas por código). "
                                 "O regulamento não está ligado na página: a forma de classificação não foi lida.",
          "Evidência": " | ".join([f"gratuito: «{g2}» ({PAG2})", f"data: «{d2}» ({PAG2})", f"público: «{p2}» ({PAG2})",
                                    f"duração: «{ch2}» ({PAG2})", f"local: «{lo2}» ({PAG2})", f"turno: «{tu2}» ({PAG2})",
                                    f"idade: «{reqs2[2]}» ({PAG2})"]),
          "Campos comprovados": "gratuito, data, público, duração, idade, turno",
          "Idade mínima": "16", "Turno": "Manhã", "Renda máxima": "",
          "O que falta confirmar": "Como os candidatos são classificados (o regulamento não está ligado na página)."})

for c in cursos:
    print(c["ID"], c["Título"][:60], c.get("Cidade"), "| requisitos:", c["Requisitos"][:120])
if SECO:
    sys.exit(0)
base = Base()
existentes = {x.get("ID") for x in base.tabela("Cursos")}
novos = [c for c in cursos if c["ID"] not in existentes]
base.acrescentar("Cursos", novos)
base.guardar()
print(f"{len(novos)} cursos gravados.")
